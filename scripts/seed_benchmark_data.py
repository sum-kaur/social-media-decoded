#!/usr/bin/env python3
"""Seed 50 synthetic signals across multiple brands for load testing and benchmarking.
Usage: python scripts/seed_benchmark_data.py [--count 50]
"""
from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

BRANDS = ["Nike", "Adidas", "Puma", "UnderArmour", "NewBalance"]
PLATFORMS = ["twitter", "instagram", "tiktok", "reddit"]
CATEGORIES = ["product_launch", "ugc", "sponsorship", "campaign", "collaboration"]
SENTIMENTS = ["positive", "negative", "neutral", "mixed"]

POSITIVE_TEMPLATES = [
    "Just got the new {brand} collection and I'm obsessed. The quality is insane! #sportswear",
    "{brand}'s latest drop is exactly what I needed for marathon training. 10/10.",
    "Shoutout to {brand} for their collab with {artist}. Absolutely fire.",
    "Can't believe {brand} just launched this for under $150. Game changer.",
    "My {brand} gear has held up after 6 months of daily use. Impressed.",
]
NEGATIVE_TEMPLATES = [
    "{brand} quality has dropped significantly in recent releases. Disappointing.",
    "Not happy with {brand}'s sizing consistency. Ordered my usual size and it didn't fit.",
    "{brand}'s customer service is a nightmare. Still waiting 3 weeks for a refund.",
    "The hype around {brand}'s new shoes is overblown. They're uncomfortable after 2 miles.",
    "Why is {brand} still using non-sustainable materials when competitors have moved on?",
]
NEUTRAL_TEMPLATES = [
    "{brand} announced their spring collection today. Expected to ship in March.",
    "Just saw {brand}'s new ad campaign. Interesting direction for the brand.",
    "Comparison: {brand} vs competitor — both have pros and cons depending on your use case.",
    "{brand} opened a new flagship store in NYC. Worth checking out if you're in the area.",
    "Spotted {brand}'s new ambassador on the campaign billboard. Bold choice.",
]


def _random_template(sentiment: str, brand: str) -> str:
    if sentiment == "positive":
        templates = POSITIVE_TEMPLATES
    elif sentiment == "negative":
        templates = NEGATIVE_TEMPLATES
    else:
        templates = NEUTRAL_TEMPLATES
    artist = random.choice(["Travis Scott", "Pharrell", "Beyoncé", "Bad Bunny"])
    return random.choice(templates).format(brand=brand, artist=artist)


def _random_created_at() -> datetime:
    days_ago = random.randint(0, 90)
    return datetime.now(tz=timezone.utc) - timedelta(days=days_ago, hours=random.randint(0, 23))


async def main(count: int) -> None:
    from db.connection import create_pool, close_pool
    from db.queries import insert_signal

    await create_pool()

    inserted = 0
    for _ in range(count):
        brand = random.choice(BRANDS)
        sentiment = random.choice(SENTIMENTS)
        engagements = int(random.lognormvariate(10, 2))  # log-normal: mostly small, few viral
        signal_strength = min(1.0, max(0.0, (engagements / 500_000) ** 0.4))

        await insert_signal(
            platform=random.choice(PLATFORMS),
            brand=brand,
            category=random.choice(CATEGORIES),
            post_text=_random_template(sentiment, brand),
            sentiment=sentiment,
            signal_strength=round(signal_strength, 4),
            engagements=engagements,
            source_url=None,
            author_handle=f"@user_{uuid.uuid4().hex[:6]}",
            language="en",
            is_verified_author=random.random() < 0.1,
            raw_metadata={"seed": True, "benchmark": True},
        )
        inserted += 1

    await close_pool()
    print(f"Seeded {inserted} benchmark signals across {len(BRANDS)} brands.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(main(args.count))
