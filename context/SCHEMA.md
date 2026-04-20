# Data Schema

All domain objects are Pydantic v2 models located in `src/football_analytics/models/`.

## Player

```python
Player(
    name: str,           # canonical display name
    alias: str | None,   # Messenger display name if different
    games_played: int,
    wins: int,
    draws: int,
    losses: int,
)
```

Computed: `win_rate = wins / games_played`

---

## Team

```python
Team(
    name: str,           # "Bibs" / "Skins" / "Team A" etc.
    players: list[Player],
    score: int,          # goals scored in a specific Game
)
```

---

## Game

```python
Game(
    date: date,
    location: str | None,
    team_a: Team,
    team_b: Team,
    notes: str | None,   # raw Garmin activity note
)
```

Computed:
- `winner → Team | None` (None = draw)
- `is_draw → bool`

---

## Processed data storage

Processed games are saved as **JSON files** in `data/processed/`, one file per game session, named `YYYY-MM-DD.json`. The JSON shape mirrors the `Game` model (Pydantic `.model_dump()`).
