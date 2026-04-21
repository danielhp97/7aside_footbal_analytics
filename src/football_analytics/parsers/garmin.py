"""Parse game data exported from Garmin Connect activities."""

import csv
import re
from datetime import date
from pathlib import Path
from typing import TypedDict

from football_analytics.models import Game, Team, Player

# Activity types Garmin uses for football / soccer sessions
_FOOTBALL_TYPES = {"football", "soccer", "soccer/football", "other"}

# Notes field conventions (case-insensitive):
#   Score:   "3-2" or "3 - 2" or "Team A 3 - 2 Team B"
#   Team A:  "team a: Alice, Bob, Charlie"
#   Team B:  "team b: Dave, Eve, Frank"
#   Location: "location: Victoria Park"
_SCORE_RE = re.compile(
    r"(?:team\s*a\s+)?(\d+)\s*[-–]\s*(\d+)(?:\s+team\s*b)?", re.IGNORECASE
)
_TEAM_A_RE = re.compile(r"team\s*a\s*:\s*(.+)", re.IGNORECASE)
_TEAM_B_RE = re.compile(r"team\s*b\s*:\s*(.+)", re.IGNORECASE)
_LOCATION_RE = re.compile(r"location\s*:\s*(.+)", re.IGNORECASE)


class _ParsedNotes(TypedDict, total=False):
    score_a: int
    score_b: int
    players_a: list[Player]
    players_b: list[Player]
    location: str


def _parse_players(raw: str) -> list[Player]:
    return [Player(name=n.strip()) for n in raw.split(",") if n.strip()]


def _parse_notes(notes: str) -> _ParsedNotes:
    result: _ParsedNotes = {}
    for line in notes.splitlines():
        line = line.strip()
        if m := _SCORE_RE.search(line):
            result["score_a"] = int(m.group(1))
            result["score_b"] = int(m.group(2))
        if m := _TEAM_A_RE.match(line):
            result["players_a"] = _parse_players(m.group(1))
        if m := _TEAM_B_RE.match(line):
            result["players_b"] = _parse_players(m.group(1))
        if m := _LOCATION_RE.match(line):
            result["location"] = m.group(1).strip()
    return result


def parse_garmin_export(path: Path) -> list[Game]:
    """
    Load game records from a Garmin Connect CSV export.

    Export from Garmin Connect → Activities → Export CSV.
    Only rows whose Activity Type matches a football/soccer type are loaded.

    Encode game details in the Notes field using these lines:
        3 - 2                      (score, Team A first)
        Team A: Alice, Bob, Charlie
        Team B: Dave, Eve, Frank
        Location: Victoria Park    (optional)
    """
    games: list[Game] = []

    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            activity_type = row.get("Activity Type", "").strip().lower()
            if activity_type not in _FOOTBALL_TYPES:
                continue

            raw_date = (row.get("Date") or row.get("Start Time") or "")[:10]
            try:
                activity_date = date.fromisoformat(raw_date)
            except ValueError:
                continue

            notes = row.get("Notes", "") or ""
            parsed = _parse_notes(notes)

            team_a = Team(
                name="Team A",
                score=parsed.get("score_a", 0),
                players=parsed.get("players_a", []),
            )
            team_b = Team(
                name="Team B",
                score=parsed.get("score_b", 0),
                players=parsed.get("players_b", []),
            )

            games.append(
                Game(
                    date=activity_date,
                    location=parsed.get("location"),
                    team_a=team_a,
                    team_b=team_b,
                    notes=notes or None,
                )
            )

    return games
