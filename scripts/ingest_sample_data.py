#!/usr/bin/env python3
"""Load sample signals into Postgres for local development and evaluation."""
from __future__ import annotations

import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

SAMPLE_SIGNALS = [
    {
        "platform": "twitter",
        "brand": "Nike",
        "category": "sportswear",
        "post_text": "Just dropped the new Air Max 2025 and people are losing their minds 🔥 #Nike #AirMax",
        "campaign_type": "product_launch",
        "engagements": 45230,
        "signal_strength": 0.92,
    },
    {
        "platform": "instagram",
        "brand": "Nike",
        "category": "sportswear",
        "post_text": "Athletes worldwide choosing Nike for their marathon training. Real performance, real results.",
        "campaign_type": "brand_awareness",
        "engagements": 128400,
        "signal_strength": 0.85,
    },
    {
        "platform": "tiktok",
        "brand": "Nike",
        "category": "sportswear",
        "post_text": "POV: you wore Nikes to the gym and now everyone wants to know your routine 😂 #NikeWorkout",
        "campaign_type": "ugc",
        "engagements": 892000,
        "signal_strength": 0.97,
    },
    {
        "platform": "twitter",
        "brand": "Nike",
        "category": "sportswear",
        "post_text": "Nike's latest sustainability report is actually disappointing. They promised 50% recycled materials by 2025.",
        "campaign_type": "organic",
        "engagements": 3400,
        "signal_strength": 0.45,
    },
    {
        "platform": "instagram",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "Impossible is Nothing. Our new Ultraboost campaign just broke records on social.",
        "campaign_type": "product_launch",
        "engagements": 98200,
        "signal_strength": 0.88,
    },
    {
        "platform": "twitter",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "The Adidas x Balenciaga collab is either a masterpiece or a disaster, no in between.",
        "campaign_type": "collaboration",
        "engagements": 67100,
        "signal_strength": 0.79,
    },
    {
        "platform": "tiktok",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "Rating every Adidas silhouette from 2024 — some of these are SLEPT ON 👟",
        "campaign_type": "ugc",
        "engagements": 1240000,
        "signal_strength": 0.95,
    },
    {
        "platform": "reddit",
        "brand": "Adidas",
        "category": "sportswear",
        "post_text": "Adidas quality has gone downhill. My Ultraboosts lasted 3 months before the sole separated.",
        "campaign_type": "organic",
        "engagements": 2800,
        "signal_strength": 0.38,
    },
    {
        "platform": "twitter",
        "brand": "Nike",
        "category": "sportswear",
        "post_text": "Nike's Colin Kaepernick ad still holds up. That campaign changed how we think about brand values.",
        "campaign_type": "brand_values",
        "engagements": 18900,
        "signal_strength": 0.72,
    },
    {
        "platform": "instagram",
        "brand": "Nike",
        "category": "sportswear",
        "post_text": "Women's World Cup partnership with Nike is generating 3x normal engagement. @Nike killing it.",
        "campaign_type": "sponsorship",
        "engagements": 234000,
        "signal_strength": 0.94,
    },
]


async def main() -> None:
    dsn = os.environ["DATABASE_URL"]
    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=3)

    inserted = 0
    async with pool.acquire() as conn:
        for signal in SAMPLE_SIGNALS:
            row = await conn.fetchrow(
                """
                INSERT INTO signals (platform, brand, category, post_text, campaign_type, engagements, signal_strength)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                signal["platform"],
                signal["brand"],
                signal["category"],
                signal["post_text"],
                signal["campaign_type"],
                signal["engagements"],
                signal["signal_strength"],
            )
            print(f"  Inserted {signal['brand']} / {signal['platform']}: {row['id']}")
            inserted += 1

    await pool.close()
    print(f"\nDone. Inserted {inserted} sample signals.")


if __name__ == "__main__":
    asyncio.run(main())
