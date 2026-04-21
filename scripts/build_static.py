"""Generate a static docs/index.html from the current data."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jinja2 import Environment, FileSystemLoader

from football_analytics.web import build_player_stats, load_garmin_stats, load_processed_games


def main() -> None:
    garmin = {r["date"]: r for r in load_garmin_stats()}
    processed = load_processed_games()
    leaderboard = build_player_stats(processed)

    from datetime import date, timedelta

    games = []
    for g in sorted(processed, key=lambda x: x["date"]):
        d = g["date"]
        activity = garmin.get(d) or garmin.get(
            (date.fromisoformat(d) + timedelta(days=1)).isoformat()
        ) or {}
        b_score = g.get("brancos", {}).get("score", 0)
        p_score = g.get("pretos", {}).get("score", 0)
        games.append({
            "date": d,
            "brancos_score": b_score,
            "pretos_score": p_score,
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
    template = env.get_template("index.html")

    html = template.render(
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
