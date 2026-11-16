from datetime import date

from vestidor.rotation import locked_items, previous_entry


def test_tops_locked_for_seven_days(wardrobe):
    history = [{"date": "2026-11-10", "items": ["top-001", "bot-001", "sho-001", "out-001"]}]
    assert locked_items(history, wardrobe, date(2026, 11, 10)) == {"top-001": "2026-11-17"}
    assert "top-001" in locked_items(history, wardrobe, date(2026, 11, 16))
    assert locked_items(history, wardrobe, date(2026, 11, 17)) == {}


def test_pants_shoes_outerwear_never_locked(wardrobe):
    history = [{"date": "2026-11-10", "items": ["bot-001", "sho-001", "out-001", "acc-001"]}]
    assert locked_items(history, wardrobe, date(2026, 11, 11)) == {}


def test_future_entries_do_not_lock_past(wardrobe):
    history = [{"date": "2026-11-20", "items": ["top-002"]}]
    assert locked_items(history, wardrobe, date(2026, 11, 18)) == {}


def test_custom_days(wardrobe):
    history = [{"date": "2026-11-10", "items": ["top-002"]}]
    assert locked_items(history, wardrobe, date(2026, 11, 12), days=2) == {}


def test_previous_entry():
    history = [{"date": "2026-11-10", "items": []}, {"date": "2026-11-12", "items": []}]
    assert previous_entry(history, date(2026, 11, 12))["date"] == "2026-11-10"
    assert previous_entry(history, date(2026, 11, 1)) is None
