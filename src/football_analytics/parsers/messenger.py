"""Parse team selections from a Facebook Messenger group chat export."""

import json
import re
import warnings
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any, TypedDict, cast

from football_analytics.models import Team, Player
from football_analytics.names import canonical, is_garbage

_PT = timezone(timedelta(hours=-8))
_MONDAY = 0

# Inline format: "Brancos: Alice, Bob" or "Brancos: Alice Bob"
_BRANCOS_INLINE_RE = re.compile(
    r"^(?:brancos?|whites?|bibs?|team\s*a)\s*[:\-]\s*(.+)", re.IGNORECASE
)
_PRETOS_INLINE_RE = re.compile(
    r"^(?:pretos?|vermelhos?|blacks?|reds?|skins?|team\s*b)\s*[:\-]\s*(.+)", re.IGNORECASE
)

# Block format: team name as standalone header line
_TEAM_LABEL_RE = re.compile(
    r"^(?:brancos?|pretos?|vermelhos?|whites?|blacks?|reds?|bibs?|skins?|team\s*[ab])\b",
    re.IGNORECASE
)

# Numbered player entry: "1 Chupa", "2. Alice", "3) Bob", "2 Amigo do Salto" (after pipe cleanup)
_NUMBERED_PLAYER_RE = re.compile(r"^\d+[\.\)\s]\s*(.+)")


class TeamSelection(TypedDict):
    game_date: date
    brancos: Team
    pretos: Team


def _make_player(name: str) -> Player | None:
    c = canonical(name)
    return None if not c or is_garbage(c) else Player(name=c)


def _parse_players(raw: str) -> list[Player]:
    if "," in raw:
        return [p for n in raw.split(",") if n.strip() and (p := _make_player(n.strip()))]
    return [p for n in raw.split() if n.strip() and (p := _make_player(n.strip()))]


def _normalize_team_name(raw: str) -> str:
    """Lowercase and strip count suffixes like '(7)'."""
    return re.sub(r"\s*\(\d+\)\s*$", "", raw).strip().lower()


def _clean_ocr_text(text: str) -> str:
    """Remove pipe artifacts from table-border OCR noise and normalize whitespace."""
    lines = []
    for line in text.splitlines():
        line = line.replace("|", " ")
        line = " ".join(line.split())
        lines.append(line)
    return "\n".join(lines)


def _extract_teams(content: str) -> tuple[Team, Team] | None:
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    # Strategy 1 — inline "Label: player1, player2"
    brancos_players: list[Player] | None = None
    pretos_players: list[Player] | None = None
    for line in lines:
        if m := _BRANCOS_INLINE_RE.match(line):
            brancos_players = _parse_players(m.group(1))
        elif m := _PRETOS_INLINE_RE.match(line):
            pretos_players = _parse_players(m.group(1))
    if brancos_players is not None and pretos_players is not None:
        return (
            Team(name="brancos", players=brancos_players),
            Team(name="pretos", players=pretos_players),
        )

    # Strategy 2 — block format: team label followed by player name lines.
    # Lines appearing before the first recognized label are treated as the first
    # team (brancos) — this handles OCR images where the header is not recognized.
    teams: list[tuple[str, list[Player]]] = []
    pre_label_players: list[Player] = []
    current_label: str | None = None
    current_players: list[Player] = []

    for line in lines:
        if _TEAM_LABEL_RE.match(line):
            if current_label is not None and current_players:
                teams.append((current_label, current_players))
            elif current_label is None and len(pre_label_players) >= 2:
                teams.append(("brancos", pre_label_players))
            current_label = _normalize_team_name(line)
            current_players = []
        elif current_label is not None:
            player_name = (
                m.group(1).strip()
                if (m := _NUMBERED_PLAYER_RE.match(line))
                else line
            )
            if player_name and (p := _make_player(player_name)):
                current_players.append(p)
        else:
            # Before any label — accumulate as potential first team
            player_name = (
                m.group(1).strip()
                if (m := _NUMBERED_PLAYER_RE.match(line))
                else line
            )
            if player_name and len(player_name) > 1 and (p := _make_player(player_name)):
                pre_label_players.append(p)

    if current_label is not None and current_players:
        teams.append((current_label, current_players))

    if len(teams) >= 2:
        return (
            Team(name=teams[0][0], players=teams[0][1]),
            Team(name=teams[1][0], players=teams[1][1]),
        )

    return None


def _ocr_image(uri: str) -> str | None:
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter

        if uri.startswith(("http://", "https://")):
            from io import BytesIO
            from urllib.request import Request, urlopen

            req = Request(uri, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=15) as resp:  # noqa: S310
                img = Image.open(BytesIO(resp.read()))
        else:
            img = Image.open(uri)

        # Preprocess: grayscale → 2× upscale → contrast boost → sharpen
        img = img.convert("L")
        w, h = img.size
        img = img.resize((w * 2, h * 2), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)

        # psm 4 (single column) picks up multi-column list layouts better than psm 6;
        # fall back to psm 6 only when psm 4 yields less text.
        raw4: str = cast(str, pytesseract.image_to_string(img, config="--psm 4"))  # type: ignore[no-untyped-call]
        raw6: str = cast(str, pytesseract.image_to_string(img, config="--psm 6"))  # type: ignore[no-untyped-call]
        raw: str = raw4 if len(raw4) >= len(raw6) else raw6
        return _clean_ocr_text(raw)
    except Exception as exc:
        warnings.warn(f"OCR error: {exc}", stacklevel=4)
        return None


def _game_monday(ts_ms: int) -> date | None:
    """Return the game Monday this message applies to, or None if outside the valid window.

    Valid window: Friday through Monday before 20:00 PT (3 days pre-kickoff).
    Tue/Wed/Thu messages are too early and are ignored.
    """
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=_PT)
    weekday = dt.weekday()  # Mon=0 … Sun=6

    if weekday == _MONDAY:
        return dt.date() if dt.hour < 20 else None
    if weekday in (4, 5, 6):  # Fri, Sat, Sun
        return dt.date() + timedelta(days=(7 - weekday) % 7)
    return None


def _parse_message_dicts(messages: list[dict[str, Any]]) -> list[TeamSelection]:
    # Per Monday: all image URIs (chronological) and latest text content
    by_monday: dict[date, dict[str, Any]] = {}

    for msg in messages:
        if msg.get("type") != "Generic":
            continue

        ts_ms: int = msg.get("timestamp_ms", 0)
        monday = _game_monday(ts_ms)
        if monday is None:
            continue

        entry = by_monday.setdefault(monday, {"images": [], "text": None})
        photos: list[dict[str, Any]] = msg.get("photos") or []
        content: str = msg.get("content") or ""

        if photos:
            uri = photos[0].get("uri", "")
            if uri:
                entry["images"].append((ts_ms, uri))
        elif content:
            if entry["text"] is None or ts_ms > entry["text"][0]:
                entry["text"] = (ts_ms, content)

    selections: list[TeamSelection] = []

    for monday, entry in sorted(by_monday.items()):
        teams: tuple[Team, Team] | None = None

        images: list[tuple[int, str]] = sorted(entry["images"])  # chronological
        if images:
            # Try each image individually, then all combined (handles split brancos/pretos)
            ocr_texts = [_ocr_image(uri) for _, uri in images]
            candidates = [t for t in ocr_texts if t]
            if len(candidates) > 1:
                candidates.append("\n".join(candidates))
            for text in candidates:
                teams = _extract_teams(text)
                if teams:
                    break

        if teams is None:
            if not entry["text"]:
                warnings.warn(f"{monday}: no team selection found.", stacklevel=2)
                continue
            if not images:
                warnings.warn(f"{monday}: no image found; using text message.", stacklevel=2)
            teams = _extract_teams(entry["text"][1])

        if teams is None:
            warnings.warn(f"{monday}: could not parse teams.", stacklevel=2)
            continue

        brancos, pretos = teams
        if len(brancos.players) != len(pretos.players):
            warnings.warn(
                f"{monday}: uneven teams — brancos {len(brancos.players)} vs pretos {len(pretos.players)}.",
                stacklevel=2,
            )
        selections.append(TeamSelection(game_date=monday, brancos=brancos, pretos=pretos))

    return selections


def parse_messenger_export(path: Path) -> list[TeamSelection]:
    """
    Extract team selections from a Messenger JSON export.

    Facebook lets you download your message history as JSON from
    Settings → Your Facebook Information → Download Your Information.
    Select Messages, format = JSON.

    For each Monday game, an image message takes priority; the last valid
    text message is used as fallback (with a warning).
    """
    data = json.loads(path.read_bytes().decode("utf-8", errors="replace"))
    messages: list[dict[str, Any]] = data.get("messages", [])

    # Resolve relative photo URIs to absolute paths alongside the export file
    base_dir = path.parent
    for msg in messages:
        for photo in (msg.get("photos") or []):
            photo_dict = cast(dict[str, Any], photo)
            uri: str = str(photo_dict.get("uri") or "")
            if uri and not uri.startswith(("http://", "https://")):
                photo_dict["uri"] = str(base_dir / uri)

    return _parse_message_dicts(messages)
