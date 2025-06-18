from typing import Optional, List, Dict
from datetime import datetime, timedelta
from bson import ObjectId
from config.mongodb_config import trending_topics_collection
import re

async def track_search_keyword(keyword: str, user_id: Optional[str] = None) -> Dict:
    """
    Track user search keyword and update trending scores
    Creates new topic if doesn't exist, or updates existing one
    """
    try:
        # Clean and normalize keyword
        normalized_keyword = keyword.strip().lower()
        if len(normalized_keyword) < 2:
            return {"success": False, "message": "Keyword too short"}
        
        # Check if topic already exists (case-insensitive search)
        existing_topic = await trending_topics_collection().find_one({
            "$or": [
                {"title": {"$regex": f"^{re.escape(keyword)}$", "$options": "i"}},
                {"keywords": {"$regex": f"^{re.escape(normalized_keyword)}$", "$options": "i"}}
            ],
            "is_active": True
        })
        
        if existing_topic:
            # Update existing topic
            await _update_topic_score(existing_topic["_id"], user_id)
            updated_topic = await get_trending_topic_by_id(str(existing_topic["_id"]))
            return {
                "success": True, 
                "action": "updated",
                "topic": updated_topic
            }
        else:
            # Create new topic from search keyword
            new_topic = await _create_topic_from_keyword(keyword, user_id)
            return {
                "success": True,
                "action": "created", 
                "topic": new_topic
            }
            
    except Exception as e:
        print(f"Error tracking search keyword: {e}")
        return {"success": False, "message": str(e)}

async def _create_topic_from_keyword(keyword: str, user_id: Optional[str] = None) -> Dict:
    """Create a new trending topic from user search keyword"""
    try:
        # Determine category based on keyword patterns
        category = _guess_category(keyword)
        
        topic_data = {
            "title": keyword.title(),
            "category": category,
            "keywords": [keyword.lower()],
            "description": f"Trending topic: {keyword}",
            "popularity": 1,  # Start with base score
            "trend_score": 0.1,
            "search_count": 1,
            "user_searches": [user_id] if user_id else [],
            "last_searched": datetime.now(),
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "source": "user_search"
        }
        
        result = await trending_topics_collection().insert_one(topic_data)
        created_topic = await get_trending_topic_by_id(str(result.inserted_id))
        
        print(f"Created new trending topic from keyword: {keyword}")
        return created_topic
        
    except Exception as e:
        print(f"Error creating topic from keyword: {e}")
        return None

async def _update_topic_score(topic_id: ObjectId, user_id: Optional[str] = None) -> bool:
    """Update trending score for existing topic"""
    try:
        # Get current topic data
        topic = await trending_topics_collection().find_one({"_id": topic_id})
        if not topic:
            return False
        
        # Calculate new scores
        current_count = topic.get("search_count", 0)
        new_count = current_count + 1
        
        # Calculate popularity boost based on recent activity
        last_searched = topic.get("last_searched", datetime.now() - timedelta(days=30))
        time_diff = datetime.now() - last_searched
        
        # More recent searches get higher boost
        if time_diff.days < 1:
            popularity_boost = 5
        elif time_diff.days < 7:
            popularity_boost = 3
        elif time_diff.days < 30:
            popularity_boost = 1
        else:
            popularity_boost = 0.5
        
        new_popularity = min(100, topic.get("popularity", 0) + popularity_boost)
        new_trend_score = min(1.0, (new_count * 0.1) + (new_popularity / 100))
        
        # Update user searches list (avoid duplicates)
        user_searches = topic.get("user_searches", [])
        if user_id and user_id not in user_searches:
            user_searches.append(user_id)
            # Keep only last 100 users to avoid too large arrays
            user_searches = user_searches[-100:]
        
        # Update topic
        update_data = {
            "search_count": new_count,
            "popularity": new_popularity,
            "trend_score": new_trend_score,
            "user_searches": user_searches,
            "last_searched": datetime.now(),
            "updated_at": datetime.now()
        }
        
        await trending_topics_collection().update_one(
            {"_id": topic_id},
            {"$set": update_data}
        )
        
        print(f"Updated topic score: {topic['title']} - New popularity: {new_popularity}")
        return True
        
    except Exception as e:
        print(f"Error updating topic score: {e}")
        return False

def _guess_category(keyword: str) -> str:
    """Guess category based on keyword patterns"""
    keyword_lower = keyword.lower()
    
    # Technology keywords
    tech_keywords = ['ai', 'tech', 'digital', 'app', 'software', 'coding', 'programming', 'computer']
    if any(tech in keyword_lower for tech in tech_keywords):
        return "Technology"
    
    # Health keywords  
    health_keywords = ['health', 'fitness', 'medical', 'wellness', 'diet', 'exercise', 'mental']
    if any(health in keyword_lower for health in health_keywords):
        return "Health"
    
    # Food keywords
    food_keywords = ['food', 'recipe', 'cooking', 'meal', 'kitchen', 'restaurant']
    if any(food in keyword_lower for food in food_keywords):
        return "Food"
    
    # Travel keywords
    travel_keywords = ['travel', 'trip', 'vacation', 'destination', 'tourism', 'hotel']
    if any(travel in keyword_lower for travel in travel_keywords):
        return "Travel"
    
    # Finance keywords
    finance_keywords = ['money', 'finance', 'investment', 'crypto', 'bitcoin', 'stock', 'trading']
    if any(finance in keyword_lower for finance in finance_keywords):
        return "Finance"
    
    # Fashion keywords
    fashion_keywords = ['fashion', 'style', 'clothes', 'outfit', 'beauty', 'makeup']
    if any(fashion in keyword_lower for fashion in fashion_keywords):
        return "Fashion"
    
    # Default category
    return "General"

async def get_trending_topic_by_id(topic_id: str) -> Optional[Dict]:
    """Get trending topic by ID with formatted output"""
    try:
        topic = await trending_topics_collection().find_one({"_id": ObjectId(topic_id)})
        if topic:
            topic["id"] = str(topic["_id"])
            topic["created_at"] = topic["created_at"].isoformat()
            topic["updated_at"] = topic["updated_at"].isoformat()
            if "last_searched" in topic:
                topic["last_searched"] = topic["last_searched"].isoformat()
            del topic["_id"]
        return topic
    except Exception as e:
        print(f"Error getting trending topic by ID: {e}")
        return None

async def get_top_trending_keywords(limit: int = 20) -> List[Dict]:
    """Get top trending keywords based on recent activity and scores"""
    try:
        # Get topics sorted by trend_score and recent activity
        cursor = trending_topics_collection().find({
            "is_active": True,
            "search_count": {"$gte": 1}
        }).sort([
            ("trend_score", -1),
            ("popularity", -1),
            ("last_searched", -1)
        ]).limit(limit)
        
        topics = []
        async for topic in cursor:
            topic["id"] = str(topic["_id"])
            topic["created_at"] = topic["created_at"].isoformat()
            topic["updated_at"] = topic["updated_at"].isoformat()
            if "last_searched" in topic:
                topic["last_searched"] = topic["last_searched"].isoformat()
            del topic["_id"]
            topics.append(topic)
        
        return topics
        
    except Exception as e:
        print(f"Error getting top trending keywords: {e}")
        return []

async def search_topics_with_tracking(query: str, user_id: Optional[str] = None, 
                                    page: int = 1, size: int = 10) -> Dict:
    """
    Search topics and track the search for trending analysis
    """
    try:
        # Track the search keyword
        tracking_result = await track_search_keyword(query, user_id)
        
        # Perform the actual search
        skip = (page - 1) * size
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
        
        # Get topics sorted by relevance and trend score
        cursor = trending_topics_collection().find(search_filter).sort([
            ("trend_score", -1),
            ("popularity", -1),
            ("search_count", -1)
        ]).skip(skip).limit(size)
        
        topics = []
        async for topic in cursor:
            topic["id"] = str(topic["_id"])
            topic["created_at"] = topic["created_at"].isoformat() 
            topic["updated_at"] = topic["updated_at"].isoformat()
            if "last_searched" in topic:
                topic["last_searched"] = topic["last_searched"].isoformat()
            del topic["_id"]
            topics.append(topic)
        
        return {
            "topics": topics,
            "total": total,
            "page": page,
            "size": size,
            "tracking": tracking_result
        }
        
    except Exception as e:
        print(f"Error in search with tracking: {e}")
        return {"topics": [], "total": 0, "page": page, "size": size, "tracking": {"success": False}}

async def cleanup_old_searches() -> int:
    """Clean up old search data to maintain performance"""
    try:
        # Remove topics with very low activity that are older than 90 days
        cutoff_date = datetime.now() - timedelta(days=90)
        
        result = await trending_topics_collection().update_many(
            {
                "source": "user_search",
                "search_count": {"$lt": 5},
                "last_searched": {"$lt": cutoff_date}
            },
            {"$set": {"is_active": False}}
        )
        
        print(f"Deactivated {result.modified_count} old search topics")
        return result.modified_count
        
    except Exception as e:
        print(f"Error cleaning up old searches: {e}")
        return 0
