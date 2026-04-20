"""CLI entry point — `uv run football`"""

import typer
from pathlib import Path
from football_analytics.reports import print_summary

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
    teams = parse_messenger_export(export_file)
    typer.echo(f"Parsed {len(teams)} team selections.")


if __name__ == "__main__":
    app()
