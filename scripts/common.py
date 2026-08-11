from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_settings() -> dict:
    return json.loads((ROOT / "config/settings.json").read_text())


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def contains_any(text: str, terms: list[str]) -> bool:
    low = (text or "").lower()
    return any(term in low for term in terms)


PROJECT_ID_RE = re.compile(r"\b(20\d{2})-(\d{4})\b")


def extract_project_id(text: str) -> str:
    match = PROJECT_ID_RE.search(text or "")
    return match.group(0) if match else ""


def next_project_id(existing_ids: list[str], year: int) -> str:
    highest = 0
    prefix = f"{year}-"
    for project_id in existing_ids:
        if not project_id or not str(project_id).startswith(prefix):
            continue
        match = PROJECT_ID_RE.fullmatch(str(project_id).strip())
        if match:
            highest = max(highest, int(match.group(2)))
    return f"{year}-{highest + 1:04d}"


DESIGN_TYPE_RULES = [
    ("Channel Letters", ["channel letter", "channel letters", "3d letter", "metal letter", "front lit", "back lit"]),
    ("Window Graphics", ["window graphic", "window decal", "window vinyl", "glass graphic"]),
    ("Vinyl Graphics", ["vinyl", "decal", "door graphic", "sticker"]),
    ("Monument Sign", ["monument", "ground sign"]),
    ("Lobby Sign", ["lobby", "interior logo"]),
    ("Wayfinding", ["wayfinding", "directional"]),
    ("Cabinet Sign", ["cabinet", "light box", "lightbox"]),
    ("Pylon Sign", ["pylon"]),
    ("ADA Signage", ["ada"]),
    ("Awning", ["awning"]),
    ("Blade Sign", ["blade sign", "projecting sign"]),
    ("Canopy", ["canopy"]),
    ("Menu Board", ["menu board", "drive thru", "drive-thru"]),
    ("LED Retrofit", ["led replacement", "retrofit", "led repair"]),
    ("Storefront Sign", ["storefront", "front building", "building sign", "exterior sign", "fascia"]),
]


def normalize_design_type(text: str) -> str:
    low = (text or "").lower()
    for design_type, terms in DESIGN_TYPE_RULES:
        if any(term in low for term in terms):
            return design_type
    return "Unknown / Review"
