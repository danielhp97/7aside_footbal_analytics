"""Aggregate win/draw/loss statistics per team composition."""

from collections import defaultdict
from football_analytics.models import Game


class TeamStats:
    def __init__(self, games: list[Game]) -> None:
        self.games = games

    def leaderboard(self) -> list[dict]:
        """Return teams sorted by win rate (most stable composition first)."""
        # TODO: decide whether a "team" is identified by name or by player set
        stats: dict[str, dict] = defaultdict(lambda: {"wins": 0, "draws": 0, "losses": 0, "played": 0})

        for game in self.games:
            for team, opponent in [(game.team_a, game.team_b), (game.team_b, game.team_a)]:
                key = team.name
                stats[key]["played"] += 1
                if game.is_draw:
                    stats[key]["draws"] += 1
                elif game.winner and game.winner.name == team.name:
                    stats[key]["wins"] += 1
                else:
                    stats[key]["losses"] += 1

        rows = [{"team": k, **v, "win_rate": v["wins"] / v["played"]} for k, v in stats.items()]
        return sorted(rows, key=lambda r: r["win_rate"], reverse=True)
