from vestidor import style


def test_warmth_bands():
    assert style.warmth_target(30)[0] == (1, 2)
    assert style.warmth_target(14)[0] == (4, 6)
    assert style.warmth_target(0)[0] == (10, 15)


def test_occasion_mapping():
    assert style.occasion_range(None)[0] == (2, 3)
    assert style.occasion_range("Cena con amigos")[0] == (3, 5)
    assert style.occasion_range("me voy a la uni")[0] == (3, 4)
    assert style.occasion_range("partido en el club de tenis")[1] == "country club"
    assert style.occasion_range("algo raro")[0] == (2, 3)


def test_color_aliases():
    assert style.normalize_color("Azul marino") == "navy"
    assert style.normalize_color("marrón") == "brown"
    assert style.color_score("navy") > style.color_score("orange")
