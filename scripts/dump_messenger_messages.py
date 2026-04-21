"""Dump raw Messenger messages to data/raw/messenger_messages.json.

Fetches only the 3-day pre-game window (Fri 00:00 → Mon 20:00 PT) for each
known game date from the Garmin export — one targeted batch per game week.
"""

import asyncio
import json
import os
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fbchat_muqit import Client
from fbchat_muqit.graphql import QueryRequest

load_dotenv()

_MESSAGES_DOC_ID = "3449967031715030"
_PT = timezone(timedelta(hours=-8))
_OUT = Path("data/raw/messenger_messages.json")


def _monday_window(game_date: date) -> tuple[int, int]:
    """Return (friday_midnight_ms, monday_20h_ms) in PT for a given game Monday."""
    monday_20h = datetime(game_date.year, game_date.month, game_date.day, 20, 0, 0, tzinfo=_PT)
    friday_midnight = monday_20h - timedelta(days=3)
    return int(friday_midnight.timestamp() * 1000), int(monday_20h.timestamp() * 1000)


_MAX_PAGES_PER_WINDOW = 20  # 1 000 messages max per game week — enough to find team picks


async def fetch_window(
    client: Client,
    thread_id: str,
    participants: dict[str, str],
    since_ms: int,
    before_ms: int,
    game_date: date,
) -> list[dict]:
    """Fetch messages in [since_ms, before_ms) for a single game window."""
    messages: list[dict] = []
    before: int = before_ms
    pages = 0

    while pages < _MAX_PAGES_PER_WINDOW:
        query = QueryRequest(
            doc_id=_MESSAGES_DOC_ID,
            query_params={
                "id": thread_id,
                "message_limit": 50,
                "load_messages": True,
                "load_read_receipts": False,
                "before": before,
            },
        )
        data = {
            "queries": client._graphql.queries_to_json(query),
            "batch_name": "MessengerGraphQLThreadFetcher",
        }
        result = await asyncio.wait_for(
            client._state._post(
                "https://www.facebook.com/api/graphqlbatch/", data=data, as_graphql=True
            ),
            timeout=30,
        )
        mt = result[0]["message_thread"]
        pages += 1

        if not participants:
            participants.update({
                e["node"]["messaging_actor"]["id"]: e["node"]["messaging_actor"].get("name", "")
                for e in mt["all_participants"]["edges"]
            })

        nodes: list[dict] = mt["messages"]["nodes"]
        if not nodes:
            break

        oldest_ts = int(nodes[-1]["timestamp_precise"])
        done = False
        for node in nodes:
            ts = int(node["timestamp_precise"])
            if ts < since_ms:
                done = True
                break
            if ts < before_ms:
                messages.append(node)

        if done or oldest_ts >= before:
            break
        before = oldest_ts - 1

    suffix = f" (page cap reached)" if pages == _MAX_PAGES_PER_WINDOW else ""
    print(f"  {game_date}: {len(messages)} messages in window{suffix}")
    return messages


async def dump(game_dates: list[date]) -> None:
    cookies_file = os.environ["MESSENGER_COOKIES_FILE"]
    thread_id = os.environ["MESSENGER_GROUP_ID"]

    # Merge into existing file if present
    existing: dict = {}
    if _OUT.exists():
        existing = json.loads(_OUT.read_text())

    all_messages: list[dict] = existing.get("messages", [])
    participants: dict[str, str] = existing.get("participants", {})
    seen_ids: set[str] = {m.get("message_id", "") for m in all_messages}

    async with Client(cookies_file_path=cookies_file, disable_logs=True) as client:
        for game_date in sorted(game_dates):
            since_ms, before_ms = _monday_window(game_date)
            window_msgs = await fetch_window(
                client, thread_id, participants, since_ms, before_ms, game_date
            )
            for msg in window_msgs:
                mid = msg.get("message_id", "")
                if mid not in seen_ids:
                    seen_ids.add(mid)
                    all_messages.append(msg)

    output = {"participants": participants, "messages": all_messages}
    _OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\nSaved {len(all_messages)} messages, {len(participants)} participants → {_OUT}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Accept explicit dates: python dump_messenger_messages.py 2026-01-12 2026-01-29 …
        game_dates = sorted(date.fromisoformat(a) for a in sys.argv[1:])
        print(f"Fetching {len(game_dates)} specified game window(s)…\n")
    else:
        from football_analytics.parsers import parse_garmin_export

        games = parse_garmin_export(Path("data/raw/football_activities_20_april.csv"))
        game_dates = sorted({g.date for g in games})
        print(f"Fetching game windows for {len(game_dates)} Mondays…\n")

    asyncio.run(dump(game_dates))
