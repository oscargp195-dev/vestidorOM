"""Reglas de estilo old money / casual arreglado (ropa de hombre)."""

from __future__ import annotations

import unicodedata

from .models import PATTERNS_LOUD, Garment

# --- color -----------------------------------------------------------------
COLOR_ALIASES = {
    "azul marino": "navy", "marino": "navy", "blanco": "white", "crema": "cream", "hueso": "cream",
    "ecru": "cream", "off-white": "cream", "beis": "beige", "beige": "beige", "arena": "beige",
    "camel": "camel", "caqui": "khaki", "kaki": "khaki", "gris": "grey", "gray": "grey",
    "gris oscuro": "charcoal", "antracita": "charcoal", "marron": "brown", "marrón": "brown",
    "chocolate": "dark-brown", "cuero": "tan", "coñac": "tan", "conac": "tan", "negro": "black",
    "verde oliva": "olive", "oliva": "olive", "verde botella": "forest-green", "verde bosque": "forest-green",
    "burdeos": "burgundy", "granate": "burgundy", "azul claro": "light-blue", "celeste": "light-blue",
    "azul": "blue", "rosa palo": "pale-pink", "rosa": "pink", "amarillo": "yellow", "rojo": "red",
    "naranja": "orange", "morado": "purple", "verde": "green", "denim": "denim", "vaquero": "denim",
    "azul denim": "denim", "light-grey": "grey", "dark-grey": "charcoal",
}

# Puntuación 0..1 de lo "old money" que es un color.
COLOR_SCORE = {
    "navy": 1.0, "white": 1.0, "cream": 1.0, "beige": 1.0, "camel": 1.0, "brown": 1.0, "dark-brown": 1.0,
    "tan": 0.95, "khaki": 0.9, "grey": 0.9, "charcoal": 0.9, "olive": 0.9, "forest-green": 0.9,
    "burgundy": 0.9, "light-blue": 0.95, "denim": 0.75, "blue": 0.7, "pale-pink": 0.7, "black": 0.55,
    "green": 0.5, "pink": 0.4, "red": 0.35, "yellow": 0.3, "purple": 0.3, "orange": 0.25,
}

NEUTRALS = {"navy", "white", "cream", "beige", "camel", "khaki", "grey", "charcoal", "brown",
            "dark-brown", "tan", "black", "denim", "light-blue"}
BROWNS = {"brown", "dark-brown", "tan", "camel"}

# --- subtipos ----------------------------------------------------------------
SUBTYPE_STYLE = {
    "oxford": 0.4, "polo": 0.3, "cable-sweater": 0.4, "quarter-zip": 0.3, "cardigan": 0.2,
    "sweater": 0.2, "sweater-vest": 0.2, "rugby": 0.2, "linen-shirt": 0.2, "shirt": 0.2,
    "blazer": 0.4, "waxed-jacket": 0.3, "harrington": 0.3, "overcoat": 0.3, "peacoat": 0.3, "trench": 0.3,
    "field-jacket": 0.2, "gilet": 0.1,
    "chinos": 0.4, "trousers": 0.3, "corduroy": 0.2, "linen-trousers": 0.2,
    "loafers": 0.5, "boat-shoes": 0.3, "derby": 0.3, "chukka": 0.3, "desert-boots": 0.2, "chelsea-boots": 0.2,
    "hoodie": -1.2, "joggers": -1.5, "sweatshirt": -0.3, "trainers": -0.6, "puffer": -0.4,
    "bomber": -0.2, "denim-jacket": -0.2, "t-shirt": -0.1,
}

# --- ocasión -----------------------------------------------------------------
OCCASIONS = [
    (("boda", "gala", "etiqueta", "ceremonia", "bautizo", "comunion"), (4, 5), "evento formal"),
    (("cena", "evento", "restaurante", "cita", "teatro", "fiesta", "copas", "opera"), (3, 5), "cena / evento"),
    (("trabajo", "oficina", "uni", "universidad", "clase", "reunion", "entrevista", "presentacion"), (3, 4), "trabajo / uni"),
    (("club", "tenis", "golf", "nautico", "barco", "regata", "polo", "hipica", "yate"), (2, 3), "country club"),
    (("playa", "piscina"), (1, 2), "playa"),
    (("deporte", "gym", "gimnasio", "correr", "entreno"), (1, 2), "deporte"),
    (("casa", "relax", "sofa", "recados"), (1, 3), "relajado"),
]
DEFAULT_OCCASION = ((2, 3), "casual arreglado (old money)")


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def normalize_color(color: str) -> str:
    c = color.strip().lower()
    return COLOR_ALIASES.get(c) or COLOR_ALIASES.get(_plain(c)) or c.replace(" ", "-")


def color_score(color: str) -> float:
    return COLOR_SCORE.get(normalize_color(color), 0.5) if color else 0.6


def occasion_range(occasion: str | None) -> tuple[tuple[int, int], str]:
    if not occasion:
        return DEFAULT_OCCASION
    text = _plain(occasion)
    for keywords, rng, label in OCCASIONS:
        if any(k in text for k in keywords):
            return rng, label
    return DEFAULT_OCCASION[0], f"{occasion} (casual arreglado)"


# --- clima -> capas -------------------------------------------------------------
WARMTH_BANDS = [  # (sensación mínima, rango de abrigo total base+mid+outer, descripción)
    (27, (1, 2), "calor: una sola capa ligera"),
    (22, (1, 3), "templado-cálido: una capa, como mucho blazer ligero"),
    (17, (2, 4), "templado: camisa/polo y, si acaso, punto fino o sobrecamisa"),
    (12, (4, 6), "fresco: capa intermedia de punto o chaqueta ligera"),
    (7, (6, 8), "frío: punto + chaqueta/abrigo"),
    (2, (8, 10), "mucho frío: capas + abrigo de lana"),
    (-99, (10, 15), "helada: abrigo pesado, punto grueso y bufanda"),
]


def warmth_target(feels: float) -> tuple[tuple[int, int], str]:
    for threshold, rng, label in WARMTH_BANDS:
        if feels >= threshold:
            return rng, label
    return WARMTH_BANDS[-1][1], WARMTH_BANDS[-1][2]


def item_weather_score(g: Garment, w: dict) -> tuple[float, list[str]]:
    """Encaje individual de una prenda con el clima (no la suma de capas)."""
    feels, rain = w["feels"], w.get("rain_prob", 0)
    s, notes = 0.0, []
    st, mat = g.subtype, (g.material or "").lower()
    if g.category == "bottom":
        if st in ("shorts", "bermuda") and feels < 23:
            s -= 3
        if st == "linen-trousers" and feels < 18:
            s -= 1
        if st == "corduroy" and feels > 20:
            s -= 1
        if st in ("shorts", "bermuda") and feels >= 27:
            s += 0.3
    if g.category == "shoes":
        if st in ("chelsea-boots", "chukka", "desert-boots") and feels > 24:
            s -= 1
        if st in ("espadrilles", "boat-shoes") and feels < 14:
            s -= 1
        if rain >= 50 and not g.rain_ok and ("ante" in mat or "suede" in mat or st == "espadrilles"):
            s -= 1.5
            notes.append(f"{g.name}: evita ante/esparto con lluvia")
        elif rain >= 50 and g.rain_ok:
            s += 0.4
    if g.category in ("top", "outerwear"):
        if g.warmth >= 4 and feels >= 18:
            s -= 1.0  # punto grueso / abrigo con temperatura templada
        if g.warmth >= 3 and feels >= 24:
            s -= 1.0
    if g.category == "outerwear" and rain >= 50:
        s += 0.8 if g.rain_ok else -0.3
    if "lino" in mat or "linen" in mat:
        s += 0.3 if feels >= 24 else (-0.6 if feels < 16 else 0)
    if g.category == "accessory" and g.subtype == "scarf" and feels >= 10:
        s -= 2
    return s, notes


def item_style_score(g: Garment, frange: tuple[int, int]) -> float:
    """Encaje old money de una prenda suelta (color, patrón, logo, subtipo, formalidad)."""
    s = SUBTYPE_STYLE.get(g.subtype, 0.0)
    s += 1.5 * (color_score(g.primary_color) - 0.75)
    pat = (g.pattern or "solid").lower()
    if pat in PATTERNS_LOUD:
        s -= 1.5
    if g.logo:
        s -= 0.8
    lo, hi = frange
    if g.category != "accessory":
        if g.formality < lo:
            s -= 0.7 * (lo - g.formality)
        elif g.formality > hi:
            s -= 0.5 * (g.formality - hi)
    return s


# Texturas que no cuentan como "estampado" a efectos de no mezclar patrones.
TEXTURES = {"solid", "", "plain", "liso", "oxford", "textured", "corduroy", "cable-knit", "cable", "pique"}


def is_patterned(g: Garment) -> bool:
    """Estampado visible (rayas, cuadros, etc.). Las texturas lisas no cuentan."""
    return (g.pattern or "solid").lower() not in TEXTURES
