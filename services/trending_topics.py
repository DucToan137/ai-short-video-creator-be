from typing import Optional, List, Dict
from datetime import datetime
from bson import ObjectId
from config.mongodb_config import trending_topics_collection

async def create_trending_topic(topic_data: Dict) -> Dict:
    """Create a new trending topic"""
    try:
        topic_data["created_at"] = datetime.now()
        topic_data["updated_at"] = datetime.now()
        topic_data["is_active"] = True
        topic_data["trend_score"] = topic_data.get("popularity", 50) / 100.0
        
        result = await trending_topics_collection().insert_one(topic_data)
        
        # Return the created topic
        created_topic = await get_trending_topic_by_id(str(result.inserted_id))
        return created_topic
    except Exception as e:
        print(f"Error creating trending topic: {e}")
        return None

async def get_trending_topic_by_id(topic_id: str) -> Optional[Dict]:
    """Get trending topic by ID"""
    try:
        topic = await trending_topics_collection().find_one({"_id": ObjectId(topic_id)})
        if topic:
            topic["id"] = str(topic["_id"])
            topic["created_at"] = topic["created_at"].isoformat()
            topic["updated_at"] = topic["updated_at"].isoformat()
            del topic["_id"]
        return topic
    except Exception as e:
        print(f"Error getting trending topic by ID: {e}")
        return None

async def get_trending_topics(page: int = 1, size: int = 10, category: Optional[str] = None, 
                             active_only: bool = True) -> Dict:
    """Get trending topics with pagination and optional filtering"""
    try:
        skip = (page - 1) * size
        
        # Build filter
        filter_query = {}
        if active_only:
            filter_query["is_active"] = True
        if category:
            filter_query["category"] = {"$regex": category, "$options": "i"}
        
        # Get total count
        total = await trending_topics_collection().count_documents(filter_query)
        
        # Get topics with sorting by popularity and trend_score
        cursor = trending_topics_collection().find(filter_query).sort([
            ("popularity", -1),
            ("trend_score", -1),
            ("created_at", -1)
        ]).skip(skip).limit(size)
        
        topics = []
        async for topic in cursor:
            topic["id"] = str(topic["_id"])
            topic["created_at"] = topic["created_at"].isoformat()
            topic["updated_at"] = topic["updated_at"].isoformat()
            del topic["_id"]
            topics.append(topic)
        
        return {
            "topics": topics,
            "total": total,
            "page": page,
            "size": size
        }
    except Exception as e:
        print(f"Error getting trending topics: {e}")
        return {"topics": [], "total": 0, "page": page, "size": size}

async def search_trending_topics(query: str, page: int = 1, size: int = 10) -> Dict:
    """Search trending topics by title, category, or keywords"""
    try:
        skip = (page - 1) * size
        
        # Build search filter
        search_filter = {
            "$and": [
                {"is_active": True},
                {
                    "$or": [
                        {"title": {"$regex": query, "$options": "i"}},
                        {"category": {"$regex": query, "$options": "i"}},
                        {"keywords": {"$regex": query, "$options": "i"}},
                        {"description": {"$regex": query, "$options": "i"}}
                    ]
                }
            ]
        }
        
        # Get total count
        total = await trending_topics_collection().count_documents(search_filter)
        
        # Get topics
        cursor = trending_topics_collection().find(search_filter).sort([
            ("popularity", -1),
            ("trend_score", -1)
        ]).skip(skip).limit(size)
        
        topics = []
        async for topic in cursor:
            topic["id"] = str(topic["_id"])
            topic["created_at"] = topic["created_at"].isoformat()
            topic["updated_at"] = topic["updated_at"].isoformat()
            del topic["_id"]
            topics.append(topic)
        
        return {
            "topics": topics,
            "total": total,
            "page": page,
            "size": size
        }
    except Exception as e:
        print(f"Error searching trending topics: {e}")
        return {"topics": [], "total": 0, "page": page, "size": size}

async def update_trending_topic(topic_id: str, update_data: Dict) -> Optional[Dict]:
    """Update trending topic"""
    try:
        update_data["updated_at"] = datetime.now()
        if "popularity" in update_data:
            update_data["trend_score"] = update_data["popularity"] / 100.0
        
        result = await trending_topics_collection().update_one(
            {"_id": ObjectId(topic_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await get_trending_topic_by_id(topic_id)
        return None
    except Exception as e:
        print(f"Error updating trending topic: {e}")
        return None

async def delete_trending_topic(topic_id: str) -> bool:
    """Delete trending topic (soft delete by setting is_active to False)"""
    try:
        result = await trending_topics_collection().update_one(
            {"_id": ObjectId(topic_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now()}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error deleting trending topic: {e}")
        return False

async def get_trending_categories() -> List[str]:
    """Get list of all trending topic categories"""
    try:
        categories = await trending_topics_collection().distinct("category", {"is_active": True})
        return sorted(categories)
    except Exception as e:
        print(f"Error getting trending categories: {e}")
        return []

async def seed_trending_topics():
    """Seed database with initial trending topics"""
    try:
        # Check if topics already exist
        count = await trending_topics_collection().count_documents({})
        if count > 0:
            print("Trending topics already exist, skipping seed.")
            return
        
        sample_topics = [
            {
                "title": "Sustainable Fashion",
                "category": "Lifestyle",
                "keywords": ["eco-friendly", "sustainable", "fashion", "environmentally friendly", "green fashion"],
                "description": "Learn about sustainable fashion practices and eco-friendly clothing choices",
                "popularity": 97
            },
            {
                "title": "AI in Healthcare",
                "category": "Technology", 
                "keywords": ["artificial intelligence", "healthcare", "medical technology", "AI diagnosis", "healthcare innovation"],
                "description": "Explore how AI is revolutionizing healthcare and medical diagnostics",
                "popularity": 95
            },
            {
                "title": "Easy Meal Prep",
                "category": "Food",
                "keywords": ["meal prep", "quick recipes", "healthy meals", "food preparation", "cooking tips"],
                "description": "Simple and effective meal preparation strategies for busy lifestyles",
                "popularity": 92
            },
            {
                "title": "Minimalist Living",
                "category": "Lifestyle",
                "keywords": ["minimalism", "decluttering", "simple living", "minimal lifestyle", "organization"],
                "description": "Embrace minimalist principles for a simpler, more intentional lifestyle",
                "popularity": 89
            },
            {
                "title": "Digital Nomad Life",
                "category": "Travel",
                "keywords": ["digital nomad", "remote work", "travel lifestyle", "working abroad", "nomadic living"],
                "description": "Guide to living and working as a digital nomad",
                "popularity": 88
            },
            {
                "title": "Fitness at Home",
                "category": "Fitness",
                "keywords": ["home workout", "fitness", "exercise", "home gym", "workout routine"],
                "description": "Effective fitness routines you can do from the comfort of your home",
                "popularity": 87
            },
            {
                "title": "Cryptocurrency Basics",
                "category": "Finance",
                "keywords": ["crypto", "bitcoin", "blockchain", "investing", "digital currency"],
                "description": "Understanding cryptocurrency and blockchain technology basics",
                "popularity": 85
            },
            {
                "title": "Mental Health Awareness",
                "category": "Health",
                "keywords": ["mental health", "wellness", "self-care", "mindfulness", "psychology"],
                "description": "Important information about mental health and wellness practices",
                "popularity": 91
            }
        ]
        
        for topic_data in sample_topics:
            await create_trending_topic(topic_data)
        
        print(f"Successfully seeded {len(sample_topics)} trending topics")
        
    except Exception as e:
        print(f"Error seeding trending topics: {e}")
