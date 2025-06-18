from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from models import PyObjectId

class TrendingTopicModel(BaseModel):
    """Model for trending topics"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str = Field(..., min_length=1, max_length=200, description="Topic title")
    category: str = Field(..., min_length=1, max_length=50, description="Topic category")
    keywords: List[str] = Field(default=[], description="Related keywords")
    popularity: int = Field(default=0, ge=0, le=100, description="Popularity score (0-100)")
    description: Optional[str] = Field(None, max_length=500, description="Topic description")
    trend_score: float = Field(default=0.0, ge=0.0, description="Trending score")
    is_active: bool = Field(default=True, description="Whether topic is active")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
