"""Limpieza de fondo de las fotos de prendas."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps

MAX_SIDE = 1600


def rembg_available() -> bool:
    try:
        import rembg  # noqa: F401
        return True
    except Exception:
        return False


def _load(src: Path) -> Image.Image:
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)  # respeta la orientación de la foto del móvil
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    return img


def process(src: str | Path, dst: str | Path, remove_bg: bool = True) -> dict:
    """Guarda `src` como PNG RGBA en `dst`, quitando el fondo si es posible.

    Devuelve {"background_removed": bool, "warning": str | None}.
    """
    src, dst = Path(src), Path(dst)
    img = _load(src)
    warning = None
    removed = False
    if remove_bg:
        if rembg_available():
            from rembg import remove

            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="PNG")
            out = remove(buf.getvalue())
            img = Image.open(io.BytesIO(out))
            removed = True
        else:
            warning = "rembg no está instalado (pip install -e '.[bg]'): se guarda la foto sin quitar el fondo"
    img = img.convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, format="PNG", optimize=True)
    return {"background_removed": removed, "warning": warning}
