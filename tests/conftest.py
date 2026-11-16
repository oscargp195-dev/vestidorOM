import pytest
from PIL import Image, ImageDraw

from vestidor.models import Garment
from vestidor.storage import Store


def make_photo(path, color):
    img = Image.new("RGBA", (400, 500), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((60, 40, 340, 460), radius=40, fill=color)
    img.save(path)
    return path


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "data")


@pytest.fixture
def wardrobe():
    G = Garment
    return [
        G("top-001", "Oxford azul claro", "top", "oxford", ["light-blue"], warmth=2, formality=3),
        G("top-002", "Polo navy", "top", "polo", ["navy"], warmth=2, formality=2),
        G("top-003", "Jersey ochos crema", "top", "cable-sweater", ["cream"], "cable-knit", "lana", 4, 3),
        G("top-004", "Quarter-zip gris", "top", "quarter-zip", ["grey"], warmth=3, formality=3),
        G("top-005", "Sudadera logo roja", "top", "hoodie", ["red"], "graphic", warmth=3, formality=1, logo=True),
        G("top-006", "Camiseta blanca", "top", "t-shirt", ["white"], warmth=1, formality=2),
        G("out-001", "Blazer navy", "outerwear", "blazer", ["navy"], warmth=2, formality=4),
        G("out-002", "Abrigo camel", "outerwear", "overcoat", ["camel"], material="lana", warmth=4, formality=4),
        G("out-003", "Barbour verde", "outerwear", "waxed-jacket", ["olive"], warmth=3, formality=3, rain_ok=True),
        G("bot-001", "Chinos beige", "bottom", "chinos", ["beige"], warmth=2, formality=3),
        G("bot-002", "Vaqueros", "bottom", "jeans", ["denim"], warmth=2, formality=2),
        G("bot-003", "Bermudas navy", "bottom", "shorts", ["navy"], warmth=1, formality=2),
        G("sho-001", "Mocasines marrones", "shoes", "loafers", ["brown"], material="cuero", formality=4),
        G("sho-002", "Desert boots ante", "shoes", "desert-boots", ["tan"], material="ante", formality=3),
        G("sho-003", "Zapatillas blancas", "shoes", "sneakers", ["white"], formality=2),
        G("acc-001", "Cinturon marron", "accessory", "belt", ["brown"]),
        G("acc-002", "Bufanda gris", "accessory", "scarf", ["grey"]),
    ]
