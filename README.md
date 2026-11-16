# VestidorOM

Estilista personal **old money / casual arreglado** pensado para que lo use un agente de IA (OpenBot) en tu PC Linux.

- Le pasas fotos de tu ropa al agente → las etiqueta, **quita el fondo** y las guarda en tu armario local.
- Le preguntas qué ponerte → mira el **clima real** de tu ciudad (Open-Meteo, sin API key), la ocasión que le digas
  y tu armario, y te manda por el chat un **collage flat-lay** con el outfit.
- Cuando apruebas un outfit, las **partes de arriba** (camisetas, polos, camisas, jerseys, sudaderas...) quedan
  **bloqueadas 7 días**. Los pantalones (y abrigos, zapatos, accesorios) se pueden repetir.

## Instalación (Linux)

```bash
git clone https://github.com/oscargp195-dev/vestidorOM.git
cd vestidorOM
python3 -m venv .venv
.venv/bin/pip install -e ".[bg]"        # [bg] = rembg para quitar fondos (descarga un modelo ~170 MB la 1ª vez)
.venv/bin/vestidor info                 # comprueba que funciona
```

Para tenerlo en el PATH (opcional): `ln -s "$PWD/.venv/bin/vestidor" ~/.local/bin/vestidor`

Requisitos: Python ≥ 3.10. Si no quieres quitar fondos, instala sin `[bg]` (`pip install -e .`).
Si el collage sale con una fuente básica, instala `fonts-dejavu` (`sudo apt install fonts-dejavu`).

## Conectar con OpenBot

La skill está en [`skills/vestidor/SKILL.md`](skills/vestidor/SKILL.md) (formato estándar `SKILL.md` con frontmatter
`name`/`description`). Enlázala en la carpeta de skills de tu agente, por ejemplo:

```bash
ln -s "$PWD/skills/vestidor" ~/.openbot/skills/vestidor     # ajusta la ruta a donde OpenBot lea las skills
```

Si OpenBot usa un `AGENTS.md` o instrucciones de proyecto, apúntalo a este repo: [`AGENTS.md`](AGENTS.md) resume todo.
El agente necesita poder ejecutar comandos de shell y enviar imágenes por el chat.

## Datos

Por defecto en `data/` dentro del repo (ignorado por git). Para guardarlos en otro sitio: `export VESTIDOR_HOME=~/vestidor-data`.

```
data/
├── config.json      # ubicación, días de bloqueo
├── wardrobe.json    # prendas y etiquetas
├── history.json     # outfits aprobados
├── images/          # prendas sin fondo (PNG)
├── originals/       # fotos originales
└── outfits/         # collages generados (JPG)
```

## Comandos

| Comando | Para qué |
|---|---|
| `vestidor config set-location "Sevilla"` | Ciudad para el clima |
| `vestidor add foto.jpg --category top --subtype polo --colors navy --warmth 2 --formality 3` | Añadir prenda |
| `vestidor list [--category top] [--available]` · `show ID` · `edit ID ...` · `remove ID` | Armario |
| `vestidor weather [--date tomorrow]` | Clima |
| `vestidor suggest [--date tomorrow] [--occasion "cena"] [--n 3]` | Outfits + collages |
| `vestidor render ID ID ...` | Collage de una combinación concreta |
| `vestidor approve ID ID ... [--date]` · `unapprove [--date]` | Registrar / deshacer outfit |
| `vestidor history` · `vestidor locked` | Historial y prendas bloqueadas |

Sin conexión: añade `--feels 12 --rain 40` a `suggest`/`weather` para indicar el tiempo a mano.
`vestidor config set-lock-days 7` cambia la duración del bloqueo.

## Cómo decide

- **Clima → capas**: suma el abrigo (`warmth`) de capa base + capa intermedia + chaqueta y lo compara con un rango
  según la sensación térmica de 9:00 a 20:00. Lluvia ≥ 50 %: prefiere prendas `rain_ok` y evita ante/esparto.
- **Old money**: premia paleta neutra (navy, crema, beige, camel, marrón, gris, oliva, burdeos) y piezas clásicas
  (oxford, polo, ochos, quarter-zip, chinos, mocasines, blazer, chaqueta encerada); penaliza logos, estampados
  llamativos, hoodies y joggers, mezclar varios estampados y zapatos/cinturón de distinto tono.
- **Ocasión**: texto libre → rango de formalidad (cena/evento, trabajo/uni, boda, club de tenis, playa...).
  Por defecto, casual arreglado.
- Evita repetir pantalón/zapatos del día anterior y da opciones con partes de arriba distintas.

## Desarrollo

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```
