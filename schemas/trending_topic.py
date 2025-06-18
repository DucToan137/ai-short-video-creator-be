from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TrendingTopicCreate(BaseModel):
    """Schema for creating trending topic"""
    title: str = Field(..., min_length=1, max_length=200, description="Topic title")
    category: str = Field(..., min_length=1, max_length=50, description="Topic category")
    keywords: List[str] = Field(default=[], description="Related keywords")
    description: Optional[str] = Field(None, max_length=500, description="Topic description")
    popularity: int = Field(default=50, ge=0, le=100, description="Popularity score (0-100)")

class TrendingTopicUpdate(BaseModel):
    """Schema for updating trending topic"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Topic title")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="Topic category")
    keywords: Optional[List[str]] = Field(None, description="Related keywords")
    description: Optional[str] = Field(None, max_length=500, description="Topic description")
    popularity: Optional[int] = Field(None, ge=0, le=100, description="Popularity score (0-100)")

class TrendingTopicResponse(BaseModel):
    """Schema for trending topic response"""
    id: str = Field(..., description="Topic ID")
    title: str = Field(..., description="Topic title")
    category: str = Field(..., description="Topic category")
    keywords: List[str] = Field(default=[], description="Related keywords")
    description: Optional[str] = Field(None, description="Topic description")
    popularity: int = Field(..., description="Popularity score (0-100)")
    trend_score: float = Field(default=0.0, description="Trending score")
    is_active: bool = Field(default=True, description="Whether topic is active")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")

class TrendingTopicListResponse(BaseModel):
    """Schema for trending topic list response"""
    topics: List[TrendingTopicResponse] = Field(..., description="List of trending topics")
    total: int = Field(..., description="Total number of topics")
    page: int = Field(default=1, description="Current page number")
    size: int = Field(default=10, description="Page size")
    tracking: Optional[dict] = Field(None, description="Search tracking information")

class TrendingTopicDelete(BaseModel):
    """Schema for trending topic deletion response"""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Response message")
