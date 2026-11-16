"""Modelo de prenda y vocabulario controlado."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

CATEGORIES = ("top", "outerwear", "bottom", "shoes", "accessory")

# Solo estas categorías entran en la regla de rotación (bloqueo de 7 días).
ROTATION_CATEGORIES = {"top"}

ID_PREFIX = {"top": "top", "outerwear": "out", "bottom": "bot", "shoes": "sho", "accessory": "acc"}

SUBTYPES = {
    "top": [
        "t-shirt", "polo", "shirt", "oxford", "linen-shirt", "henley", "rugby",
        "sweater", "cable-sweater", "cardigan", "quarter-zip", "sweatshirt", "hoodie", "sweater-vest",
    ],
    "outerwear": [
        "blazer", "overshirt", "harrington", "field-jacket", "waxed-jacket", "gilet", "bomber",
        "denim-jacket", "suede-jacket", "trench", "peacoat", "overcoat", "parka", "puffer",
    ],
    "bottom": ["chinos", "trousers", "jeans", "corduroy", "linen-trousers", "shorts", "bermuda", "joggers"],
    "shoes": [
        "loafers", "boat-shoes", "derby", "oxford-shoes", "chelsea-boots", "chukka", "desert-boots",
        "sneakers", "trainers", "espadrilles",
    ],
    "accessory": ["belt", "watch", "scarf", "cap", "sunglasses", "tie"],
}

# Capa base vs capa intermedia dentro de "top" (se pueden llevar a la vez: oxford + jersey).
TOP_BASE = {"t-shirt", "polo", "shirt", "oxford", "linen-shirt", "henley", "rugby"}
TOP_MID = {"sweater", "cable-sweater", "cardigan", "quarter-zip", "sweatshirt", "hoodie", "sweater-vest"}

PATTERNS_SUBTLE = {"stripes", "oxford", "check", "gingham", "plaid", "tartan", "herringbone", "houndstooth",
                   "cable-knit", "cable", "pinstripe", "corduroy", "textured", "argyle", "fair-isle"}
PATTERNS_LOUD = {"graphic", "floral", "camo", "print", "tie-dye", "animal", "logo-print", "hawaiian"}


@dataclass
class Garment:
    id: str
    name: str
    category: str
    subtype: str = ""
    colors: list[str] = field(default_factory=list)
    pattern: str = "solid"
    material: str = ""
    warmth: int = 2
    formality: int = 3
    rain_ok: bool = False
    logo: bool = False
    image: str = ""
    original: str = ""
    notes: str = ""
    added: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Garment":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    @property
    def layer(self) -> str:
        """Rol de capa: base / mid (solo tops), o la categoría en el resto."""
        if self.category != "top":
            return self.category
        if self.subtype in TOP_MID:
            return "mid"
        if self.subtype in TOP_BASE:
            return "base"
        return "mid" if self.warmth >= 3 else "base"

    @property
    def primary_color(self) -> str:
        return self.colors[0] if self.colors else ""


def validate(g: Garment) -> list[str]:
    errors = []
    if g.category not in CATEGORIES:
        errors.append(f"category debe ser una de {CATEGORIES}")
    if not 1 <= int(g.warmth) <= 5:
        errors.append("warmth debe estar entre 1 y 5")
    if not 1 <= int(g.formality) <= 5:
        errors.append("formality debe estar entre 1 y 5")
    if not g.name:
        errors.append("name es obligatorio")
    return errors
