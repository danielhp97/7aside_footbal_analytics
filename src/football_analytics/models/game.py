from datetime import date
from pydantic import BaseModel

from .player import Player


class Team(BaseModel):
    name: str  # e.g. "Bibs" / "Skins" or "Team A" / "Team B"
    players: list[Player] = []
    score: int = 0


class Game(BaseModel):
    date: date
    location: str | None = None
    team_a: Team
    team_b: Team
    notes: str | None = None

    @property
    def winner(self) -> Team | None:
        if self.team_a.score > self.team_b.score:
            return self.team_a
        if self.team_b.score > self.team_a.score:
            return self.team_b
        return None  # draw

    @property
    def is_draw(self) -> bool:
        return self.team_a.score == self.team_b.score
