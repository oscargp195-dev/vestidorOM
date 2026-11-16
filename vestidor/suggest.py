"""Generación y puntuación de outfits."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from . import style
from .models import Garment

TOP_K = 8  # candidatos por hueco tras el pre-filtrado


@dataclass
class Outfit:
    items: list[Garment]
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    breakdown: dict = field(default_factory=dict)

    def ids(self) -> list[str]:
        return [g.id for g in self.items]

    def tops(self) -> set[str]:
        return {g.id for g in self.items if g.category == "top"}

    def by(self, category: str) -> list[Garment]:
        return [g for g in self.items if g.category == category]

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 2),
            "items": [{"id": g.id, "name": g.name, "category": g.category, "subtype": g.subtype,
                       "colors": g.colors, "image": g.image} for g in self.items],
            "reasons": self.reasons,
            "warnings": self.warnings,
            "breakdown": {k: round(v, 2) for k, v in self.breakdown.items()},
        }


def _prefilter(items: list[Garment], weather: dict, frange) -> list[Garment]:
    scored = [(style.item_style_score(g, frange) + style.item_weather_score(g, weather)[0], g) for g in items]
    scored.sort(key=lambda t: t[0], reverse=True)
    return [g for _, g in scored[:TOP_K]]


def _belt_for(shoes: Garment | None, belts: list[Garment]) -> Garment | None:
    if not belts:
        return None
    if shoes is None:
        return belts[0]
    shoe_brown = style.normalize_color(shoes.primary_color) in style.BROWNS
    for b in belts:
        if (style.normalize_color(b.primary_color) in style.BROWNS) == shoe_brown:
            return b
    return None


def score_outfit(items: list[Garment], weather: dict, frange, prev_ids: set[str],
                 cache: dict | None = None) -> Outfit:
    cache = {} if cache is None else cache

    def item_scores(g: Garment):
        if g.id not in cache:
            cache[g.id] = (style.item_style_score(g, frange), style.item_weather_score(g, weather))
        return cache[g.id]

    o = Outfit(items=items)
    bd = o.breakdown
    feels = weather["feels"]

    # 1. Estilo de cada prenda
    bd["estilo"] = sum(item_scores(g)[0] for g in items)

    # 2. Clima: prendas sueltas + abrigo total de capas
    bd["clima_prendas"] = 0.0
    for g in items:
        s, notes = item_scores(g)[1]
        bd["clima_prendas"] += s
        o.warnings += notes
    layers = [g for g in items if g.category in ("top", "outerwear")]
    total = sum(g.warmth for g in layers)
    (lo, hi), band = style.warmth_target(feels)
    dist = lo - total if total < lo else (total - hi if total > hi else 0)
    bd["clima_capas"] = -1.5 * dist
    outer = o.by("outerwear")
    if feels < 10 and not outer:
        bd["clima_capas"] -= 2
    if feels < 5 and not any(g.warmth >= 4 for g in outer):
        bd["clima_capas"] -= 1.5
    if weather.get("feels_max", feels) - weather.get("feels_min", feels) >= 8 and len(layers) == 1:
        bd["clima_capas"] -= 0.5
        o.warnings.append("Mucha diferencia de temperatura en el día: mejor llevar una capa que puedas quitarte")

    # 3. Armonía de color y patrones
    colors = [style.normalize_color(g.primary_color) for g in items if g.primary_color]
    accents = [c for c in colors if c not in style.NEUTRALS]
    bd["color"] = -0.7 * max(0, len(accents) - 1)
    visible = {g.category: style.normalize_color(g.primary_color) for g in items}
    top_outer = [style.normalize_color(g.primary_color) for g in layers]
    bottom_c = visible.get("bottom", "")
    if ("black" in top_outer and bottom_c == "navy") or ("navy" in top_outer and bottom_c == "black"):
        bd["color"] -= 0.5
    if bottom_c and layers and top_outer[-1] == bottom_c and bottom_c not in ("white", "cream", "denim"):
        bd["color"] -= 0.3  # mismo color arriba y abajo
    patterned = [g for g in items if style.is_patterned(g)]
    bd["patrones"] = -0.6 * max(0, len(patterned) - 1)

    # 4. Coherencia de formalidad
    forms = [g.formality for g in items if g.category != "accessory"]
    spread = max(forms) - min(forms) if forms else 0
    bd["formalidad"] = -0.5 * max(0, spread - 2)

    # 5. Zapatos y cinturón
    shoes = o.by("shoes")
    belts = [g for g in o.by("accessory") if g.subtype == "belt"]
    bd["cuero"] = 0.0
    if shoes and belts:
        sb = style.normalize_color(shoes[0].primary_color) in style.BROWNS
        bb = style.normalize_color(belts[0].primary_color) in style.BROWNS
        bd["cuero"] = 0.3 if sb == bb else -0.6

    # 6. No repetir pantalón/zapatos del día anterior
    bd["repeticion"] = -0.4 * len({g.id for g in items if g.category == "bottom"} & prev_ids)
    bd["repeticion"] -= 0.2 * len({g.id for g in shoes} & prev_ids)

    o.score = sum(bd.values())

    # Razones legibles
    o.reasons.append(f"Sensación {feels:.0f} °C → {band} (abrigo total {total}, ideal {lo}-{hi})")
    neutral_share = sum(c in style.NEUTRALS for c in colors) / len(colors) if colors else 0
    if neutral_share >= 0.75:
        o.reasons.append("Paleta neutra old money: " + ", ".join(dict.fromkeys(colors)))
    if bd["cuero"] > 0:
        o.reasons.append("Zapatos y cinturón en el mismo tono")
    rain = weather.get("rain_prob", 0)
    if rain >= 50:
        if any(g.rain_ok for g in outer):
            o.reasons.append(f"Lluvia {rain:.0f} %: capa exterior que aguanta el agua")
        else:
            o.warnings.append(f"Lluvia {rain:.0f} %: llévate paraguas")
    if dist:
        o.warnings.append("No hay combinación con el abrigo ideal en el armario disponible" if dist > 1
                          else "Abrigo ligeramente por " + ("debajo" if total < lo else "encima") + " de lo ideal")
    if accents:
        o.reasons.append("Toque de color: " + ", ".join(dict.fromkeys(accents)))
    return o


def suggest(garments: list[Garment], weather: dict, occasion: str | None = None, n: int = 3,
            locked: dict[str, str] | None = None, prev_ids: set[str] | None = None) -> dict:
    locked = locked or {}
    prev_ids = prev_ids or set()
    frange, occ_label = style.occasion_range(occasion)
    avail = [g for g in garments if g.id not in locked]

    def pick(pred):
        return _prefilter([g for g in avail if pred(g)], weather, frange)

    bases = pick(lambda g: g.category == "top" and g.layer == "base")
    mids = pick(lambda g: g.category == "top" and g.layer == "mid")
    outers = pick(lambda g: g.category == "outerwear")
    bottoms = pick(lambda g: g.category == "bottom")
    shoes = pick(lambda g: g.category == "shoes")
    belts = [g for g in avail if g.category == "accessory" and g.subtype == "belt"]
    scarves = [g for g in avail if g.category == "accessory" and g.subtype == "scarf"]

    problems = []
    if not bases and not mids:
        problems.append("No hay partes de arriba disponibles (todas bloqueadas o armario vacío)")
    if not bottoms:
        problems.append("No hay pantalones en el armario")
    if problems:
        return {"ok": False, "error": "; ".join(problems), "locked": locked}

    outfits: list[Outfit] = []
    cache: dict = {}
    for base, mid, outer, bottom, shoe in itertools.product(
            bases + [None], mids + [None], outers + [None], bottoms, shoes or [None]):
        if base is None and mid is None:
            continue
        if base is not None and mid is not None and mid.subtype == "hoodie" and base.subtype != "t-shirt":
            continue
        items = [g for g in (outer, mid, base, bottom, shoe) if g is not None]
        belt = _belt_for(shoe, belts) if bottom.subtype not in ("joggers",) else None
        if belt:
            items.append(belt)
        if scarves and weather["feels"] < 8:
            items.append(scarves[0])
        outfits.append(score_outfit(items, weather, frange, prev_ids, cache))

    outfits.sort(key=lambda o: o.score, reverse=True)
    chosen: list[Outfit] = []
    for strict in (True, False):
        for o in outfits:
            if len(chosen) >= n:
                break
            if any(o is c for c in chosen):
                continue
            if strict and any(o.tops() & c.tops() or o.ids() == c.ids() for c in chosen):
                continue
            chosen.append(o)

    result_warnings = []
    if not shoes:
        result_warnings.append("No hay calzado en el armario")
    return {
        "ok": True,
        "occasion": occ_label,
        "formality_range": list(frange),
        "weather": weather,
        "locked": locked,
        "warnings": result_warnings,
        "outfits": [o.to_dict() for o in chosen],
    }
