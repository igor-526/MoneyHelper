from core.icons import ALLOWED_ICONS, list_icon_names

EXPECTED_ICONS = {
    "banknote",
    "briefcase",
    "bus",
    "car",
    "coins",
    "credit-card",
    "film",
    "gamepad-2",
    "gift",
    "graduation-cap",
    "heart-pulse",
    "house",
    "landmark",
    "piggy-bank",
    "plane",
    "shirt",
    "shopping-cart",
    "smartphone",
    "trending-down",
    "trending-up",
    "utensils",
    "wallet",
    "zap",
}

UI_ICONS = {"settings", "sun", "moon", "log-out", "download", "share", "wifi-off"}


def test_allowed_icons_contains_expected_names() -> None:
    assert ALLOWED_ICONS == EXPECTED_ICONS


def test_allowed_icons_excludes_ui_icons() -> None:
    assert ALLOWED_ICONS.isdisjoint(UI_ICONS)


def test_list_icon_names_is_sorted_without_duplicates() -> None:
    names = list_icon_names()

    assert names == sorted(EXPECTED_ICONS)
    assert len(names) == len(set(names))
