"""List Messenger group chats to find the football group's thread ID."""

import asyncio
from pathlib import Path

from fbchat_muqit import Client
from fbchat_muqit.models import ThreadFolder

COOKIES = Path("data/raw/cookies.json")


async def main() -> None:
    async with Client(cookies_file_path=str(COOKIES), disable_logs=True) as client:
        print(f"Logged in as: {client.name} ({client.uid})\n")

        threads = await client.fetch_thread_list(limit=20, thread_folder=ThreadFolder.INBOX)

        groups = [t for t in threads if str(t.thread_type).endswith("GROUP")]
        print(f"Found {len(groups)} group chats:\n")
        for t in groups:
            members = len(t.all_participants)
            print(f"  {t.name!r:40s}  id={t.thread_id}  members={members}")


asyncio.run(main())
