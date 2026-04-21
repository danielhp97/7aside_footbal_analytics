# Football Group Analytics

A personal analytics tool for tracking and analysing a weekly recreational 5-a-side / 6-a-side / 7-a-side football group. It ingests data from Facebook Messenger (team selections) and Garmin Connect (scores and activity metrics), then produces win/loss leaderboards, player statistics, and team composition analysis.

## Overview

- Games occur every **Monday at 20:00 PT**
- Team selections are posted in a **Facebook Messenger group chat**
- Scores and activity data are logged on **Garmin Connect**
- Teams are labelled as **brancos** and **pretos** 
- All processing is local — no external APIs required after initial exports

## Project Structure

```
footbal_analytics/
├── src/football_analytics/
│   ├── cli.py                  # Typer CLI entry point
│   ├── web.py                  # FastAPI web dashboard
│   ├── garmin_client.py        # Garmin Connect API client
│   ├── messenger_client.py     # Facebook Messenger async client
│   ├── names.py                # Name canonicalisation / alias resolution
│   ├── models/
│   │   ├── game.py             # Game, Team, Player Pydantic models
│   │   └── player.py
│   ├── parsers/
│   │   ├── garmin.py           # CSV parser for Garmin exports
│   │   └── messenger.py        # JSON parser + OCR for Messenger exports
│   ├── analysis/
│   │   ├── player_stats.py     # Per-player win/loss/draw rates
│   │   └── team_stats.py       # Team composition stats
│   ├── reports/
│   │   └── summary.py          # Terminal leaderboard via Rich
│   └── templates/
│       └── index.html          # Web dashboard template
├── scripts/
│   ├── process_games.py        # Build games.json from Messenger + manual overrides
│   ├── dump_messenger_messages.py
│   ├── list_messenger_groups.py
│   ├── build_static.py         # Pre-render static analysis
│   └── seed_example.py         # Generate test data
├── data/
│   ├── raw/                    # Original exports (git-ignored, never modified)
│   └── processed/
│       └── games.json          # Normalised game data
├── context/                    # Project documentation
│   ├── PROJECT.md
│   ├── AGENTS.md
│   ├── DATA_SOURCES.md
│   └── SCHEMA.md
├── pyproject.toml
└── .env                        # Credentials (not committed)
```

## Tech Stack

| Layer | Library |
|---|---|
| Language | Python 3.12+ |
| Package manager | `uv` |
| Data models | Pydantic v2, pandas |
| CLI | Typer |
| Web | FastAPI, Uvicorn, Jinja2 |
| Garmin integration | `garminconnect` |
| Messenger integration | `fbchat-muqit` |
| OCR | Pillow, pytesseract (Tesseract) |
| Terminal UI | Rich |
| Testing | pytest, pytest-cov |

## Installation

```bash
# Requires uv — https://docs.astral.sh/uv/
uv sync
```

Python 3.12 is pinned in `.python-version`; `uv` will install it automatically if missing.

## Configuration

Create a `.env` file in the project root:

```bash
# Garmin Connect
GARMIN_EMAIL=your-email@example.com
GARMIN_PASSWORD=your-password

# Facebook Messenger
MESSENGER_COOKIES_FILE=data/raw/cookies.json
MESSENGER_GROUP_ID=<your-group-thread-id>
```

`data/raw/` is git-ignored — place all raw exports (Garmin CSV, Messenger JSON) there.

## CLI Commands

All commands are run with `uv run football <command>`.

| Command | Description |
|---|---|
| `report [data_dir]` | Print player leaderboard from processed games |
| `import_garmin <file>` | Parse a Garmin CSV export |
| `import_messenger <file>` | Parse a Messenger JSON export |
| `fetch_messenger <file>` | Live-fetch teams from Messenger (requires cookies) |
| `fetch_scores [dir]` | Fetch scores from Garmin and update `games.json` |
| `serve` | Start the web dashboard at `http://127.0.0.1:8000` |

Options for `serve`:

```bash
uv run football serve --host 0.0.0.0 --port 5000
uv run football serve --reload   # dev mode
```

## Scripts

```bash
uv run python scripts/seed_example.py              # Generate example games
uv run python scripts/process_games.py             # Build games.json from Messenger dump
uv run python scripts/dump_messenger_messages.py   # Export Messenger history to JSON
uv run python scripts/list_messenger_groups.py     # List available Messenger groups
uv run python scripts/build_static.py              # Pre-render static analysis
```

## Web Dashboard

The dashboard (`web.py`) loads the Garmin CSV and `games.json`, merges them, and renders:

- **Player leaderboard** sorted by win rate (minimum 3 games)
- **Game history** with team lineups and scores
- **Activity metrics** — distance, heart rate, calories, steps

Start it with:

```bash
uv run football serve
# → http://127.0.0.1:8000
```

## Data Pipeline

```
Messenger JSON export ──► messenger parser ──► games.json ──┐
Garmin CSV export     ──► garmin parser    ──► games.json ──┼──► analysis ──► dashboard / report
Live Garmin API       ──► garmin client    ──► games.json ──┘
```

### Messenger parser

- Handles **text messages** matching patterns like `Brancos: Alice, Bob | Pretos: Dave, Eve`
- Handles **image messages** with OCR (Tesseract) for screenshot team lists — grayscale, 2× upscale, contrast boost, sharpen preprocessing
- Validates game dates against the valid selection window (Friday–Monday before 20:00 PT)

### Garmin parser

- Parses CSV exports for activities of type football/soccer
- Extracts scores from the notes field using regex: `3 - 2 | Team A: Alice, Bob | Team B: Dave, Eve`

### Name canonicalisation

`names.py` resolves player name variants and aliases (e.g. Padre / Padreco for the group organiser, Luis Zé variants, Ambrósio, Rémora). Players named "Amigo do…" are filtered out.

## Testing

```bash
uv run pytest           # run all tests
uv run pytest --cov     # with coverage report
```

## Data Schema

See [context/SCHEMA.md](context/SCHEMA.md) for the full `Game` / `Team` / `Player` model schema and the `games.json` format.
