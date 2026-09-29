import json
from pathlib import Path

_ICONS_PATH = Path(__file__).parent / "icons.json"

ALLOWED_ICONS: frozenset[str] = frozenset(json.loads(_ICONS_PATH.read_text(encoding="utf-8")))


def list_icon_names() -> list[str]:
    return sorted(ALLOWED_ICONS)
