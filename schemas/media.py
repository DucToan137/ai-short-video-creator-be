from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Union, List
from models.media import MediaType

# Schema for subtitle style
class SubtitleStyle(BaseModel):
    name: str = Field(default="default", description="Style name")
    fontFamily: str = Field(default="Arial", description="Font family")
    fontSize: int = Field(default=16, description="Font size")
    fontColor: str = Field(default="#FFFFFF", description="Font color")
    backgroundColor: str = Field(default="#000000", description="Background color")
    backgroundOpacity: float = Field(default=0.7, description="Background opacity")
    position: str = Field(default="bottom", description="Subtitle position")
    outline: bool = Field(default=True, description="Enable outline")
    outlineColor: str = Field(default="#000000", description="Outline color")

# Schema for creating new media
class MediaCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500, description="Prompt or text content for the media")
    media_type: MediaType = Field(..., description="Type of media")
    metadata: Optional[Dict] = Field(default={}, description="Additional metadata")

# Schema for updating media
class MediaUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=500, description="Prompt or text content for the media")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")

# Schema for video configuration
class VideoSettings(BaseModel):
    min_scene_duration: float = Field(default=3.0, ge=1.0, le=10.0, description="Minimum duration per scene in seconds")
    max_scene_duration: float = Field(default=8.0, ge=3.0, le=15.0, description="Maximum duration per scene in seconds")
    enable_transitions: bool = Field(default=True, description="Enable crossfade transitions between scenes")
    transition_duration: float = Field(default=0.5, ge=0.1, le=2.0, description="Duration of transitions in seconds")

# Schema for voice settings
class VoiceSettings(BaseModel):
    speed: Optional[float] = Field(default=1.0, description="Voice speed (0.5-2.0)")
    pitch: Optional[float] = Field(default=1.0, description="Voice pitch (0.5-2.0)")

# Schema for complete video creation
class CompleteVideoRequest(BaseModel):
    script_text: str = Field(..., description="Script content for the video")
    title: Optional[str] = Field(None, max_length=100, description="Title for the video")
    voice_id: Optional[str] = Field(None, description="ID of the voice to use (for AI voice)")
    audio_url: Optional[str] = Field(None, description="URL of uploaded audio file")
    audio_source: Optional[str] = Field(None, description="Source of audio: 'uploaded', 'generated', 'voice_generation'")
    uploaded_audio_id: Optional[str] = Field(None, description="ID of uploaded audio file")
    voice_settings: Optional[VoiceSettings] = Field(None, description="Voice generation settings")
    background_image_id: str = Field(..., description="ID of the background image (legacy)")
    background_image_ids: Optional[List[str]] = Field(None, description="IDs of multiple background images")
    subtitle_enabled: bool = Field(default=True, description="Whether to enable subtitles")
    subtitle_language: str = Field(default="en", description="Language for subtitles")
    subtitle_style: Union[str, SubtitleStyle] = Field(default="default", description="Style for subtitles")
    video_settings: Optional[VideoSettings] = Field(default=None, description="Advanced video creation settings")

# Schema for video from components
class VideoFromComponentsRequest(BaseModel):
    audio_file_id: str = Field(..., description="ID of the audio file")
    background_image_id: str = Field(..., description="ID of the background image (legacy)")
    background_image_ids: Optional[List[str]] = Field(None, description="IDs of multiple background images")
    script_text: Optional[str] = Field(None, description="Script text for subtitles")
    subtitle_enabled: bool = Field(default=False, description="Whether to enable subtitles")
    subtitle_language: str = Field(default="en", description="Language for subtitles")
    subtitle_style: Union[str, SubtitleStyle] = Field(default="default", description="Style for subtitles")
    video_settings: Optional[VideoSettings] = Field(default=None, description="Advanced video creation settings")

# Schema for media response
class MediaResponse(BaseModel):
    id: str = Field(..., description="Media ID")
    user_id: str = Field(..., description="User ID who owns the media")
    title: Optional[str] = Field(None, description="Title of the media")
    content: str = Field(..., description="Prompt or text content for the media")
    media_type: MediaType = Field(..., description="Type of media")
    url: str = Field(..., description="Cloudinary URL")
    public_id: str = Field(..., description="Cloudinary public ID")
    metadata: Dict = Field(default={}, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

# Schema for media list response
class MediaListResponse(BaseModel):
    media: list[MediaResponse]
    total: int
    page: int
    size: int
    has_next: bool = Field(default=False, description="Whether there are more pages")

# Schema for deleting media
class MediaDelete(BaseModel):
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Deletion message")

# Schema for video statistics response
class MonthlyVideoStats(BaseModel):
    month: int = Field(..., description="Month number (1-12)")
    total_videos: int = Field(..., description="Total videos in this month")
    total_views: int = Field(..., description="Total views in this month")
    total_duration: float = Field(..., description="Total duration in seconds")
    video_count: int = Field(..., description="Number of videos")

class VideoStatsResponse(BaseModel):
    year: int = Field(..., description="Year of the statistics")
    month: Optional[int] = Field(None, description="Specific month (if querying single month)")
    total_videos: int = Field(..., description="Total videos")
    total_views: int = Field(..., description="Total views")
    total_duration: float = Field(..., description="Total duration in seconds")
    monthly_breakdown: Optional[Dict[int, MonthlyVideoStats]] = Field(None, description="Monthly breakdown")
    videos_this_month: Optional[int] = Field(None, description="Videos created this month")
    videos: Optional[List[Dict]] = Field(None, description="List of videos (for single month query)")

# Schema for daily video statistics response
class DailyVideoStatsResponse(BaseModel):
    date: str = Field(..., description="Date in ISO format")
    videos_today: int = Field(..., description="Videos created today")
    videos: Optional[List[Dict]] = Field(None, description="List of videos created today")

# Schema for weekly video statistics response
class WeeklyVideoStatsResponse(BaseModel):
    week_start: str = Field(..., description="Start of week in ISO format")
    week_end: str = Field(..., description="End of week in ISO format")
    videos_this_week: int = Field(..., description="Videos created this week")
    videos: Optional[List[Dict]] = Field(None, description="List of videos created this week")

# Schema for enhanced video statistics response that includes daily and weekly stats
class EnhancedVideoStatsResponse(BaseModel):
    total_videos: int = Field(..., description="Total videos")
    videos_this_month: int = Field(..., description="Videos created this month")
    videos_today: int = Field(..., description="Videos created today")
    videos_this_week: int = Field(..., description="Videos created this week")