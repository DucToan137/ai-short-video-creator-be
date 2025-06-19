from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from schemas.voice import VoiceResponse, VoiceGenerationRequest, VoiceGenerationResponse
from services.voice_service import (
    get_all_voices,
    get_voice_by_id, 
    get_voices_by_language,
    get_voices_by_gender,
    generate_voice_audio,
    get_voice_languages,
    get_voice_genders
)
import os

router = APIRouter(prefix="/voices", tags=["Voice Management"])

@router.get("/", response_model=List[VoiceResponse])
async def get_voices(
    language: Optional[str] = Query(None, description="Filter by language"),
    gender: Optional[str] = Query(None, description="Filter by gender")
):
    """Get all available voices with optional filtering"""
    try:
        if language:
            voices = get_voices_by_language(language)
        elif gender:
            voices = get_voices_by_gender(gender)
        else:
            voices = get_all_voices()
            
        return [VoiceResponse(**voice) for voice in voices]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get voices: {str(e)}")

@router.get("/{voice_id}", response_model=VoiceResponse)
async def get_voice(voice_id: str):
    """Get voice by ID"""
    voice = get_voice_by_id(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    return VoiceResponse(**voice)

@router.get("/languages/available")
async def get_available_languages():
    """Get list of available voice languages"""
    return {"languages": get_voice_languages()}

@router.get("/genders/available") 
async def get_available_genders():
    """Get list of available voice genders"""
    return {"genders": get_voice_genders()}

@router.post("/generate", response_model=VoiceGenerationResponse)
async def generate_voice(request: VoiceGenerationRequest):
    """Generate audio from text using specified voice"""
    try:
        # Validate voice exists
        voice = get_voice_by_id(request.voice_id)
        if not voice:
            raise HTTPException(status_code=404, detail="Voice not found")
        
        # Extract settings
        settings = request.settings or {}
        speed = getattr(settings, 'speed', 1.0)
        pitch = getattr(settings, 'pitch', 0)
        
        # Generate audio
        result = generate_voice_audio(
            text=request.text,
            voice_id=request.voice_id,
            speed=speed,
            pitch=pitch
        )
        
        return VoiceGenerationResponse(
            audio_url=result["audio_url"],
            duration=result["duration"], 
            voice_id=result["voice_id"],
            settings=result["settings"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice generation failed: {str(e)}")

@router.get("/preview/{voice_id}")
async def get_voice_preview(voice_id: str):
    """Get voice preview audio (placeholder)"""
    # In a real implementation, this would return actual preview audio
    # For now, return a placeholder response
    voice = get_voice_by_id(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    return {
        "message": f"Preview for voice {voice['name']} ({voice_id})",
        "preview_text": "Hello, this is a preview of my voice. I can help you create amazing videos with natural-sounding speech."
    }

@router.get("/audio/{voice_id}/{filename}")
async def get_generated_audio(voice_id: str, filename: str):
    """Serve generated audio files"""
    # This endpoint serves the generated audio files
    # In a production environment, you'd typically use a CDN or cloud storage
    from config import TEMP_DIR
    import os
    
    file_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        file_path,
        media_type="audio/wav",
        filename=filename
    )
