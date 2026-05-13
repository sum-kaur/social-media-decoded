#!/usr/bin/env python3
"""Poll the /health endpoint and print status.
Usage: python scripts/check_health.py [--url http://localhost:8000] [--interval 5]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime

import httpx


async def check_once(url: str) -> bool:
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{url}/health")
            data = resp.json()
            ts = datetime.now().strftime("%H:%M:%S")
            status = data.get("status", "unknown")
            db = data.get("db", False)
            icon = "" if status == "ok" else ""
            print(f"[{ts}] {icon}  status={status}  db={db}")
            return status == "ok"
        except Exception as exc:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}]   unreachable: {exc}")
            return False


async def main(url: str, interval: float | None) -> None:
    if interval is None:
        ok = await check_once(url)
        sys.exit(0 if ok else 1)

    print(f"Polling {url}/health every {interval}s — Ctrl+C to stop")
    while True:
        await check_once(url)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--interval", type=float, default=None,
                        help="Seconds between checks; omit for one-shot")
    args = parser.parse_args()
    asyncio.run(main(args.url, args.interval))
