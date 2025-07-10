from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from schemas.trending_topic import (
    TrendingTopicCreate, 
    TrendingTopicUpdate, 
    TrendingTopicResponse, 
    TrendingTopicListResponse,
    TrendingTopicDelete
)
from services.trending_topics import (
    get_trending_topics,
    get_trending_topic_by_id,
    search_trending_topics,
    create_trending_topic,
    update_trending_topic,
    delete_trending_topic,
    get_trending_categories,
    seed_trending_topics,
    suggest_trending_topics
)
from services.internet_trends import (
    search_topics_with_tracking,
    track_search_keyword,
    get_top_trending_keywords
)
from api.deps import get_current_user

router = APIRouter(prefix="/trending", tags=["Trending Topics"])

@router.get("/topics", response_model=TrendingTopicListResponse)
async def get_trending_topics_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    category: Optional[str] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only active topics")
):
    """Get trending topics with pagination and optional filtering"""
    result = await get_trending_topics(page, size, category, active_only)
    
    topic_responses = [TrendingTopicResponse(**topic) for topic in result["topics"]]
    
    return TrendingTopicListResponse(
        topics=topic_responses,
        total=result["total"],
        page=result["page"],
        size=result["size"]
    )

@router.get("/topics/search", response_model=TrendingTopicListResponse)
async def search_trending_topics_endpoint(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    track: bool = Query(True, description="Track search for trending analysis")
):
    """Search trending topics by title, category, or keywords with optional tracking"""
    if track:
        # Use tracking search that saves keywords and updates scores
        result = await search_topics_with_tracking(q, None, page, size)
    else:
        # Use regular search without tracking
        result = await search_trending_topics(q, page, size)
    
    topic_responses = [TrendingTopicResponse(**topic) for topic in result["topics"]]
    
    response = TrendingTopicListResponse(
        topics=topic_responses,
        total=result["total"],
        page=result["page"],
        size=result["size"]
    )
    
    # Add tracking info if available
    if "tracking" in result:
        response.tracking = result["tracking"]
        return response

@router.get("/hot-keywords")
async def get_hot_keywords_endpoint(
    limit: int = Query(20, ge=1, le=50, description="Number of keywords to return")
):
    """Get currently hot trending keywords based on recent search activity"""
    keywords = await get_top_trending_keywords(limit)
    return {"keywords": keywords}

@router.post("/track-search")
async def track_search_endpoint(
    keyword: str = Query(..., description="Search keyword to track"),
    current_user = Depends(get_current_user)
):
    """Manually track a search keyword (for authenticated users)"""
    user_id = str(current_user.id) if current_user else None
    result = await track_search_keyword(keyword, user_id)
    return result

@router.get("/topics/{topic_id}", response_model=TrendingTopicResponse)
async def get_trending_topic(topic_id: str):
    """Get trending topic by ID"""
    topic = await get_trending_topic_by_id(topic_id)
    
    if not topic:
        raise HTTPException(status_code=404, detail="Trending topic not found")
    
    return TrendingTopicResponse(**topic)

@router.get("/categories")
async def get_trending_categories_endpoint():
    """Get list of all trending topic categories"""
    categories = await get_trending_categories()
    return {"categories": categories}

@router.post("/topics", response_model=TrendingTopicResponse)
async def create_trending_topic_endpoint(
    topic_create: TrendingTopicCreate,
    current_user = Depends(get_current_user)
):
    """Create a new trending topic (Admin only)"""
    topic_data = topic_create.model_dump()
    
    created_topic = await create_trending_topic(topic_data)
    
    if not created_topic:
        raise HTTPException(status_code=500, detail="Failed to create trending topic")
    
    return TrendingTopicResponse(**created_topic)

@router.put("/topics/{topic_id}", response_model=TrendingTopicResponse)
async def update_trending_topic_endpoint(
    topic_id: str,
    topic_update: TrendingTopicUpdate,
    current_user = Depends(get_current_user)
):
    """Update trending topic (Admin only)"""
    # Filter out None values
    update_data = {k: v for k, v in topic_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")
    
    updated_topic = await update_trending_topic(topic_id, update_data)
    
    if not updated_topic:
        raise HTTPException(status_code=404, detail="Trending topic not found")
    
    return TrendingTopicResponse(**updated_topic)

@router.delete("/topics/{topic_id}", response_model=TrendingTopicDelete)
async def delete_trending_topic_endpoint(
    topic_id: str,
    current_user = Depends(get_current_user)
):
    """Delete trending topic (Admin only)"""
    success = await delete_trending_topic(topic_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Trending topic not found")
    
    return TrendingTopicDelete(
        success=True,
        message="Trending topic deleted successfully"
    )

@router.post("/topics/seed")
async def seed_trending_topics_endpoint(
    current_user = Depends(get_current_user)
):
    """Seed database with initial trending topics (Admin only)"""
    try:
        await seed_trending_topics()
        return {"message": "Successfully seeded trending topics"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed trending topics: {str(e)}")

@router.get("/suggestions")
async def get_topic_suggestions(
    q: str = Query(..., description="Search query for suggestions"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of suggestions")
):
    """Get search suggestions for trending topics as user types"""
    suggestions = await suggest_trending_topics(q, limit)
    return {"suggestions": suggestions}
