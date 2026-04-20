from pydantic import BaseModel


class Player(BaseModel):
    name: str
    # Messenger alias used to identify the player in chat logs
    alias: str | None = None

    games_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0

    @property
    def win_rate(self) -> float:
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played
