#!/usr/bin/env python3
"""
CLI script to trigger the pipeline directly without going through the API.
Usage: python scripts/run_pipeline.py --brand Nike --platform twitter
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def main(brand: str, platform: str, limit: int) -> None:
    # Import here so the script can be run standalone
    from db.connection import create_pool, close_pool
    from db import queries
    from pipeline.orchestrator import run_pipeline

    print(f"Connecting to database...")
    await create_pool()

    print(f"Fetching signals for brand={brand!r}...")
    raw_signals = await queries.get_signals_by_brand(brand, limit=limit)

    if not raw_signals:
        print(f"No signals found for brand={brand!r}. Run scripts/ingest_sample_data.py first.")
        await close_pool()
        return

    signal_ids = [str(s["id"]) for s in raw_signals]
    signals_dicts = []
    for s in raw_signals:
        d = dict(s)
        d["id"] = str(d["id"])
        if d.get("ingested_at"):
            d["ingested_at"] = d["ingested_at"].isoformat()
        signals_dicts.append(d)

    print(f"Running pipeline on {len(raw_signals)} signals...")
    final_state = await run_pipeline(
        brand=brand,
        platform=platform,
        signal_ids=signal_ids,
        raw_signals=signals_dicts,
    )

    print(f"\n=== Pipeline Complete ===")
    print(f"Run ID:    {final_state['run_id']}")
    print(f"Insight ID: {final_state.get('insight_id')}")
    print(f"Agents:    {', '.join(final_state.get('completed_agents', []))}")

    if final_state.get("recommended_actions"):
        print(f"\nTop Recommendations:")
        for i, action in enumerate(final_state["recommended_actions"][:3], 1):
            print(f"  {i}. [{action['priority'].upper()}] {action['action']}")

    if final_state.get("error"):
        print(f"\nError: {final_state['error']}")

    await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Social Media Decoded pipeline")
    parser.add_argument("--brand", default="Nike", help="Brand to analyse")
    parser.add_argument("--platform", default="twitter", help="Primary platform")
    parser.add_argument("--limit", type=int, default=10, help="Max signals to process")
    args = parser.parse_args()

    asyncio.run(main(args.brand, args.platform, args.limit))
