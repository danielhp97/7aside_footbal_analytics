"""CLI entry point — `uv run football`"""

import typer
from pathlib import Path
from dotenv import load_dotenv
from football_analytics.reports import print_summary

load_dotenv()

app = typer.Typer(help="Football group game analytics")


@app.command()
def report(
    data_dir: Path = typer.Argument(Path("data/processed"), help="Directory with processed game JSON files"),
) -> None:
    """Print a summary leaderboard from processed game data."""
    # TODO: load Game objects from data_dir
    typer.echo(f"Loading games from {data_dir} … (not yet implemented)")


@app.command()
def import_garmin(
    export_file: Path = typer.Argument(..., help="Path to Garmin Connect export file"),
) -> None:
    """Import games from a Garmin Connect export."""
    from football_analytics.parsers import parse_garmin_export
    games = parse_garmin_export(export_file)
    typer.echo(f"Imported {len(games)} games.")


@app.command()
def import_messenger(
    export_file: Path = typer.Argument(..., help="Path to Facebook Messenger JSON export"),
) -> None:
    """Import team selections from a Messenger group chat export."""
    from football_analytics.parsers import parse_messenger_export
    selections = parse_messenger_export(export_file)
    typer.echo(f"Parsed {len(selections)} game team selections.")


@app.command()
def fetch_messenger(
    garmin_export: Path = typer.Argument(..., help="Garmin CSV export — used to determine the earliest game date"),
) -> None:
    """Fetch team selections from Messenger, scoped to games in the Garmin export.

    Requires MESSENGER_COOKIES_FILE and MESSENGER_GROUP_ID env vars.
    """
    from football_analytics.parsers import parse_garmin_export
    from football_analytics.messenger_client import fetch_team_selections

    games = parse_garmin_export(garmin_export)
    if not games:
        typer.echo("No games found in Garmin export.")
        raise typer.Exit(1)

    since = min(g.date for g in games)
    typer.echo(f"Fetching Messenger team selections from {since} ({len(games)} Garmin games)…")
    selections = fetch_team_selections(since)
    typer.echo(f"Fetched {len(selections)} team selections.")


def _padre_team(game: dict) -> str | None:
    """Return 'brancos' or 'pretos' depending on which side Padre/Padreco is on."""
    aliases = {"padre", "padreco"}
    for side in ("brancos", "pretos"):
        if any(p.lower() in aliases for p in game.get(side, {}).get("players", [])):
            return side
    return None


@app.command()
def fetch_scores(
    processed_dir: Path = typer.Argument(Path("data/processed"), help="Directory with processed game JSON files"),
) -> None:
    """Fetch scores from Garmin Connect and write them into processed/games.json.

    Requires GARMIN_EMAIL and GARMIN_PASSWORD env vars.
    Score assignment: 'My Team' score goes to whichever side Padre/Padreco is on.
    """
    import json
    from datetime import date as date_type
    from football_analytics.garmin_client import fetch_games

    games_file = processed_dir / "games.json"
    if not games_file.exists():
        typer.echo(f"No games.json found in {processed_dir}")
        raise typer.Exit(1)

    games: list[dict] = json.loads(games_file.read_text(encoding="utf-8"))
    if not games:
        typer.echo("No games to update.")
        raise typer.Exit(0)

    dates = [date_type.fromisoformat(g["date"]) for g in games]
    typer.echo(f"Fetching Garmin scores for {len(dates)} games ({min(dates)} → {max(dates)})…")

    garmin_games = fetch_games(min(dates), max(dates))
    score_by_date = {g.date: (g.team_a.score, g.team_b.score) for g in garmin_games}
    typer.echo(f"  Garmin returned {len(score_by_date)} scored activities.")

    from datetime import timedelta

    updated = 0
    for game in games:
        game_date = date_type.fromisoformat(game["date"])
        # Team selections are posted the day before or same day as the Garmin
        # activity, so try game_date then game_date+1 as a fallback.
        scores = score_by_date.get(game_date) or score_by_date.get(game_date + timedelta(days=1))
        if scores is None:
            continue
        score_my, score_opp = scores
        padre_side = _padre_team(game)
        if padre_side == "brancos":
            game["brancos"]["score"] = score_my
            game["pretos"]["score"] = score_opp
        elif padre_side == "pretos":
            game["pretos"]["score"] = score_my
            game["brancos"]["score"] = score_opp
        else:
            # Padre not found — store my-team score on brancos as best guess
            game["brancos"]["score"] = score_my
            game["pretos"]["score"] = score_opp
            typer.echo(f"  {game_date}: Padre not found, assigning scores to brancos/pretos as-is.")
        updated += 1

    games_file.write_text(json.dumps(games, indent=2, ensure_ascii=False), encoding="utf-8")
    typer.echo(f"Done — updated scores for {updated}/{len(games)} games.")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, help="Auto-reload on file changes"),
) -> None:
    """Start the web dashboard."""
    import uvicorn
    typer.echo(f"Starting dashboard at http://{host}:{port}")
    uvicorn.run("football_analytics.web:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
