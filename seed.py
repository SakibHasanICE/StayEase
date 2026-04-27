"""
Run once to seed the listings table with sample data.
Usage: python seed.py
"""
import asyncio
from app.config.database import engine, Base, AsyncSessionLocal
from app.config.models import Listing


SAMPLE_LISTINGS = [
    Listing(
        name="Ocean View Suite",
        location="Cox's Bazar",
        description="Spacious suite with direct ocean view on Marine Drive.",
        address="Marine Drive Road, Cox's Bazar",
        price_per_night=4500,
        max_guests=4,
        amenities=["WiFi", "AC", "Sea View", "Hot Water"],
        
        cancellation_policy="Free cancellation 48 hours before check-in.",
    ),
    Listing(
        name="Sundarbans Eco Lodge",
        location="Khulna",
        description="Eco-friendly lodge on the edge of the Sundarbans mangrove forest.",
        address="Forest Road, Mongla, Khulna",
        price_per_night=3200,
        max_guests=3,
        amenities=["WiFi", "Fan", "River View", "Boat Tours"],
    
        cancellation_policy="Free cancellation 72 hours before check-in.",
    ),
    Listing(
        name="Sylhet Tea Garden Retreat",
        location="Sylhet",
        description="Peaceful bungalow surrounded by lush tea gardens in Srimangal.",
        address="Tea Garden Road, Srimangal, Sylhet",
        price_per_night=5800,
        max_guests=6,
        amenities=["WiFi", "AC", "Garden View", "Breakfast Included", "Parking"],
       
        cancellation_policy="Free cancellation 24 hours before check-in.",
    ),
    Listing(
        name="Dhaka City Center Apartment",
        location="Dhaka",
        description="Modern serviced apartment in Gulshan with city skyline views.",
        address="Gulshan Avenue, Gulshan-2, Dhaka",
        price_per_night=6500,
        max_guests=2,
        amenities=["WiFi", "AC", "City View", "Gym", "24/7 Security"],
       
        cancellation_policy="Non-refundable.",
    ),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        db.add_all(SAMPLE_LISTINGS)
        await db.commit()
        print(f"✅ Seeded {len(SAMPLE_LISTINGS)} listings.")


if __name__ == "__main__":
    asyncio.run(seed())