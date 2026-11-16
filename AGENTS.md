# AGENTS.md — VestidorOM

Este repo es el armario personal de Oscar y un estilista old money para agentes de IA.

**Instrucciones completas para el agente: [`skills/vestidor/SKILL.md`](skills/vestidor/SKILL.md).** Léelo antes de
usar la herramienta.

Resumen:
- CLI: `vestidor` (o `.venv/bin/vestidor`). Salida siempre JSON (`ok`, `code`, `error`).
- Fotos → `vestidor add FOTO --category ... --subtype ... --colors ... --warmth N --formality N` (quita el fondo).
- Outfit del día → `vestidor suggest [--date] [--occasion]` → enviar `collage` (JPG) por el chat →
  al aprobar `vestidor approve <ids> --date <fecha>`.
- Regla: las partes de arriba (`top`) aprobadas se bloquean 7 días; pantalones, abrigos, calzado y accesorios no.
- Datos (fotos, `wardrobe.json`, `history.json`, `config.json`) en `data/` o `$VESTIDOR_HOME`. No se suben a git.

## Desarrollo
```bash
.venv/bin/python -m pytest -q
```
Código en `vestidor/`: `cli.py` (comandos), `suggest.py` (motor), `style.py` (reglas old money y clima→capas),
`rotation.py` (bloqueo 7 días), `weather.py` (Open-Meteo), `collage.py` (imagen), `background.py` (rembg).
