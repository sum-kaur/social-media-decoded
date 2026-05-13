#!/usr/bin/env python3
"""Refresh analytics materialized views.
Usage: python scripts/refresh_views.py
Meant to be called from a cron job or after bulk ingestion.
"""
from __future__ import annotations

import asyncio

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    from db.connection import create_pool, close_pool
    from db.queries import refresh_analytics_views

    await create_pool()
    await refresh_analytics_views()
    await close_pool()
    print("Analytics materialized views refreshed.")


if __name__ == "__main__":
    asyncio.run(main())
