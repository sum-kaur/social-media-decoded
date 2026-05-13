#!/usr/bin/env python3
"""Export insights to JSON for offline analysis or sharing.
Usage: python scripts/export_insights.py [--brand Nike] [--output insights.json]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def main(brand: str | None, output: str) -> None:
    from db.connection import create_pool, close_pool
    from db.queries import get_insights

    await create_pool()
    insights = await get_insights(brand=brand, limit=100)
    await close_pool()

    # Strip large pipeline_trace for cleaner exports
    export_data = []
    for ins in insights:
        row = dict(ins)
        row["id"] = str(row["id"])
        if row.get("signal_ids"):
            row["signal_ids"] = [str(s) for s in row["signal_ids"]]
        row.pop("pipeline_trace", None)  # omit verbose trace from export
        export_data.append(row)

    out_path = Path(output)
    with open(out_path, "w") as f:
        json.dump(export_data, f, indent=2, default=_json_default)

    print(f"Exported {len(export_data)} insights to {out_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", default=None)
    parser.add_argument("--output", default="insights_export.json")
    args = parser.parse_args()
    asyncio.run(main(args.brand, args.output))
