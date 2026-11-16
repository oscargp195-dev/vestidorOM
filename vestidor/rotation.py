"""Regla de rotación: las partes de arriba aprobadas se bloquean N días."""

from __future__ import annotations

from datetime import date, timedelta

from .models import ROTATION_CATEGORIES, Garment

DEFAULT_LOCK_DAYS = 7


def locked_items(history: list[dict], garments: list[Garment], on: date,
                 days: int = DEFAULT_LOCK_DAYS) -> dict[str, str]:
    """Devuelve {garment_id: fecha_desbloqueo} de las prendas bloqueadas en `on`.

    Aprobar el día D bloquea la prenda D..D+days-1; vuelve a estar disponible el D+days.
    Solo afecta a categorías de rotación (tops). Las entradas futuras no bloquean el pasado.
    """
    rotating = {g.id for g in garments if g.category in ROTATION_CATEGORIES}
    locked: dict[str, str] = {}
    for entry in history:
        worn = date.fromisoformat(entry["date"])
        unlock = worn + timedelta(days=days)
        if worn <= on < unlock:
            for gid in entry["items"]:
                if gid in rotating:
                    prev = locked.get(gid)
                    if prev is None or unlock.isoformat() > prev:
                        locked[gid] = unlock.isoformat()
    return locked


def previous_entry(history: list[dict], on: date) -> dict | None:
    past = [e for e in history if date.fromisoformat(e["date"]) < on]
    return max(past, key=lambda e: e["date"]) if past else None
