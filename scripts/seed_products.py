"""Seed the database with sample luxury candle products.

Usage:
    python scripts/seed_products.py

Idempotent — safe to run multiple times (uses upsert semantics).
"""

import sys
from pathlib import Path

# Add project root to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.database import init_db
from app.services import product_service

SEED_PRODUCTS = [
    {
        "id": "lavender-dream-300ml",
        "name": "Lavender Dream",
        "description": "Hand-poured soy candle with French lavender essential oil. "
        "A calming scent that fills your space with the essence of Provence.",
        "materials": "Soy wax, French lavender essential oil, cotton wick",
        "days_to_craft": 3,
        "price_cents": 3200,
        "category": "luxury-jar",
        "stock": 24,
        "is_active": True,
        "is_featured": True,
    },
    {
        "id": "midnight-amber-300ml",
        "name": "Midnight Amber",
        "description": "Warm amber and sandalwood in a hand-glazed black ceramic vessel. "
        "Perfect for evening relaxation.",
        "materials": "Coconut wax, amber resin, sandalwood oil, ceramic vessel",
        "days_to_craft": 5,
        "price_cents": 4500,
        "category": "luxury-jar",
        "stock": 12,
        "is_active": True,
        "is_featured": True,
    },
    {
        "id": "vanilla-creme-brulee-200ml",
        "name": "Vanilla Crème Brûlée",
        "description": "Rich vanilla custard with a caramelized sugar top note. "
        "A gourmand delight inspired by Parisian patisseries.",
        "materials": "Soy wax, vanilla absolute, caramel fragrance oil",
        "days_to_craft": 2,
        "price_cents": 2800,
        "category": "dessert",
        "stock": 36,
        "is_active": True,
        "is_featured": False,
    },
    {
        "id": "salted-caramel-macaron-200ml",
        "name": "Salted Caramel Macaron",
        "description": "Buttery caramel with a delicate sea salt finish. "
        "Evokes the warmth of a French boulangerie.",
        "materials": "Soy wax, caramel fragrance, sea salt accord",
        "days_to_craft": 2,
        "price_cents": 2800,
        "category": "dessert",
        "stock": 28,
        "is_active": True,
        "is_featured": False,
    },
    {
        "id": "rose-garden-250ml",
        "name": "Rose Garden",
        "description": "Bulgarian rose and peony with a green stem accord. "
        "Like walking through a blooming garden at dawn.",
        "materials": "Coconut-soy blend, Bulgarian rose oil, peony extract",
        "days_to_craft": 4,
        "price_cents": 3800,
        "category": "luxury-jar",
        "stock": 18,
        "is_active": True,
        "is_featured": True,
    },
    {
        "id": "winter-spice-trio",
        "name": "Winter Spice Trio",
        "description": "Gift set of three votives: cinnamon bark, mulled wine, "
        "and gingerbread. Perfect for the holiday season.",
        "materials": "Soy wax, cinnamon bark oil, mulled wine fragrance, gingerbread accord",
        "days_to_craft": 4,
        "price_cents": 5200,
        "category": "gift-set",
        "stock": 15,
        "is_active": True,
        "is_featured": False,
    },
    {
        "id": "spring-blossom-duo",
        "name": "Spring Blossom Duo",
        "description": "Gift set of two candles: cherry blossom and jasmine. "
        "Celebrate the arrival of spring.",
        "materials": "Soy wax, cherry blossom fragrance, jasmine absolute",
        "days_to_craft": 3,
        "price_cents": 4200,
        "category": "gift-set",
        "stock": 20,
        "is_active": True,
        "is_featured": False,
    },
    {
        "id": "pumpkin-chai-latte-200ml",
        "name": "Pumpkin Chai Latte",
        "description": "Warm pumpkin spice with chai tea undertones. "
        "A cozy autumn ritual in candle form.",
        "materials": "Soy wax, pumpkin spice blend, chai tea extract",
        "days_to_craft": 2,
        "price_cents": 2600,
        "category": "seasonal",
        "stock": 40,
        "is_active": True,
        "is_featured": False,
    },
    {
        "id": "summer-citrus-burst-300ml",
        "name": "Summer Citrus Burst",
        "description": "Bright bergamot, lemon zest, and pink grapefruit. "
        "A refreshing burst of Mediterranean sunshine.",
        "materials": "Coconut wax, bergamot oil, lemon zest, grapefruit oil",
        "days_to_craft": 3,
        "price_cents": 3400,
        "category": "seasonal",
        "stock": 30,
        "is_active": True,
        "is_featured": False,
    },
    {
        "id": "honey-tobacco-oak-300ml",
        "name": "Honey Tobacco & Oak",
        "description": "Rich tobacco leaf, raw honey, and aged oak barrel. "
        "A sophisticated evening scent for the discerning home.",
        "materials": "Coconut-soy blend, tobacco absolute, honey accord, oak moss",
        "days_to_craft": 5,
        "price_cents": 4800,
        "category": "luxury-jar",
        "stock": 8,
        "is_active": True,
        "is_featured": True,
    },
]


def main() -> None:
    """Seed the database with sample products."""
    settings = get_settings()
    init_db(settings.database_path)

    print(f"Seeding {len(SEED_PRODUCTS)} products...")

    for product_data in SEED_PRODUCTS:
        product_id = product_data["id"]
        data = {k: v for k, v in product_data.items() if k != "id"}
        result = product_service.upsert_product(product_id, data)
        print(f"  ✓ {result['id']}: {result['name']}")

    print(f"\nDone! {len(SEED_PRODUCTS)} products seeded.")


if __name__ == "__main__":
    main()
