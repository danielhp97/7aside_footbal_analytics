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

## Game domain rules

- Games are played every **Monday at 20h PT**.
- Teams are decided any time from **3 days before up to kick-off**; multiple drafts are posted — only the **last valid team message before 20h Monday** counts.
- Teams are always **brancos** (first list) and **pretos** (second list). Labels may be absent — position determines the assignment.
- Team selections arrive as either:
  - A **text message** with two ordered player lists.
  - An **image** (simple screenshot) — use OCR (pytesseract) to extract text, then parse as above.
- **Game type** (5-a-side, 6-a-side, 7-a-side) is auto-detected from player count per team.
- The user's alias in the chat is **"Padre" / "Padreco"** (and close variants) — used to identify `my_team`.
- Teams may **not be detected** for a given week (no message found, OCR failure, etc.) — raise a descriptive issue/warning and continue. Manual game entry will be supported in future.
- Chat source: **Facebook Messenger JSON export**.

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
