"""Build data/processed/games.json from the Messenger dump + manual overrides."""

import json
import warnings
from datetime import date
from pathlib import Path

from football_analytics.messenger_client import _image_uri
from football_analytics.models import Game, Team
from football_analytics.parsers.messenger import (
    TeamSelection,
    _extract_teams,
    _ocr_image,
    _parse_message_dicts,
)

_DUMP = Path("data/raw/messenger_messages.json")
_OCR_DIR = Path("data/raw/ocr_debug")
_OUT = Path("data/processed/games.json")

# Manual overrides: game date → list of image/text paths in _OCR_DIR.
# Used when the Messenger dump has no image for that week.
_MANUAL: dict[date, list[str]] = {
    date(2025, 12, 22): ["12-22-25.jpg"],
    date(2026, 1, 12): ["12-01-26.jpg"],
    date(2026, 3, 23): ["23-03-26.jpg"],
    date(2026, 4, 20): ["20-04-26.txt"],
}


def _parse_manual(game_date: date, filenames: list[str]) -> TeamSelection | None:
    texts: list[str] = []
    for fname in filenames:
        path = _OCR_DIR / fname
        if path.suffix == ".txt":
            texts.append(path.read_text())
        else:
            t = _ocr_image(str(path))
            if t:
                texts.append(t)
    combined = "\n".join(texts)
    result = _extract_teams(combined)
    if result is None:
        return None
    return TeamSelection(game_date=game_date, brancos=result[0], pretos=result[1])


def load_selections() -> list[TeamSelection]:
    # Parse the Messenger dump
    data = json.loads(_DUMP.read_text())
    participants: dict[str, str] = data.get("participants", {})
    normalized = []
    for node in data["messages"]:
        ts_ms = int(node.get("timestamp_precise", 0))
        sender_id = (node.get("message_sender") or {}).get("id", "")
        text = ((node.get("message") or {}).get("text") or "")
        blobs = node.get("blob_attachments") or []
        entry: dict = {
            "type": "Generic",
            "timestamp_ms": ts_ms,
            "sender_name": participants.get(sender_id, ""),
        }
        if text:
            entry["content"] = text
        if blobs:
            uri = _image_uri(blobs[0])
            if uri:
                entry["photos"] = [{"uri": uri}]
        normalized.append(entry)

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        selections = _parse_message_dicts(normalized)

    # Apply manual overrides (add if not already parsed)
    parsed_dates = {s["game_date"] for s in selections}
    for game_date, filenames in _MANUAL.items():
        if game_date not in parsed_dates:
            sel = _parse_manual(game_date, filenames)
            if sel:
                selections.append(sel)

    # Only keep Mondays
    return [s for s in selections if s["game_date"].weekday() == 0]


def to_game(sel: TeamSelection) -> Game:
    return Game(
        date=sel["game_date"],
        team_a=sel["brancos"],
        team_b=sel["pretos"],
    )


def main() -> None:
    selections = load_selections()
    games = sorted([to_game(s) for s in selections], key=lambda g: g.date)

    output = [
        {
            "date": g.date.isoformat(),
            "brancos": {
                "players": [p.name for p in g.team_a.players],
                "score": g.team_a.score,
            },
            "pretos": {
                "players": [p.name for p in g.team_b.players],
                "score": g.team_b.score,
            },
        }
        for g in games
    ]

    _OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Saved {len(games)} games → {_OUT}")
    for g in games:
        nb = len(g.team_a.players)
        np = len(g.team_b.players)
        print(f"  {g.date}  brancos={nb}  pretos={np}")


if __name__ == "__main__":
    main()
