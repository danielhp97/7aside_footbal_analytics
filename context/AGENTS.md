# Agent & Automation Context

This file explains how AI agents (e.g. Claude Code) should operate within this project.

## Project conventions

- **Language:** Python 3.12+, managed with `uv`.
- **Install deps:** `uv sync` — never `pip install`.
- **Run scripts:** `uv run python scripts/<file>.py` or `uv run football <command>`.
- **Tests:** `uv run pytest` (tests live in `tests/`).
- **No comments** explaining *what* the code does — only *why* where non-obvious.

## Folder responsibilities

| Folder | Purpose |
|--------|---------|
| `src/football_analytics/models/` | Pure domain objects (Pydantic). No I/O. |
| `src/football_analytics/parsers/` | One parser per data source. Returns domain models. |
| `src/football_analytics/analysis/` | Stateless computation over lists of `Game` objects. |
| `src/football_analytics/reports/` | Terminal output via Rich. No business logic. |
| `data/raw/` | Original exports — **never modified**. |
| `data/processed/` | Normalised JSON game files. |
| `scripts/` | One-off helper scripts and the seed example. |
| `context/` | Human + agent context docs (this folder). |

## Key TODOs for agents picking up this project

1. **Implement `parse_garmin_export`** in `parsers/garmin.py` — needs the actual Garmin export format.
2. **Implement `parse_messenger_export`** in `parsers/messenger.py` — needs a sample chat JSON export.
3. **Implement the `report` CLI command** in `cli.py` — load `Game` objects from `data/processed/` JSON files.
4. **Write tests** in `tests/` covering models, analysis, and parsers.
5. **Decide team identity** — by name string or by frozenset of player names? (see `analysis/team_stats.py` TODO).

## What agents should NOT do

- Do not modify files in `data/raw/`.
- Do not add optional parameters or abstractions that are not needed for a current task.
- Do not add error handling for internal code paths — only validate at system boundaries (file input, CLI args).
