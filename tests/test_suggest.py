from datetime import date

from vestidor.suggest import suggest
from vestidor.weather import manual


def ids(outfit):
    return {i["id"] for i in outfit["items"]}


def test_cold_day_needs_coat(wardrobe):
    res = suggest(wardrobe, manual(date(2026, 11, 16), feels=3), n=3)
    assert res["ok"]
    best = ids(res["outfits"][0])
    assert "out-002" in best          # abrigo camel
    assert "bot-003" not in best      # nada de bermudas
    assert "acc-002" in best          # bufanda


def test_hot_day_light_layers(wardrobe):
    res = suggest(wardrobe, manual(date(2026, 7, 16), feels=30), n=3)
    best = res["outfits"][0]
    cats = [i["category"] for i in best["items"]]
    assert "outerwear" not in cats
    assert not ids(best) & {"top-003", "top-004", "top-005"}


def test_hoodie_with_logo_avoided(wardrobe):
    res = suggest(wardrobe, manual(date(2026, 11, 16), feels=15), n=3)
    for o in res["outfits"]:
        assert "top-005" not in ids(o)


def test_locked_tops_excluded(wardrobe):
    locked = {"top-001": "2026-11-20", "top-003": "2026-11-20"}
    res = suggest(wardrobe, manual(date(2026, 11, 16), feels=14), n=3, locked=locked)
    for o in res["outfits"]:
        assert not ids(o) & set(locked)


def test_options_have_different_tops(wardrobe):
    res = suggest(wardrobe, manual(date(2026, 11, 16), feels=14), n=3)
    tops = [frozenset(i["id"] for i in o["items"] if i["category"] == "top") for o in res["outfits"]]
    assert len(res["outfits"]) == 3
    for a in range(3):
        for b in range(a + 1, 3):
            assert not tops[a] & tops[b]


def test_rain_avoids_suede(wardrobe):
    res = suggest(wardrobe, manual(date(2026, 11, 16), feels=12, rain_prob=80), n=1)
    best = ids(res["outfits"][0])
    assert "sho-002" not in best
    assert "out-003" in best   # barbour encerado


def test_formal_occasion_prefers_loafers(wardrobe):
    res = suggest(wardrobe, manual(date(2026, 5, 16), feels=20), occasion="cena", n=1)
    best = ids(res["outfits"][0])
    assert "sho-001" in best
    assert "bot-002" not in best


def test_all_tops_locked_is_error(wardrobe):
    locked = {g.id: "2026-12-01" for g in wardrobe if g.category == "top"}
    res = suggest(wardrobe, manual(date(2026, 11, 16), feels=14), locked=locked)
    assert not res["ok"]
