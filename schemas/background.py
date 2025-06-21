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

class MultipleBackgroundGenerationRequest(BaseModel):
    """Schema for generating multiple backgrounds from script"""
    script_text: str = Field(..., min_length=1, description="Script text to generate backgrounds from")
    style: str = Field(..., description="Style for background generation")
    count: int = Field(default=3, ge=1, le=10, description="Number of backgrounds to generate")
    image_prompts: Optional[List[str]] = Field(default=None, description="Pre-generated image prompts from cache")

class MultipleBackgroundGenerationResponse(BaseModel):
    """Schema for multiple background generation response"""
    backgrounds: List[BackgroundGenerationResponse] = Field(..., description="List of generated backgrounds")
    style: str = Field(..., description="Style used")
    total_generated: int = Field(..., description="Total number of backgrounds generated")
