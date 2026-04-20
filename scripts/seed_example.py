"""Seed a couple of example Game objects so you can test reports immediately."""

from datetime import date
from football_analytics.models import Game, Team, Player
from football_analytics.reports import print_summary

players_a = [Player(name="Alice"), Player(name="Bob"), Player(name="Carlos")]
players_b = [Player(name="David"), Player(name="Eve"), Player(name="Frank")]

games = [
    Game(
        date=date(2025, 1, 10),
        team_a=Team(name="Bibs", players=players_a, score=3),
        team_b=Team(name="Skins", players=players_b, score=2),
    ),
    Game(
        date=date(2025, 1, 17),
        team_a=Team(name="Bibs", players=players_a, score=1),
        team_b=Team(name="Skins", players=players_b, score=1),
    ),
    Game(
        date=date(2025, 1, 24),
        team_a=Team(name="Bibs", players=players_a, score=0),
        team_b=Team(name="Skins", players=players_b, score=2),
    ),
]

print_summary(games)
