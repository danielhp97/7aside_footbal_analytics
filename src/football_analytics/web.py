"""FastAPI web dashboard for football analytics."""

import csv
import json
import re
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

_ROOT = Path(__file__).parent.parent.parent
_DATA_RAW = _ROOT / "data" / "raw"
_GARMIN_CSV = _DATA_RAW / "football_activities_20_april.csv"
_MESSENGER_JSON = _DATA_RAW / "messenger_messages.json"

_FOOTBALL_TYPES = {"football", "soccer", "soccer/football", "other"}
_PT = timezone(timedelta(hours=-8))

_BRANCOS_RE = re.compile(
    r"^(?:brancos?|whites?|bibs?|team\s*a)\s*[:\-]\s*(.+)", re.IGNORECASE | re.MULTILINE
)
_PRETOS_RE = re.compile(
    r"^(?:pretos?|vermelhos?|blacks?|reds?|skins?|team\s*b)\s*[:\-]\s*(.+)",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_players(raw: str) -> list[str]:
    if "," in raw:
        return [n.strip() for n in raw.split(",") if n.strip()]
    return [n.strip() for n in raw.split() if n.strip()]


def _game_monday(ts_ms: int) -> date | None:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=_PT)
    wd = dt.weekday()
    if wd == 0:
        return dt.date() if dt.hour < 20 else None
    if wd in (4, 5, 6):
        return dt.date() + timedelta(days=(7 - wd) % 7)
    return None


def _extract_teams_from_text(text: str) -> dict[str, list[str]] | None:
    bm = _BRANCOS_RE.search(text)
    pm = _PRETOS_RE.search(text)
    if bm and pm:
        return {
            "brancos": _parse_players(bm.group(1)),
            "pretos": _parse_players(pm.group(1)),
        }
    return None


def load_garmin_stats() -> list[dict[str, Any]]:
    if not _GARMIN_CSV.exists():
        return []
    rows = []
    with _GARMIN_CSV.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("Activity Type", "").strip().lower() not in _FOOTBALL_TYPES:
                continue
            date_str = (row.get("Date") or row.get("Start Time") or "")[:10]
            try:
                date.fromisoformat(date_str)
            except ValueError:
                continue
            rows.append(
                {
                    "date": date_str,
                    "title": row.get("Title", ""),
                    "distance_km": row.get("Distance", ""),
                    "calories": row.get("Calories", ""),
                    "time": row.get("Time", ""),
                    "moving_time": row.get("Moving Time", ""),
                    "avg_hr": row.get("Avg HR", ""),
                    "max_hr": row.get("Max HR", ""),
                    "avg_speed": row.get("Avg Speed", ""),
                    "max_speed": row.get("Max Speed", ""),
                    "steps": row.get("Steps", ""),
                    "aerobic_te": row.get("Aerobic TE", ""),
                }
            )
    return sorted(rows, key=lambda r: r["date"])


def load_processed_games() -> list[dict[str, Any]]:
    path = _ROOT / "data" / "processed" / "games.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_processed_games(games: list[dict[str, Any]]) -> None:
    path = _ROOT / "data" / "processed" / "games.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(games, indent=2, ensure_ascii=False), encoding="utf-8")


def build_player_stats(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, int]] = {}

    for g in games:
        b_score = g.get("brancos", {}).get("score", 0)
        p_score = g.get("pretos", {}).get("score", 0)
        if b_score > p_score:
            winners, losers = "brancos", "pretos"
            result = "win"
        elif p_score > b_score:
            winners, losers = "pretos", "brancos"
            result = "win"
        else:
            winners, losers = None, None
            result = "draw"

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
        rows.append({
            "player": player,
            "played": played,
            "wins": s["wins"],
            "draws": s["draws"],
            "losses": s["losses"],
            "win_rate": win_rate,
        })

    return sorted(
        [
            r for r in rows
            if r["played"] >= 3 and not r["player"].lower().startswith("amigo do")
        ],
        key=lambda x: (-x["win_rate"], -x["wins"], -x["played"]),
    )


app = FastAPI(title="Football Analytics")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    garmin = {r["date"]: r for r in load_garmin_stats()}
    processed = load_processed_games()
    leaderboard = build_player_stats(processed)

    # Merge processed games with Garmin activity stats
    games = []
    for g in sorted(processed, key=lambda x: x["date"]):
        d = g["date"]
        activity = garmin.get(d) or garmin.get(
            # game date is Monday; Garmin sometimes records the next day
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

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "games": games,
            "leaderboard": leaderboard,
            "total_games": len(games),
            "total_players": len(leaderboard),
            "latest_game": games[-1]["date"] if games else "—",
            "games_json": json.dumps(games),
            "leaderboard_json": json.dumps(leaderboard),
        },
    )


@app.post("/games")
async def add_game(
    date_str: str = Form(default="", alias="date"),
    text: str = Form(default=""),
    brancos_score: str = Form(default=""),
    pretos_score: str = Form(default=""),
    image: UploadFile | None = File(default=None),
) -> JSONResponse:
    from football_analytics.parsers.messenger import _extract_teams, _ocr_image  # noqa: PLC2701

    # Parse date (default to today)
    if date_str:
        try:
            game_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(400, "Invalid date format, expected YYYY-MM-DD")
    else:
        game_date = date.today()

    # Parse optional scores
    b_score = int(brancos_score) if brancos_score.strip().isdigit() else None
    p_score = int(pretos_score) if pretos_score.strip().isdigit() else None

    # Extract teams from image or text
    teams = None
    if image and image.filename:
        suffix = Path(image.filename).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(image.file, tmp)
            tmp_path = tmp.name
        try:
            ocr_text = _ocr_image(tmp_path)
            if ocr_text:
                teams = _extract_teams(ocr_text)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    if teams is None and text.strip():
        teams = _extract_teams(text)

    if teams is None:
        raise HTTPException(400, "Could not parse team lineups — check the format (e.g. 'Brancos: Alice, Bob')")

    brancos_team, pretos_team = teams

    game_entry: dict[str, Any] = {
        "date": game_date.isoformat(),
        "brancos": {
            "players": [p.name for p in brancos_team.players],
            "score": b_score if b_score is not None else 0,
        },
        "pretos": {
            "players": [p.name for p in pretos_team.players],
            "score": p_score if p_score is not None else 0,
        },
    }

    # Upsert into games.json
    games = load_processed_games()
    idx = next((i for i, g in enumerate(games) if g["date"] == game_date.isoformat()), None)
    if idx is not None:
        existing = games[idx]
        # Preserve existing scores when none supplied
        if b_score is None:
            game_entry["brancos"]["score"] = existing.get("brancos", {}).get("score", 0)
        if p_score is None:
            game_entry["pretos"]["score"] = existing.get("pretos", {}).get("score", 0)
        games[idx] = game_entry
        action = "updated"
    else:
        games.append(game_entry)
        games.sort(key=lambda g: g["date"])
        action = "created"

    save_processed_games(games)
    return JSONResponse({
        "status": "ok",
        "action": action,
        "date": game_date.isoformat(),
        "brancos": game_entry["brancos"]["players"],
        "pretos": game_entry["pretos"]["players"],
    })


_PADRE_ALIASES = {"padre", "padreco"}


@app.post("/games/sync-garmin")
async def sync_garmin_scores() -> JSONResponse:
    from football_analytics.garmin_client import fetch_games as garmin_fetch

    games = load_processed_games()
    if not games:
        return JSONResponse({"status": "ok", "updated": 0, "total": 0})

    dates = [date.fromisoformat(g["date"]) for g in games]
    try:
        garmin_games = garmin_fetch(min(dates), max(dates))
    except Exception as exc:
        raise HTTPException(500, f"Garmin error: {exc}")

    score_by_date = {g.date: (g.team_a.score, g.team_b.score) for g in garmin_games}

    updated = 0
    for game in games:
        game_date = date.fromisoformat(game["date"])
        scores = score_by_date.get(game_date) or score_by_date.get(game_date + timedelta(days=1))
        if scores is None:
            continue
        score_my, score_opp = scores

        padre_side = next(
            (side for side in ("brancos", "pretos")
             if any(p.lower() in _PADRE_ALIASES for p in game.get(side, {}).get("players", []))),
            None,
        )

        if padre_side == "brancos":
            game["brancos"]["score"] = score_my
            game["pretos"]["score"] = score_opp
        elif padre_side == "pretos":
            game["pretos"]["score"] = score_my
            game["brancos"]["score"] = score_opp
        else:
            game["brancos"]["score"] = score_my
            game["pretos"]["score"] = score_opp
        updated += 1

    save_processed_games(games)
    return JSONResponse({"status": "ok", "updated": updated, "total": len(games)})
