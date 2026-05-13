#!/usr/bin/env python3
"""
Run the pipeline for all brands in the database concurrently.
Usage: python scripts/batch_run.py [--concurrency 3] [--platform twitter]
"""
from __future__ import annotations

import argparse
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def main(platform: str, concurrency: int) -> None:
    from db.connection import create_pool, close_pool
    from db.connection import acquire
    from pipeline.batch import BatchJob, run_batch

    print("Connecting to database...")
    await create_pool()

    # Discover all brands with signals
    async with acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT brand FROM signals ORDER BY brand")
    brands = [r["brand"] for r in rows]

    if not brands:
        print("No brands found. Run a seed script first.")
        await close_pool()
        return

    print(f"Found {len(brands)} brands: {', '.join(brands)}")
    jobs = [BatchJob(brand=b, platform=platform) for b in brands]

    results = await run_batch(jobs, concurrency=concurrency)

    print("\n=== Batch Results ===")
    for r in results:
        status = "✓" if r.success else "✗"
        agents = len(r.agents_completed)
        print(f"  {status} {r.brand:<20} agents={agents} insight={r.insight_id or 'none'}")
        if r.error:
            print(f"    └─ error: {r.error}")

    succeeded = sum(1 for r in results if r.success)
    print(f"\nDone: {succeeded}/{len(results)} succeeded.")
    await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", default="twitter")
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()
    asyncio.run(main(args.platform, args.concurrency))
