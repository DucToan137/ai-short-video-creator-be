from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from typing import Optional
import os
import tempfile
from datetime import datetime
import asyncio
import httpx

from api.deps import get_current_user
from models.user import User
from services.Media.media_utils import create_video, add_subtitles, upload_media, get_media_by_id
from services.Media.text_to_speech import generate_speech_async
from services.subtitle_service import generate_srt_content
from config import TEMP_DIR
from schemas.media import MediaResponse, CompleteVideoRequest, VideoFromComponentsRequest

router = APIRouter(prefix="/api/video", tags=["video"])

@router.post("/create-complete", response_model=MediaResponse)
async def create_complete_video(
    request: CompleteVideoRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a complete video from script, voice, background, and optionally subtitles
    """
    try:
        user_id = str(current_user.id)        # Step 1: Generate audio from script using voice service
        print("Generating audio from script...")
        from services.voice_service import generate_voice_audio
        audio_result = await generate_voice_audio(
            text=request.script_text,
            voice_id=request.voice_id,
            speed=1.0,  # Default settings for video
            pitch=0,
            user_id=user_id
        )
        
        if not audio_result or not audio_result.get("audio_url"):
            raise HTTPException(status_code=500, detail="Failed to generate audio")
          # Download audio from Cloudinary to temp file for video creation
        audio_path = os.path.join(TEMP_DIR, f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        async with httpx.AsyncClient() as client:
            audio_response = await client.get(audio_result["audio_url"])
            audio_response.raise_for_status()
            with open(audio_path, "wb") as f:
                f.write(audio_response.content)
        
        # Step 2: Get background image
        print("Fetching background image...")
        background_media = await get_media_by_id(request.background_image_id)
        if not background_media:
            raise HTTPException(status_code=404, detail="Background image not found")
          # Download background image to temp file
        background_path = os.path.join(TEMP_DIR, f"bg_{request.background_image_id}.jpg")
        async with httpx.AsyncClient() as client:
            response = await client.get(background_media["url"])
            response.raise_for_status()
            with open(background_path, "wb") as f:
                f.write(response.content)
        
        # Step 3: Create video from image and audio
        print("Creating video from image and audio...")
        video_path = os.path.join(TEMP_DIR, f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        video_result = create_video(background_path, audio_path, video_path)
        
        if not video_result:
            raise HTTPException(status_code=500, detail="Failed to create video")
        
        final_video_path = video_result
          # Step 4: Add subtitles if enabled
        if request.subtitle_enabled:
            print("Adding subtitles to video...")
            # Generate SRT content
            srt_content = generate_srt_content(request.script_text, audio_result.get("duration", 30))
            
            # Save SRT to temp file
            srt_path = os.path.join(TEMP_DIR, f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            
            # Add subtitles to video
            subtitled_video_path = os.path.join(TEMP_DIR, f"final_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            subtitle_result = add_subtitles(video_path, srt_path, subtitled_video_path)
            
            if subtitle_result:
                final_video_path = subtitle_result
                # Clean up intermediate video
                if os.path.exists(video_path):
                    os.remove(video_path)
                if os.path.exists(srt_path):
                    os.remove(srt_path)
          # Step 5: Upload final video to cloud
        print("Uploading final video to cloud...")
          # Convert subtitle_style to string if it's an object
        subtitle_style_str = "default"
        if isinstance(request.subtitle_style, str):
            subtitle_style_str = request.subtitle_style
        elif hasattr(request.subtitle_style, 'name'):
            subtitle_style_str = request.subtitle_style.name
        
        upload_result = await upload_media(
            final_video_path, 
            user_id,
            folder="videos",
            resource_type="video",
            prompt=f"Complete video: {request.script_text[:50]}...",
            metadata={
                "voice_id": request.voice_id,
                "audio_id": audio_result.get("audio_id"),  # Link to audio file
                "background_image_id": request.background_image_id,
                "subtitle_enabled": request.subtitle_enabled,
                "subtitle_language": request.subtitle_language,
                "subtitle_style": subtitle_style_str,
                "script_text": request.script_text[:200]  # Save partial script for reference
            }
        )
          # Clean up temporary files
        for temp_file in [audio_path, background_path, final_video_path]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        # Return MediaResponse with correct structure
        return {
            "id": upload_result["id"],
            "user_id": user_id,
            "content": f"Complete video: {request.script_text[:50]}...",
            "media_type": "VIDEO",
            "url": upload_result["url"],
            "public_id": upload_result["public_id"],
            "metadata": {
                "voice_id": request.voice_id,
                "audio_id": audio_result.get("audio_id"),
                "background_image_id": request.background_image_id,
                "subtitle_enabled": request.subtitle_enabled,
                "subtitle_language": request.subtitle_language,
                "subtitle_style": subtitle_style_str,
                "script_text": request.script_text[:200]
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
    except Exception as e:
        print(f"Error creating complete video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create video: {str(e)}")

@router.post("/create-from-components")
async def create_video_from_components(
    request: VideoFromComponentsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create video from existing audio file and background image
    """
    try:
        user_id = str(current_user.id)
        
        # Get audio file
        audio_media = await get_media_by_id(request.audio_file_id)
        if not audio_media:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Get background image
        background_media = await get_media_by_id(request.background_image_id)
        if not background_media:
            raise HTTPException(status_code=404, detail="Background image not found")
        
        # Download files to temp
        audio_path = os.path.join(TEMP_DIR, f"audio_{request.audio_file_id}.wav")
        background_path = os.path.join(TEMP_DIR, f"bg_{request.background_image_id}.jpg")
        
        async with httpx.AsyncClient() as client:
            # Download audio
            audio_response = await client.get(audio_media["url"])
            audio_response.raise_for_status()
            with open(audio_path, "wb") as f:
                f.write(audio_response.content)
            
            # Download background
            bg_response = await client.get(background_media["url"])
            bg_response.raise_for_status()
            with open(background_path, "wb") as f:
                f.write(bg_response.content)
        
        # Create video
        video_path = os.path.join(TEMP_DIR, f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        video_result = create_video(background_path, audio_path, video_path)
        
        if not video_result:
            raise HTTPException(status_code=500, detail="Failed to create video")
        
        final_video_path = video_result
        
        # Add subtitles if enabled and script provided
        if request.subtitle_enabled and request.script_text:
            srt_content = generate_srt_content(request.script_text, 30)  # Estimate duration
            srt_path = os.path.join(TEMP_DIR, f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.srt")
            
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            
            subtitled_video_path = os.path.join(TEMP_DIR, f"final_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            subtitle_result = add_subtitles(video_path, srt_path, subtitled_video_path)
            
            if subtitle_result:
                final_video_path = subtitle_result
                if os.path.exists(video_path):
                    os.remove(video_path)
                if os.path.exists(srt_path):
                    os.remove(srt_path)
        
        # Upload to cloud
        upload_result = await upload_media(
            final_video_path,
            user_id,
            folder="videos",
            resource_type="video",
            prompt=f"Video from components",
            metadata={
                "audio_file_id": request.audio_file_id,
                "background_image_id": request.background_image_id,
                "subtitle_enabled": request.subtitle_enabled
            }
        )
        
        # Clean up
        for temp_file in [audio_path, background_path, final_video_path]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        return MediaResponse(**upload_result["media"])
        
    except Exception as e:
        print(f"Error creating video from components: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create video: {str(e)}")

@router.get("/download/{video_id}")
async def download_video(
    video_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download video file
    """
    try:
        # Get video metadata
        video_media = await get_media_by_id(video_id)
        if not video_media:
            raise HTTPException(status_code=404, detail="Video not found")
          # Check if user owns the video
        if str(video_media["user_id"]) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")        
        # Download video to temp file
        temp_video_path = os.path.join(TEMP_DIR, f"download_{video_id}.mp4")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(video_media["url"])
            response.raise_for_status()
            with open(temp_video_path, "wb") as f:
                f.write(response.content)
        
        # Return file for download
        return FileResponse(
            temp_video_path,
            media_type="video/mp4",
            filename=f"{video_media.get('prompt', 'video')}.mp4"
        )
        
    except Exception as e:
        print(f"Error downloading video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

@router.get("/preview/{video_id}")
async def preview_video(
    video_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get video URL for preview
    """
    try:
        video_media = await get_media_by_id(video_id)
        if not video_media:
            raise HTTPException(status_code=404, detail="Video not found")
          # Check if user owns the video
        if str(video_media["user_id"]) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "video_url": video_media["url"],
            "title": video_media.get("prompt", "Video"),
            "duration": video_media.get("metadata", {}).get("duration"),
            "created_at": video_media["created_at"]
        }
        
    except Exception as e:
        print(f"Error getting video preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get video: {str(e)}")
