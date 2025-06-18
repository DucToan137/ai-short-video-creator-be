"""
Script to seed trending topics database
Run this script to populate the database with initial trending topics data
"""
import asyncio
from services.trending_topics import seed_trending_topics
from config.mongodb_config import test_connection

async def main():
    print("Testing MongoDB connection...")
    connected = await test_connection()
    
    if not connected:
        print("Failed to connect to MongoDB. Please check your connection settings.")
        return
    
    print("Seeding trending topics...")
    await seed_trending_topics()
    print("Seeding completed!")

if __name__ == "__main__":
    asyncio.run(main())
