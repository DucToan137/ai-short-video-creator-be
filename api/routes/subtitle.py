from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional
from schemas.subtitle import (
    SubtitleRequest,
    SubtitleResponse, 
    SubtitleEditRequest,
    SubtitleApplyRequest,
    SubtitleListResponse,
    SubtitleSegment,
    SubtitleStyle
)
from services.subtitle_service import (
    generate_subtitles_from_audio,
    update_subtitle_segments,
    apply_subtitles_to_video,
    get_available_subtitle_styles,
    get_supported_languages,
    delete_subtitle_files,
    generate_subtitle_preview
)
import os
import tempfile
from uuid import uuid4

router = APIRouter(prefix="/subtitles", tags=["Subtitle Management"])

@router.get("/styles", response_model=SubtitleListResponse)
async def get_subtitle_options():
    """Get available subtitle styles and supported languages"""
    try:
        styles = get_available_subtitle_styles()
        languages = get_supported_languages()
        
        return SubtitleListResponse(
            styles=[SubtitleStyle(**style) for style in styles],
            languages=languages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subtitle options: {str(e)}")

@router.post("/generate", response_model=SubtitleResponse)
async def generate_subtitles_endpoint(
    audio_file: UploadFile = File(...),
    language: Optional[str] = Form("en"),
    max_words_per_segment: Optional[int] = Form(5)
):
    """Generate subtitles from uploaded audio file"""
    try:
        # Save uploaded audio file temporarily
        temp_audio = os.path.join(tempfile.gettempdir(), f"audio_{uuid4().hex[:8]}.wav")
        
        with open(temp_audio, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Generate subtitles
        subtitle_data = generate_subtitles_from_audio(
            temp_audio, 
            language, 
            max_words_per_segment
        )
        
        # Clean up temp audio file
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        
        return SubtitleResponse(
            id=subtitle_data["id"],
            segments=[SubtitleSegment(**seg) for seg in subtitle_data["segments"]],
            language=subtitle_data["language"],
            srt_url=subtitle_data["srt_url"],
            total_duration=subtitle_data["total_duration"]
        )
        
    except Exception as e:
        # Clean up temp file on error
        if 'temp_audio' in locals() and os.path.exists(temp_audio):
            os.remove(temp_audio)
        raise HTTPException(status_code=500, detail=f"Failed to generate subtitles: {str(e)}")

@router.get("/generate-from-script")
async def generate_subtitles_from_script_endpoint(
    script_text: str,
    language: Optional[str] = "en",
    max_words_per_segment: Optional[int] = 5
):
    """Generate subtitles directly from script text (no timing, just segments)"""
    try:
        words = script_text.split()
        segments = []
        
        # Split into segments based on max_words_per_segment
        for i in range(0, len(words), max_words_per_segment):
            segment_words = words[i:i + max_words_per_segment]
            segment_text = " ".join(segment_words)
            
            # Estimate timing (rough calculation)
            start_time = i * 0.5  # 0.5 seconds per word
            end_time = start_time + len(segment_words) * 0.5
            
            segments.append({
                "id": len(segments) + 1,
                "start_time": start_time,
                "end_time": end_time,
                "text": segment_text
            })
        
        total_duration = segments[-1]["end_time"] if segments else 0
        
        return {
            "id": f"script_{uuid4().hex[:8]}",
            "segments": segments,
            "language": language,
            "total_duration": total_duration,
            "source": "script"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate subtitles from script: {str(e)}")

@router.put("/{subtitle_id}", response_model=SubtitleResponse)
async def update_subtitles_endpoint(subtitle_id: str, request: SubtitleEditRequest):
    """Update subtitle segments"""
    try:
        # Convert segments to dict format
        segments_dict = [
            {
                "id": seg.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "text": seg.text
            }
            for seg in request.segments
        ]
        
        # Update subtitles
        subtitle_data = update_subtitle_segments(subtitle_id, segments_dict)
        
        return SubtitleResponse(
            id=subtitle_data["id"],
            segments=[SubtitleSegment(**seg) for seg in subtitle_data["segments"]],
            language="en",  # Default for now
            srt_url=subtitle_data["srt_url"],
            total_duration=subtitle_data["total_duration"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update subtitles: {str(e)}")

@router.post("/apply")
async def apply_subtitles_endpoint(
    video_file: UploadFile = File(...),
    subtitle_id: str = Form(...),
    style_name: Optional[str] = Form("default")
):
    """Apply subtitles to video file"""
    try:
        # Save uploaded video file temporarily
        temp_video = os.path.join(tempfile.gettempdir(), f"video_{uuid4().hex[:8]}.mp4")
        
        with open(temp_video, "wb") as f:
            content = await video_file.read()
            f.write(content)
        
        # Get style
        styles = get_available_subtitle_styles()
        style = next((s for s in styles if s.get("name") == style_name), styles[0])
        
        # Apply subtitles
        result_path = apply_subtitles_to_video(temp_video, subtitle_id, style)
        
        # Clean up temp video file
        if os.path.exists(temp_video):
            os.remove(temp_video)
        
        if not result_path or not os.path.exists(result_path):
            raise HTTPException(status_code=500, detail="Failed to create video with subtitles")
        
        return FileResponse(
            result_path,
            media_type="video/mp4",
            filename=f"video_with_subtitles_{subtitle_id}.mp4"
        )
        
    except Exception as e:
        # Clean up temp files on error
        if 'temp_video' in locals() and os.path.exists(temp_video):
            os.remove(temp_video)
        raise HTTPException(status_code=500, detail=f"Failed to apply subtitles: {str(e)}")

@router.get("/{subtitle_id}/download")
async def download_srt_file(subtitle_id: str):
    """Download SRT file"""
    try:
        from config import TEMP_DIR
        srt_file = os.path.join(TEMP_DIR, f"{subtitle_id}.srt")
        
        if not os.path.exists(srt_file):
            raise HTTPException(status_code=404, detail="Subtitle file not found")
        
        return FileResponse(
            srt_file,
            media_type="text/plain",
            filename=f"subtitles_{subtitle_id}.srt"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download subtitles: {str(e)}")

@router.get("/{subtitle_id}/preview")
async def preview_subtitles(
    subtitle_id: str,
    style_name: Optional[str] = "default"
):
    """Preview how subtitles will look with selected style"""
    try:
        from config import TEMP_DIR
        import json
        
        # Check if subtitle file exists
        srt_file = os.path.join(TEMP_DIR, f"{subtitle_id}.srt")
        if not os.path.exists(srt_file):
            raise HTTPException(status_code=404, detail="Subtitle file not found")
        
        # Parse subtitle segments
        from services.subtitle_service import parse_srt_file
        segments = parse_srt_file(srt_file)
        
        if not segments:
            raise HTTPException(status_code=404, detail="No subtitle segments found")
        
        # Get style
        styles = get_available_subtitle_styles()
        style = next((s for s in styles if s.get("name") == style_name), styles[0])
        
        # Generate preview
        preview_html = generate_subtitle_preview(segments[:3], style)  # Preview first 3 segments
        
        return {
            "preview_html": preview_html,
            "style": style,
            "total_segments": len(segments),
            "sample_segments": segments[:3]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")

@router.delete("/{subtitle_id}")
async def delete_subtitles_endpoint(subtitle_id: str):
    """Delete subtitle files"""
    try:
        delete_subtitle_files(subtitle_id)
        return {"message": f"Subtitle {subtitle_id} deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete subtitles: {str(e)}")

@router.get("/languages/supported")
async def get_supported_languages_endpoint():
    """Get list of supported languages for subtitle generation"""
    try:
        languages = get_supported_languages()
        return {"languages": languages}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get supported languages: {str(e)}")
