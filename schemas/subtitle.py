from pydantic import BaseModel, Field
from typing import List, Optional

class SubtitleSegment(BaseModel):
    """Individual subtitle segment"""
    id: int = Field(..., description="Segment ID")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Subtitle text")

class SubtitleStyle(BaseModel):
    """Subtitle styling options"""
    font_family: Optional[str] = Field("Arial", description="Font family")
    font_size: Optional[int] = Field(16, description="Font size")
    font_color: Optional[str] = Field("#FFFFFF", description="Font color")
    background_color: Optional[str] = Field("#000000", description="Background color")
    background_opacity: Optional[float] = Field(0.7, description="Background opacity (0-1)")
    position: Optional[str] = Field("bottom", description="Position: top, middle, bottom")
    outline: Optional[bool] = Field(True, description="Text outline")
    outline_color: Optional[str] = Field("#000000", description="Outline color")

class SubtitleRequest(BaseModel):
    """Request to generate subtitles from audio"""
    audio_file_id: str = Field(..., description="Audio file identifier")
    language: Optional[str] = Field("en", description="Audio language")
    max_words_per_segment: Optional[int] = Field(5, description="Maximum words per subtitle segment")

class SubtitleResponse(BaseModel):
    """Response containing generated subtitles"""
    id: str = Field(..., description="Subtitle file ID")
    segments: List[SubtitleSegment] = Field(..., description="List of subtitle segments")
    language: str = Field(..., description="Subtitle language")
    srt_url: Optional[str] = Field(None, description="URL to download SRT file")
    total_duration: float = Field(..., description="Total duration in seconds")

class SubtitleEditRequest(BaseModel):
    """Request to edit subtitle segments"""
    subtitle_id: str = Field(..., description="Subtitle file ID")
    segments: List[SubtitleSegment] = Field(..., description="Updated subtitle segments")
    style: Optional[SubtitleStyle] = Field(None, description="Subtitle styling")

class SubtitleApplyRequest(BaseModel):
    """Request to apply subtitles to video"""
    video_file_id: str = Field(..., description="Video file identifier")
    subtitle_id: str = Field(..., description="Subtitle file ID")
    style: Optional[SubtitleStyle] = Field(None, description="Subtitle styling")

class SubtitleListResponse(BaseModel):
    """Response for available subtitle templates"""
    styles: List[SubtitleStyle] = Field(..., description="Available subtitle styles")
    languages: List[str] = Field(..., description="Supported languages")
