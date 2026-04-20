# Project Overview

## What this is

A personal analytics tool for a **weekly recreational football group**.

- Games are organised through a **Facebook Messenger group chat** — players confirm attendance and teams are picked there.
- Scores and activity data are logged on **Garmin Connect** by the user after each session.
- This project ingests both sources and produces **win/loss leaderboards** for teams and individual players.

## Goals

1. Track which players and team compositions win most often.
2. Surface trends over time (streaks, form, head-to-head records).
3. Keep everything local — no external APIs needed after the initial exports.

## Non-goals

- Real-time data ingestion (exports are manual for now).
- Public-facing web app (CLI + terminal reports are sufficient).

## Current status

Skeleton only. Parsers (`garmin.py`, `messenger.py`) are not yet implemented — they raise `NotImplementedError` until the export formats are confirmed.
