"""Generate a static docs/index.html from the current data."""

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent.parent
_DATA_RAW = ROOT / "data" / "raw"
_GARMIN_CSV = _DATA_RAW / "football_activities_20_april.csv"
_FOOTBALL_TYPES = {"football", "soccer", "soccer/football", "other"}


def load_garmin_stats() -> list[dict]:
    if not _GARMIN_CSV.exists():
        return []
    rows = []
    with _GARMIN_CSV.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row.get("Activity Type", "").strip().lower() not in _FOOTBALL_TYPES:
                continue
            date_str = (row.get("Date") or row.get("Start Time") or "")[:10]
            try:
                date.fromisoformat(date_str)
            except ValueError:
                continue
            rows.append({
                "date": date_str,
                "distance_km": row.get("Distance", ""),
                "calories": row.get("Calories", ""),
                "time": row.get("Time", ""),
                "moving_time": row.get("Moving Time", ""),
                "avg_hr": row.get("Avg HR", ""),
                "max_hr": row.get("Max HR", ""),
                "avg_speed": row.get("Avg Speed", ""),
                "steps": row.get("Steps", ""),
            })
    return rows


def load_processed_games() -> list[dict]:
    path = ROOT / "data" / "processed" / "games.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def build_player_stats(games: list[dict]) -> list[dict]:
    stats: dict[str, dict] = {}
    for g in games:
        b_score = g.get("brancos", {}).get("score", 0)
        p_score = g.get("pretos", {}).get("score", 0)
        if b_score > p_score:
            winners = "brancos"
        elif p_score > b_score:
            winners = "pretos"
        else:
            winners = None
        result = "draw" if winners is None else "win"

        for side in ("brancos", "pretos"):
            for player in g.get(side, {}).get("players", []):
                s = stats.setdefault(player, {"played": 0, "wins": 0, "draws": 0, "losses": 0})
                s["played"] += 1
                if result == "draw":
                    s["draws"] += 1
                elif side == winners:
                    s["wins"] += 1
                else:
                    s["losses"] += 1

    rows = []
    for player, s in stats.items():
        played = s["played"]
        win_rate = round(s["wins"] / played * 100) if played else 0
        rows.append({"player": player, "played": played, "win_rate": win_rate, **s})

    return sorted(
        [r for r in rows if r["played"] >= 3 and not r["player"].lower().startswith("amigo do")],
        key=lambda x: (-x["win_rate"], -x["wins"], -x["played"]),
    )


def main() -> None:
    garmin = {r["date"]: r for r in load_garmin_stats()}
    processed = load_processed_games()
    leaderboard = build_player_stats(processed)

    games = []
    for g in sorted(processed, key=lambda x: x["date"]):
        d = g["date"]
        activity = garmin.get(d) or garmin.get(
            (date.fromisoformat(d) + timedelta(days=1)).isoformat()
        ) or {}
        games.append({
            "date": d,
            "brancos_score": g.get("brancos", {}).get("score", 0),
            "pretos_score": g.get("pretos", {}).get("score", 0),
            "brancos_players": g.get("brancos", {}).get("players", []),
            "pretos_players": g.get("pretos", {}).get("players", []),
            "distance_km": activity.get("distance_km", ""),
            "time": activity.get("time", ""),
            "moving_time": activity.get("moving_time", ""),
            "avg_hr": activity.get("avg_hr", ""),
            "max_hr": activity.get("max_hr", ""),
            "avg_speed": activity.get("avg_speed", ""),
            "calories": activity.get("calories", ""),
            "steps": activity.get("steps", ""),
        })

    env = Environment(loader=FileSystemLoader(str(ROOT / "src" / "football_analytics" / "templates")))
    html = env.get_template("index.html").render(
        games=games,
        leaderboard=leaderboard,
        total_games=len(games),
        total_players=len(leaderboard),
        latest_game=games[-1]["date"] if games else "—",
        games_json=json.dumps(games),
        leaderboard_json=json.dumps(leaderboard),
    )

    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Built {out}  ({len(games)} games, {len(leaderboard)} players)")


if __name__ == "__main__":
    main()
