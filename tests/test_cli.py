import json
from pathlib import Path

from vestidor.cli import main

from .conftest import make_photo


def run(capsys, home, *args):
    code = main(["--home", str(home), *args])
    return code, json.loads(capsys.readouterr().out)


def test_full_flow(tmp_path, capsys):
    home = tmp_path / "data"
    photos = [
        ("top", "oxford", "light-blue", (170, 200, 230, 255), 2, 3),
        ("top", "cable-sweater", "cream", (240, 232, 210, 255), 4, 3),
        ("outerwear", "overcoat", "camel", (190, 150, 100, 255), 4, 4),
        ("bottom", "chinos", "beige", (215, 200, 170, 255), 2, 3),
        ("shoes", "loafers", "brown", (110, 70, 40, 255), 2, 4),
        ("accessory", "belt", "brown", (100, 60, 30, 255), 1, 3),
    ]
    ids = []
    for i, (cat, st, color, rgba, warmth, form) in enumerate(photos):
        p = make_photo(tmp_path / f"p{i}.png", rgba)
        code, res = run(capsys, home, "add", str(p), "--category", cat, "--subtype", st, "--colors", color,
                        "--warmth", str(warmth), "--formality", str(form), "--no-bg")
        assert code == 0, res
        assert Path(res["garment"]["image"]).exists()
        ids.append(res["garment"]["id"])
    assert ids[:3] == ["top-001", "top-002", "out-001"]

    code, res = run(capsys, home, "suggest", "--date", "2026-11-16", "--feels", "8", "--n", "1")
    assert code == 0, res
    outfit = res["outfits"][0]
    assert Path(outfit["collage"]).exists()
    chosen = [i["id"] for i in outfit["items"]]

    code, res = run(capsys, home, "approve", *chosen, "--date", "2026-11-16")
    assert code == 0
    tops = [i for i in chosen if i.startswith("top-")]
    assert tops and set(res["locked_until"]) == set(tops)

    code, res = run(capsys, home, "locked", "--date", "2026-11-20")
    assert {x["id"] for x in res["locked"]} == set(tops)

    code, res = run(capsys, home, "approve", tops[0], "--date", "2026-11-18")
    assert code == 1 and res["code"] == "LOCKED"

    # pantalones sí se pueden repetir
    code, res = run(capsys, home, "approve", "bot-001", "--date", "2026-11-17")
    assert code == 0

    code, res = run(capsys, home, "render", *chosen, "--date", "2026-11-16", "--feels", "8")
    assert code == 0 and Path(res["collage"]).exists()


def test_suggest_without_location(tmp_path, capsys):
    code, res = run(capsys, tmp_path / "d", "suggest")
    assert code == 1 and res["code"] == "LOCATION_NOT_SET"
