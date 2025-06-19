from pydantic import BaseModel, Field
from typing import List, Optional

class VoiceBase(BaseModel):
    """Base voice schema"""
    name: str = Field(..., description="Voice name")
    gender: str = Field(..., description="Voice gender (male/female/neutral)")
    language: str = Field(..., description="Voice language")
    accent: Optional[str] = Field(None, description="Voice accent")
    tags: List[str] = Field(default=[], description="Voice tags")

class VoiceResponse(VoiceBase):
    """Voice response schema"""
    id: str = Field(..., description="Voice ID")
    preview_url: Optional[str] = Field(None, description="Preview audio URL")
    available: bool = Field(default=True, description="Whether voice is available")

class VoiceSettings(BaseModel):
    """Voice generation settings"""
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speaking speed (0.5-2.0)")
    pitch: int = Field(default=0, ge=-10, le=10, description="Voice pitch (-10 to +10)")

class VoiceGenerationRequest(BaseModel):
    """Voice generation request"""
    text: str = Field(..., min_length=1, description="Text to convert to speech")
    voice_id: str = Field(..., description="Voice ID to use")
    settings: Optional[VoiceSettings] = Field(default=None, description="Voice settings")

class VoiceGenerationResponse(BaseModel):
    """Voice generation response"""
    audio_url: str = Field(..., description="Generated audio file URL")
    duration: float = Field(..., description="Audio duration in seconds")
    voice_id: str = Field(..., description="Voice ID used")
    settings: VoiceSettings = Field(..., description="Settings used")
