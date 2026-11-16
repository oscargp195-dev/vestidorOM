"""Collage flat-lay del outfit para mandarlo por chat."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .models import Garment

W, H = 1080, 1350
BG = (243, 238, 228)        # crema
INK = (38, 42, 54)          # azul tinta
MUTED = (120, 112, 100)
ACCENT = (27, 45, 79)       # navy

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

SERIF = ["DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
         "/usr/share/fonts/TTF/DejaVuSerif.ttf", "LiberationSerif-Regular.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", "georgia.ttf", "times.ttf"]
SANS = ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf", "LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "arial.ttf"]


def _font(candidates: list[str], size: int) -> ImageFont.ImageFont:
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _load_item(g: Garment, home: Path) -> Image.Image | None:
    if not g.image:
        return None
    p = Path(g.image)
    p = p if p.is_absolute() else home / p
    if not p.exists():
        return None
    img = Image.open(p).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    return img.crop(bbox) if bbox else img


def _paste(canvas: Image.Image, img: Image.Image | None, g: Garment, box: tuple[int, int, int, int],
           caption_font) -> None:
    x0, y0, x1, y1 = box
    caption_h = 34
    bw, bh = x1 - x0 - 24, y1 - y0 - 24 - caption_h
    draw = ImageDraw.Draw(canvas)
    if img is None:
        draw.rounded_rectangle((x0 + 12, y0 + 12, x1 - 12, y1 - 12 - caption_h), radius=18,
                               outline=MUTED, width=2)
        cx, cy = (x0 + x1) // 2, (y0 + y1 - caption_h) // 2
        draw.text((cx, cy), g.subtype or g.category, fill=MUTED, font=caption_font, anchor="mm")
    else:
        img = img.copy()
        img.thumbnail((bw, bh), Image.LANCZOS)
        px = x0 + (x1 - x0 - img.width) // 2
        py = y0 + 12 + (bh - img.height) // 2
        pad = 30
        alpha = Image.new("L", (img.width + 2 * pad, img.height + 2 * pad), 0)
        alpha.paste(img.getchannel("A").point(lambda a: int(a * 0.28)), (pad, pad))
        shadow = Image.new("RGBA", alpha.size, (60, 50, 40, 0))
        shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(10)))
        sx, sy = px + 8 - pad, py + 12 - pad
        canvas.alpha_composite(shadow.crop((max(0, -sx), max(0, -sy), shadow.width, shadow.height)),
                               (max(0, sx), max(0, sy)))
        canvas.alpha_composite(img, (px, py))
    draw.text(((x0 + x1) // 2, y1 - caption_h // 2 - 4), g.name[:38], fill=MUTED, font=caption_font, anchor="mm")


def _header(draw: ImageDraw.ImageDraw, day: date | None, weather: dict | None, title: str | None) -> None:
    title_font = _font(SERIF, 54)
    sub_font = _font(SANS, 26)
    heading = title or "Outfit del día"
    draw.text((60, 52), heading, fill=ACCENT, font=title_font)
    parts = []
    if day:
        parts.append(f"{DIAS[day.weekday()]} {day.day} {MESES[day.month - 1]}")
    if weather:
        if weather.get("location"):
            parts.append(weather["location"])
        if weather.get("source") != "manual" and weather.get("tmin") is not None:
            parts.append(f"{weather['tmin']:.0f}–{weather['tmax']:.0f} °C")
        parts.append(f"sensación {weather['feels']:.0f} °C")
        if weather.get("rain_prob"):
            parts.append(f"lluvia {weather['rain_prob']:.0f} %")
        if weather.get("description") and weather["description"] != "manual":
            parts.append(weather["description"])
    line = "  ·  ".join(parts)
    size = 26
    while size > 14 and draw.textlength(line, font=sub_font) > W - 124:
        size -= 1
        sub_font = _font(SANS, size)
    draw.text((62, 126), line, fill=INK, font=sub_font)
    draw.line((60, 172, W - 60, 172), fill=(214, 204, 186), width=2)


def render(items: list[Garment], out_path: str | Path, home: str | Path, day: date | None = None,
           weather: dict | None = None, title: str | None = None) -> Path:
    home = Path(home)
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    draw = ImageDraw.Draw(canvas)
    _header(draw, day, weather, title)
    cap = _font(SANS, 22)

    order = {"outerwear": 0, "mid": 1, "base": 2}
    uppers = sorted([g for g in items if g.category in ("outerwear", "top")], key=lambda g: order[g.layer])
    bottoms = [g for g in items if g.category == "bottom"]
    shoes = [g for g in items if g.category == "shoes"]
    accs = [g for g in items if g.category == "accessory"]

    top_y, bot_y = 196, H - 40
    left = (40, 580)
    right = (580, W - 40)

    # Columna izquierda: capas de arriba apiladas
    if uppers:
        h = (bot_y - top_y) // len(uppers)
        for i, g in enumerate(uppers):
            _paste(canvas, _load_item(g, home), g, (left[0], top_y + i * h, left[1], top_y + (i + 1) * h), cap)

    # Columna derecha: pantalón, zapatos, accesorios
    blocks = [(g, 0.60) for g in bottoms] + [(g, 0.26) for g in shoes]
    acc_h = 0.16 if accs else 0
    total = sum(f for _, f in blocks) + acc_h or 1
    y = top_y
    span = bot_y - top_y
    for g, f in blocks:
        h = int(span * f / total)
        _paste(canvas, _load_item(g, home), g, (right[0], y, right[1], y + h), cap)
        y += h
    if accs:
        h = bot_y - y
        w = (right[1] - right[0]) // len(accs)
        for i, g in enumerate(accs):
            _paste(canvas, _load_item(g, home), g, (right[0] + i * w, y, right[0] + (i + 1) * w, y + h), cap)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path, format="JPEG", quality=90)
    return out_path
