"""Rich terminal reports."""

from rich.console import Console
from rich.table import Table
from football_analytics.analysis import TeamStats, PlayerStats
from football_analytics.models import Game

console = Console()


def print_summary(games: list[Game]) -> None:
    _print_player_leaderboard(games)
    _print_team_leaderboard(games)


def _print_player_leaderboard(games: list[Game]) -> None:
    rows = PlayerStats(games).leaderboard()
    table = Table(title="Player Leaderboard", show_lines=True)
    table.add_column("Player")
    table.add_column("Played", justify="right")
    table.add_column("W", justify="right", style="green")
    table.add_column("D", justify="right", style="yellow")
    table.add_column("L", justify="right", style="red")
    table.add_column("Win %", justify="right")

    for r in rows:
        table.add_row(r["player"], str(r["played"]), str(r["wins"]), str(r["draws"]), str(r["losses"]), f"{r['win_rate']:.0%}")

    console.print(table)


def _print_team_leaderboard(games: list[Game]) -> None:
    rows = TeamStats(games).leaderboard()
    table = Table(title="Team Leaderboard", show_lines=True)
    table.add_column("Team")
    table.add_column("Played", justify="right")
    table.add_column("W", justify="right", style="green")
    table.add_column("D", justify="right", style="yellow")
    table.add_column("L", justify="right", style="red")
    table.add_column("Win %", justify="right")

    for r in rows:
        table.add_row(r["team"], str(r["played"]), str(r["wins"]), str(r["draws"]), str(r["losses"]), f"{r['win_rate']:.0%}")

    console.print(table)
