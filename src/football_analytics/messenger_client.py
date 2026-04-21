"""Fetch team selections live from a Facebook Messenger group chat."""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timezone
from typing import Any

from fbchat_muqit import Client
from fbchat_muqit.graphql import QueryRequest

from football_analytics.parsers.messenger import TeamSelection, _parse_message_dicts

_PAGE_SIZE = 50
# doc_id that returns messages.nodes (the fetch_thread_info one with load_messages=True)
_MESSAGES_DOC_ID = "3449967031715030"


def _date_to_ms(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def _image_uri(blob: dict[str, Any]) -> str | None:
    """Extract the best available image URL from a blob attachment node."""
    for field in ("large_preview", "preview", "thumbnail"):
        img = blob.get(field)
        if isinstance(img, dict):
            uri = img.get("uri")
            if uri:
                return str(uri)
    return None


async def _fetch(since: date) -> list[TeamSelection]:
    cookies_file = os.environ["MESSENGER_COOKIES_FILE"]
    thread_id = os.environ["MESSENGER_GROUP_ID"]
    since_ms = _date_to_ms(since)

    async with Client(cookies_file_path=cookies_file, disable_logs=True) as client:
        # Build participant id→name map from the first page (includes all_participants)
        participants: dict[str, str] = {}
        raw: list[dict[str, Any]] = []
        before: int | None = None
        first_page = True

        while True:
            query = QueryRequest(
                doc_id=_MESSAGES_DOC_ID,
                query_params={
                    "id": thread_id,
                    "message_limit": _PAGE_SIZE,
                    "load_messages": True,
                    "load_read_receipts": False,
                    "before": before,
                },
            )
            data = {
                "queries": client._graphql.queries_to_json(query),
                "batch_name": "MessengerGraphQLThreadFetcher",
            }
            result = await client._state._post(
                "https://www.facebook.com/api/graphqlbatch/", data=data, as_graphql=True
            )
            mt: dict[str, Any] = result[0]["message_thread"]

            if first_page:
                participants = {
                    e["node"]["messaging_actor"]["id"]: e["node"]["messaging_actor"].get("name", "")
                    for e in mt["all_participants"]["edges"]
                }
                first_page = False

            nodes: list[dict[str, Any]] = mt["messages"]["nodes"]
            if not nodes:
                break

            done = False
            for node in nodes:
                ts_ms = int(node["timestamp_precise"])
                if ts_ms < since_ms:
                    done = True
                    break

                sender_name = participants.get(node["message_sender"]["id"], "")
                text: str = (node.get("message") or {}).get("text") or ""
                blobs: list[dict[str, Any]] = node.get("blob_attachments") or []

                entry: dict[str, Any] = {
                    "type": "Generic",
                    "timestamp_ms": ts_ms,
                    "sender_name": sender_name,
                }
                if text:
                    entry["content"] = text
                if blobs:
                    uri = _image_uri(blobs[0])
                    if uri:
                        entry["photos"] = [{"uri": uri}]

                raw.append(entry)

            if done:
                break

            before = int(nodes[-1]["timestamp_precise"]) - 1

    return _parse_message_dicts(raw)


def fetch_team_selections(since: date) -> list[TeamSelection]:
    """Return team selections from the Messenger group chat since the given date.

    Requires env vars:
      MESSENGER_COOKIES_FILE  path to the Facebook session cookies JSON
      MESSENGER_GROUP_ID      Messenger thread ID of the football group chat
    """
    return asyncio.run(_fetch(since))
