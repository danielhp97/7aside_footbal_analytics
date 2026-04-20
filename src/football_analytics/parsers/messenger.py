"""Parse team selections from a Facebook Messenger group chat export."""

from pathlib import Path
from football_analytics.models import Team, Player


def parse_messenger_export(path: Path) -> list[Team]:
    """
    Extract team selections from a Messenger JSON export.

    Facebook lets you download your message history as JSON from
    Settings → Your Facebook Information → Download Your Information.

    TODO: implement pattern matching for team-picking messages once
    the chat export format is available.
    """
    raise NotImplementedError("Messenger parser not yet implemented")
