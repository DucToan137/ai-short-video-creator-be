from pydantic import BaseModel
from typing import List, Optional

class WikipediaSource(BaseModel):
    """Schema for Wikipedia source information"""
    title: str
    url: str
    extract: str

class TextGenerationResponse(BaseModel):
    """Enhanced schema for text generation response with Wikipedia sources"""
    text: dict  # The original parsed JSON content (title, script, image_prompts)
    wikipedia_sources: List[WikipediaSource] = []
    wikipedia_topic: Optional[str] = None

class GeneratedContent(BaseModel):
    """Schema for the generated content within text field"""
    title: str
    script: str
    image_prompts: List[str]
