from pydantic import BaseModel, Field
from typing import List, Optional

class BackgroundResponse(BaseModel):
    """Schema for background response"""
    id: str = Field(..., description="Background ID")
    title: str = Field(..., description="Background title")
    category: str = Field(..., description="Background category")
    image_url: str = Field(..., description="Background image URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    tags: List[str] = Field(default=[], description="Background tags")
    premium: bool = Field(default=False, description="Whether background is premium")
    available: bool = Field(default=True, description="Whether background is available")

class BackgroundListResponse(BaseModel):
    """Schema for background list response"""
    backgrounds: List[BackgroundResponse] = Field(..., description="List of available backgrounds")
    total: int = Field(..., description="Total number of backgrounds")
    categories: List[str] = Field(default=[], description="Available categories")

class BackgroundGenerationRequest(BaseModel):
    """Schema for custom background generation"""
    prompt: str = Field(..., min_length=1, max_length=500, description="Description of background to generate")
    style: Optional[str] = Field("realistic", description="Generation style: realistic, abstract, cartoon")
    resolution: Optional[str] = Field("1080x1920", description="Image resolution for vertical video")

class BackgroundGenerationResponse(BaseModel):
    """Schema for background generation response"""
    id: str = Field(..., description="Generated background ID")
    image_url: str = Field(..., description="Generated background image URL")
    prompt: str = Field(..., description="Prompt used for generation")
    style: str = Field(..., description="Style used")
    resolution: str = Field(..., description="Image resolution")
