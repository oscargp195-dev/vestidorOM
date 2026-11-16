"""CLI `vestidor`: pensada para que la use un agente de IA. Toda la salida es JSON."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

from . import __version__, background, collage, rotation, weather
from .models import CATEGORIES, SUBTYPES, Garment, validate
from .storage import Store
from .style import normalize_color
from .suggest import suggest


class CliError(Exception):
    def __init__(self, message: str, code: str = "ERROR", **extra):
        super().__init__(message)
        self.code = code
        self.extra = extra


def out(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


# --- helpers ---------------------------------------------------------------------
def abs_image(store: Store, rel: str) -> str:
    return str((store.home / rel).resolve()) if rel else ""


def garment_view(store: Store, g: Garment, locked: dict[str, str] | None = None) -> dict:
    d = g.to_dict()
    d["image"] = abs_image(store, g.image)
    d["original"] = abs_image(store, g.original)
    d["layer"] = g.layer
    if locked is not None:
        d["locked_until"] = locked.get(g.id)
    return d


def lock_days(store: Store) -> int:
    return int(store.config().get("lock_days", rotation.DEFAULT_LOCK_DAYS))


def current_locks(store: Store, day: date) -> dict[str, str]:
    return rotation.locked_items(store.history(), store.wardrobe(), day, lock_days(store))


def get_weather(store: Store, day: date, feels: float | None = None, rain: float | None = None) -> dict:
    loc = store.config().get("location")
    if feels is not None:
        return weather.manual(day, feels, rain or 0, loc.get("name") if loc else None)
    if not loc:
        raise CliError("No hay ubicación configurada. Pregunta al usuario su ciudad y ejecuta "
                       "`vestidor config set-location \"<ciudad>\"`.", code="LOCATION_NOT_SET")
    try:
        return weather.forecast(loc, day)
    except Exception as exc:  # red caída, fecha fuera de rango...
        raise CliError(f"No se pudo obtener el clima: {exc}. Puedes pasar --feels y --rain a mano.",
                       code="WEATHER_UNAVAILABLE")


def parse_colors(raw: str | None) -> list[str]:
    return [normalize_color(c) for c in raw.split(",") if c.strip()] if raw else []


def require(store: Store, ids: list[str]) -> list[Garment]:
    by_id = {g.id: g for g in store.wardrobe()}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise CliError(f"Prendas no encontradas: {', '.join(missing)}", code="NOT_FOUND")
    return [by_id[i] for i in ids]


def store_image(store: Store, gid: str, photo: str, remove_bg: bool) -> dict:
    src = Path(photo).expanduser()
    if not src.exists():
        raise CliError(f"No existe la foto {src}", code="NOT_FOUND")
    original = store.originals / f"{gid}{src.suffix.lower() or '.jpg'}"
    shutil.copy2(src, original)
    res = background.process(src, store.images / f"{gid}.png", remove_bg=remove_bg)
    res["image"] = f"images/{gid}.png"
    res["original"] = f"originals/{original.name}"
    return res


# --- comandos ---------------------------------------------------------------------
def cmd_info(store: Store, a) -> dict:
    cfg = store.config()
    return {"ok": True, "version": __version__, "home": str(store.home.resolve()),
            "location": cfg.get("location"), "lock_days": lock_days(store),
            "rembg_available": background.rembg_available(), "garments": len(store.wardrobe()),
            "categories": CATEGORIES, "subtypes": SUBTYPES}


def cmd_config(store: Store, a) -> dict:
    cfg = store.config()
    if a.action == "set-location":
        if not a.value:
            raise CliError("Falta la ciudad", code="BAD_INPUT")
        cfg["location"] = weather.geocode(a.value)
        store.save_config(cfg)
    elif a.action == "set-lock-days":
        cfg["lock_days"] = int(a.value)
        store.save_config(cfg)
    return {"ok": True, "config": cfg}


def _apply_fields(g: Garment, a) -> None:
    for attr in ("name", "subtype", "pattern", "material", "notes", "category"):
        val = getattr(a, attr, None)
        if val is not None:
            setattr(g, attr, val.strip().lower() if attr in ("subtype", "pattern", "category") else val.strip())
    if a.colors is not None:
        g.colors = parse_colors(a.colors)
    for attr in ("warmth", "formality"):
        val = getattr(a, attr, None)
        if val is not None:
            setattr(g, attr, int(val))
    for attr in ("rain_ok", "logo"):
        val = getattr(a, attr, None)
        if val is not None:
            setattr(g, attr, val)


def cmd_add(store: Store, a) -> dict:
    category = a.category.strip().lower()
    if category not in CATEGORIES:
        raise CliError(f"category debe ser una de {CATEGORIES}", code="BAD_INPUT")
    gid = store.next_id(category)
    g = Garment(id=gid, name=a.name or "", category=category, added=datetime.now().isoformat(timespec="seconds"))
    _apply_fields(g, a)
    if not g.name:
        g.name = " ".join(filter(None, [g.subtype, g.primary_color])) or gid
    errors = validate(g)
    if errors:
        raise CliError("; ".join(errors), code="BAD_INPUT")
    res = store_image(store, gid, a.photo, remove_bg=not a.no_bg)
    g.image, g.original = res["image"], res["original"]
    garments = store.wardrobe()
    garments.append(g)
    store.save_wardrobe(garments)
    warnings = [res["warning"]] if res["warning"] else []
    if g.subtype and g.subtype not in SUBTYPES[g.category]:
        warnings.append(f"Subtipo '{g.subtype}' no está en la lista conocida; se acepta igualmente")
    return {"ok": True, "garment": garment_view(store, g), "background_removed": res["background_removed"],
            "warnings": warnings}


def cmd_edit(store: Store, a) -> dict:
    garments = store.wardrobe()
    g = next((x for x in garments if x.id == a.id), None)
    if g is None:
        raise CliError(f"No existe {a.id}", code="NOT_FOUND")
    _apply_fields(g, a)
    errors = validate(g)
    if errors:
        raise CliError("; ".join(errors), code="BAD_INPUT")
    warnings = []
    if a.photo:
        res = store_image(store, g.id, a.photo, remove_bg=not a.no_bg)
        g.image, g.original = res["image"], res["original"]
        if res["warning"]:
            warnings.append(res["warning"])
    store.save_wardrobe(garments)
    return {"ok": True, "garment": garment_view(store, g), "warnings": warnings}


def cmd_remove(store: Store, a) -> dict:
    garments = store.wardrobe()
    g = next((x for x in garments if x.id == a.id), None)
    if g is None:
        raise CliError(f"No existe {a.id}", code="NOT_FOUND")
    store.save_wardrobe([x for x in garments if x.id != a.id])
    if a.delete_images:
        for rel in (g.image, g.original):
            if rel:
                (store.home / rel).unlink(missing_ok=True)
    return {"ok": True, "removed": g.id}


def cmd_list(store: Store, a) -> dict:
    day = weather.parse_date(a.date)
    locked = current_locks(store, day)
    items = store.wardrobe()
    if a.category:
        items = [g for g in items if g.category == a.category]
    if a.available:
        items = [g for g in items if g.id not in locked]
    return {"ok": True, "count": len(items), "garments": [garment_view(store, g, locked) for g in items]}


def cmd_show(store: Store, a) -> dict:
    (g,) = require(store, [a.id])
    locked = current_locks(store, date.today())
    worn = [e["date"] for e in store.history() if g.id in e["items"]]
    return {"ok": True, "garment": garment_view(store, g, locked), "worn_on": worn}


def cmd_weather(store: Store, a) -> dict:
    return {"ok": True, "weather": get_weather(store, weather.parse_date(a.date), a.feels, a.rain)}


def cmd_suggest(store: Store, a) -> dict:
    day = weather.parse_date(a.date)
    w = get_weather(store, day, a.feels, a.rain)
    history = store.history()
    garments = store.wardrobe()
    locked = rotation.locked_items(history, garments, day, lock_days(store))
    prev = rotation.previous_entry(history, day)
    result = suggest(garments, w, a.occasion, a.n, locked, set(prev["items"]) if prev else set())
    if not result["ok"]:
        raise CliError(result["error"], code="NO_OUTFIT", locked=locked)
    by_id = {g.id: g for g in garments}
    for i, o in enumerate(result["outfits"], 1):
        for item in o["items"]:
            item["image"] = abs_image(store, item["image"])
        if not a.no_render:
            path = store.outfits / f"{day.isoformat()}-{i}.jpg"
            collage.render([by_id[it["id"]] for it in o["items"]], path, store.home, day, w,
                           title=f"Opción {i}" if len(result["outfits"]) > 1 else None)
            o["collage"] = str(path.resolve())
    result["date"] = day.isoformat()
    result["approve_hint"] = "vestidor approve <ids...> --date " + day.isoformat()
    return result


def cmd_render(store: Store, a) -> dict:
    items = require(store, a.ids)
    day = weather.parse_date(a.date)
    w = None
    if not a.no_weather:
        try:
            w = get_weather(store, day, a.feels, a.rain)
        except CliError:
            w = None
    name = a.output or str(store.outfits / f"{day.isoformat()}-custom-{datetime.now():%H%M%S}.jpg")
    path = collage.render(items, name, store.home, day, w, title=a.title)
    locked = current_locks(store, day)
    clash = [g.id for g in items if g.id in locked]
    return {"ok": True, "collage": str(Path(path).resolve()), "locked_items": {i: locked[i] for i in clash}}


def cmd_approve(store: Store, a) -> dict:
    items = require(store, a.ids)
    day = weather.parse_date(a.date)
    history = store.history()
    others = [e for e in history if e["date"] != day.isoformat()]
    locked = rotation.locked_items(others, store.wardrobe(), day, lock_days(store))
    clash = {g.id: locked[g.id] for g in items if g.id in locked}
    if clash and not a.force:
        raise CliError("Hay partes de arriba bloqueadas por la regla de rotación", code="LOCKED", locked=clash)
    entry = {"date": day.isoformat(), "items": [g.id for g in items], "occasion": a.occasion,
             "approved_at": datetime.now().isoformat(timespec="seconds")}
    store.save_history(others + [entry])
    unlock = rotation.locked_items([entry], store.wardrobe(), day, lock_days(store))
    replaced = len(others) != len(history)
    return {"ok": True, "entry": entry, "replaced_previous_for_date": replaced, "locked_until": unlock}


def cmd_unapprove(store: Store, a) -> dict:
    day = weather.parse_date(a.date).isoformat()
    history = store.history()
    remaining = [e for e in history if e["date"] != day]
    if len(remaining) == len(history):
        raise CliError(f"No hay outfit aprobado para {day}", code="NOT_FOUND")
    store.save_history(remaining)
    return {"ok": True, "removed_date": day}


def cmd_history(store: Store, a) -> dict:
    by_id = {g.id: g for g in store.wardrobe()}
    cutoff = date.today().toordinal() - a.days
    entries = [e for e in store.history() if date.fromisoformat(e["date"]).toordinal() >= cutoff]
    for e in entries:
        e["names"] = [by_id[i].name if i in by_id else f"{i} (eliminada)" for i in e["items"]]
    return {"ok": True, "entries": entries}


def cmd_locked(store: Store, a) -> dict:
    day = weather.parse_date(a.date)
    locked = current_locks(store, day)
    by_id = {g.id: g for g in store.wardrobe()}
    return {"ok": True, "date": day.isoformat(),
            "locked": [{"id": i, "name": by_id[i].name, "unlocks_on": d} for i, d in sorted(locked.items())]}


# --- parser ---------------------------------------------------------------------
def _garment_args(p: argparse.ArgumentParser, add: bool) -> None:
    p.add_argument("--name")
    p.add_argument("--subtype")
    p.add_argument("--colors", help="lista separada por comas, el principal primero (navy,white)")
    p.add_argument("--pattern", help="solid, stripes, check, gingham, herringbone, cable-knit...")
    p.add_argument("--material", help="algodón, lino, lana, cashmere, ante, cuero...")
    p.add_argument("--warmth", type=int, choices=range(1, 6))
    p.add_argument("--formality", type=int, choices=range(1, 6))
    p.add_argument("--rain-ok", dest="rain_ok", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--logo", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--notes")
    p.add_argument("--no-bg", action="store_true", help="no quitar el fondo (ya viene limpia)")
    if not add:
        p.add_argument("--category", choices=CATEGORIES)
        p.add_argument("--photo", help="sustituir la foto")


def _weather_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--date", default="today", help="today | tomorrow | YYYY-MM-DD")
    p.add_argument("--feels", type=float, help="sensación térmica manual (sin red)")
    p.add_argument("--rain", type=float, help="probabilidad de lluvia manual (%%)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vestidor", description="Asistente de outfits old money (salida JSON)")
    p.add_argument("--home", help="carpeta de datos (por defecto VESTIDOR_HOME o <repo>/data)")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="rutas, ubicación, vocabulario válido").set_defaults(fn=cmd_info)

    c = sub.add_parser("config", help="configuración")
    c.add_argument("action", choices=["show", "set-location", "set-lock-days"])
    c.add_argument("value", nargs="?")
    c.set_defaults(fn=cmd_config)

    ad = sub.add_parser("add", help="añadir prenda desde una foto")
    ad.add_argument("photo")
    ad.add_argument("--category", required=True, choices=CATEGORIES)
    _garment_args(ad, add=True)
    ad.set_defaults(fn=cmd_add)

    ed = sub.add_parser("edit", help="editar etiquetas o foto de una prenda")
    ed.add_argument("id")
    _garment_args(ed, add=False)
    ed.set_defaults(fn=cmd_edit)

    rm = sub.add_parser("remove", help="quitar prenda del armario")
    rm.add_argument("id")
    rm.add_argument("--delete-images", action="store_true")
    rm.set_defaults(fn=cmd_remove)

    ls = sub.add_parser("list", help="listar armario")
    ls.add_argument("--category", choices=CATEGORIES)
    ls.add_argument("--available", action="store_true", help="solo no bloqueadas")
    ls.add_argument("--date", default="today")
    ls.set_defaults(fn=cmd_list)

    sh = sub.add_parser("show", help="ver una prenda")
    sh.add_argument("id")
    sh.set_defaults(fn=cmd_show)

    we = sub.add_parser("weather", help="clima del día")
    _weather_args(we)
    we.set_defaults(fn=cmd_weather)

    sg = sub.add_parser("suggest", help="proponer outfits y generar collages")
    _weather_args(sg)
    sg.add_argument("--occasion", help="texto libre: cena, uni, boda, club de tenis... (por defecto casual arreglado)")
    sg.add_argument("--n", type=int, default=3)
    sg.add_argument("--no-render", action="store_true")
    sg.set_defaults(fn=cmd_suggest)

    rd = sub.add_parser("render", help="collage de una combinación concreta")
    rd.add_argument("ids", nargs="+")
    _weather_args(rd)
    rd.add_argument("--title")
    rd.add_argument("--output")
    rd.add_argument("--no-weather", action="store_true")
    rd.set_defaults(fn=cmd_render)

    ap = sub.add_parser("approve", help="registrar outfit aprobado (bloquea las partes de arriba)")
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--date", default="today")
    ap.add_argument("--occasion")
    ap.add_argument("--force", action="store_true", help="aprobar aunque haya prendas bloqueadas")
    ap.set_defaults(fn=cmd_approve)

    un = sub.add_parser("unapprove", help="deshacer el outfit aprobado de un día")
    un.add_argument("--date", default="today")
    un.set_defaults(fn=cmd_unapprove)

    hi = sub.add_parser("history", help="historial de outfits")
    hi.add_argument("--days", type=int, default=14)
    hi.set_defaults(fn=cmd_history)

    lk = sub.add_parser("locked", help="partes de arriba bloqueadas")
    lk.add_argument("--date", default="today")
    lk.set_defaults(fn=cmd_locked)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    try:
        store = Store(args.home)
        out(args.fn(store, args))
        return 0
    except CliError as exc:
        out({"ok": False, "code": exc.code, "error": str(exc), **exc.extra})
        return 1
    except (ValueError, OSError) as exc:
        out({"ok": False, "code": "ERROR", "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
