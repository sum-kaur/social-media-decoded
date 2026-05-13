#!/usr/bin/env python3
"""Seed additional Adidas signals with richer metadata for evaluation and demos."""
from __future__ import annotations

import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

ADIDAS_SIGNALS = [
    {
        "platform": "twitter",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "Just ran my first marathon in @adidas Adizero Pro 4. Sub-3 hours. These shoes are engineering art.",
        "campaign_type": "ugc",
        "engagements": 22400,
        "signal_strength": 0.78,
        "author_handle": "@marathoner_mel",
        "language": "en",
    },
    {
        "platform": "instagram",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "The new Adidas Originals drop is selling out worldwide. Stan Smith never dies. 🌿",
        "campaign_type": "product_launch",
        "engagements": 187000,
        "signal_strength": 0.91,
        "author_handle": "@sneakerheadofficial",
        "language": "en",
    },
    {
        "platform": "tiktok",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "My honest review of the Adidas x Gucci collab — worth the hype or massive L? #Adidas #Fashion",
        "campaign_type": "collaboration",
        "engagements": 3400000,
        "signal_strength": 0.99,
        "author_handle": "@stylereviewer",
        "language": "en",
    },
    {
        "platform": "reddit",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "Adidas brought back the Forum Low and honestly it might be the best retro reissue of 2025.",
        "campaign_type": "organic",
        "engagements": 5600,
        "signal_strength": 0.62,
        "language": "en",
    },
    {
        "platform": "twitter",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "Adidas sustainability efforts are real — 60% recycled content in their latest line. Respect.",
        "campaign_type": "brand_awareness",
        "engagements": 9800,
        "signal_strength": 0.70,
        "language": "en",
    },
]


async def main() -> None:
    pool = await asyncpg.create_pool(dsn=os.environ["DATABASE_URL"], min_size=1, max_size=3)
    inserted = 0
    async with pool.acquire() as conn:
        for s in ADIDAS_SIGNALS:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO signals
                        (platform, brand, category, post_text, campaign_type, engagements,
                         signal_strength, author_handle, language)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                    RETURNING id
                    """,
                    s["platform"], s["brand"], s["category"], s["post_text"],
                    s["campaign_type"], s["engagements"], s["signal_strength"],
                    s.get("author_handle"), s.get("language", "en"),
                )
                print(f"  Inserted {s['brand']} / {s['platform']}: {row['id']}")
                inserted += 1
            except Exception as e:
                print(f"  Skipped (likely duplicate): {e}")
    await pool.close()
    print(f"\nDone. Inserted {inserted} Adidas signals.")


if __name__ == "__main__":
    asyncio.run(main())
