"""Parse game data exported from Garmin Connect activities."""

from pathlib import Path
from football_analytics.models import Game


def parse_garmin_export(path: Path) -> list[Game]:
    """
    Load game records from a Garmin Connect export file.

    Garmin does not have a native team-sport format; the expected workflow is
    to manually export activity notes (CSV or JSON) that have been annotated
    with scores and team rosters.

    TODO: implement once the export format is confirmed.
    """
    raise NotImplementedError("Garmin parser not yet implemented")
