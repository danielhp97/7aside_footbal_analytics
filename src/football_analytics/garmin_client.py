"""Fetch football activities and scores from Garmin Connect."""

from __future__ import annotations

import os
from datetime import date, datetime

from garminconnect import Garmin

from football_analytics.models import Game, Team

_CONNECTIQ_APP_ID = "1d68ae88-0874-4f7b-80e3-b1ee87dc571e"
# Developer field numbers within the Soccer/Football Connect IQ data
_FIELD_SCORE_MY_TEAM = 0
_FIELD_SCORE_OPPONENT = 1


def _client() -> Garmin:
    email = os.environ["GARMIN_EMAIL"]
    password = os.environ["GARMIN_PASSWORD"]
    c = Garmin(email, password)
    c.login()
    return c


def _extract_scores(details: dict) -> tuple[int, int]:
    iq = {
        m["developerFieldNumber"]: m["value"]
        for m in details.get("connectIQMeasurements", [])
        if m.get("appID") == _CONNECTIQ_APP_ID
    }
    try:
        score_a = int(float(iq[_FIELD_SCORE_MY_TEAM]))
        score_b = int(float(iq[_FIELD_SCORE_OPPONENT]))
    except (KeyError, ValueError):
        score_a, score_b = 0, 0
    return score_a, score_b


def fetch_games(start: date, end: date) -> list[Game]:
    """Return Game objects for all football activities between start and end."""
    client = _client()

    activities = client.get_activities_by_date(
        start.isoformat(), end.isoformat()
    )
    football = [
        a for a in activities
        if "soccer" in a.get("activityType", {}).get("typeKey", "").lower()
    ]

    games: list[Game] = []
    for activity in football:
        details = client.get_activity(activity["activityId"])
        score_a, score_b = _extract_scores(details)

        activity_date = datetime.fromisoformat(activity["startTimeLocal"]).date()

        games.append(Game(
            date=activity_date,
            location=activity.get("locationName"),
            team_a=Team(name="My Team", score=score_a),
            team_b=Team(name="Opponent", score=score_b),
        ))

    return games
