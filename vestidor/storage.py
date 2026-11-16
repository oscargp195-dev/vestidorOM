"""Persistencia en JSON dentro de VESTIDOR_HOME."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from .models import ID_PREFIX, Garment


def default_home() -> Path:
    env = os.environ.get("VESTIDOR_HOME")
    if env:
        return Path(env).expanduser()
    repo = Path(__file__).resolve().parent.parent
    if (repo / "pyproject.toml").exists():
        return repo / "data"
    xdg = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(xdg) / "vestidor"


class Store:
    def __init__(self, home: str | Path | None = None):
        self.home = Path(home) if home else default_home()
        self.images = self.home / "images"
        self.originals = self.home / "originals"
        self.outfits = self.home / "outfits"
        for d in (self.home, self.images, self.originals, self.outfits):
            d.mkdir(parents=True, exist_ok=True)

    # --- bajo nivel -------------------------------------------------------
    def _read(self, name: str, default):
        path = self.home / name
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, name: str, data) -> None:
        path = self.home / name
        fd, tmp = tempfile.mkstemp(dir=self.home, prefix=f".{name}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    # --- armario ----------------------------------------------------------
    def wardrobe(self) -> list[Garment]:
        data = self._read("wardrobe.json", {"garments": []})
        return [Garment.from_dict(g) for g in data.get("garments", [])]

    def save_wardrobe(self, garments: list[Garment]) -> None:
        self._write("wardrobe.json", {"garments": [g.to_dict() for g in garments]})

    def get(self, garment_id: str) -> Garment | None:
        return next((g for g in self.wardrobe() if g.id == garment_id), None)

    def next_id(self, category: str) -> str:
        prefix = ID_PREFIX[category]
        nums = [int(m.group(1)) for g in self.wardrobe() if (m := re.fullmatch(rf"{prefix}-(\d+)", g.id))]
        return f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"

    # --- historial --------------------------------------------------------
    def history(self) -> list[dict]:
        return self._read("history.json", {"entries": []}).get("entries", [])

    def save_history(self, entries: list[dict]) -> None:
        entries = sorted(entries, key=lambda e: e["date"])
        self._write("history.json", {"entries": entries})

    # --- config -----------------------------------------------------------
    def config(self) -> dict:
        return self._read("config.json", {"lock_days": 7})

    def save_config(self, cfg: dict) -> None:
        self._write("config.json", cfg)
