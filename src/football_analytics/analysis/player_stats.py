"""Aggregate win/draw/loss statistics per individual player."""

from collections import defaultdict
from football_analytics.models import Game


class PlayerStats:
    def __init__(self, games: list[Game]) -> None:
        self.games = games

    def leaderboard(self) -> list[dict]:
        """Return players sorted by win rate."""
        stats: dict[str, dict] = defaultdict(lambda: {"wins": 0, "draws": 0, "losses": 0, "played": 0})

        for game in self.games:
            for team, is_winner in [
                (game.team_a, game.winner == game.team_a),
                (game.team_b, game.winner == game.team_b),
            ]:
                for player in team.players:
                    key = player.name
                    stats[key]["played"] += 1
                    if game.is_draw:
                        stats[key]["draws"] += 1
                    elif is_winner:
                        stats[key]["wins"] += 1
                    else:
                        stats[key]["losses"] += 1

        rows = [{"player": k, **v, "win_rate": v["wins"] / v["played"]} for k, v in stats.items()]
        return sorted(rows, key=lambda r: r["win_rate"], reverse=True)
