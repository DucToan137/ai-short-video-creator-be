from typing import List, Dict, Optional
import os
from services.Media.text_to_speech import generate_speech
from config import TEMP_DIR
from uuid import uuid4

# Voice data mapping from frontend mockdata with real Groq voices
AVAILABLE_VOICES = [
    {
        "id": "v1",
        "name": "Alex",
        "gender": "male", 
        "language": "English",
        "accent": "American",
        "tags": ["clear", "professional", "authoritative"],
        "groq_voice": "Fritz-PlayAI"  # Male, clear voice
    },
    {
        "id": "v2", 
        "name": "Sophie",
        "gender": "female",
        "language": "English", 
        "accent": "British",
        "tags": ["warm", "friendly", "engaging"],
        "groq_voice": "Eleanor-PlayAI"  # Female, British-like voice
    },
    {
        "id": "v3",
        "name": "Michael", 
        "gender": "male",
        "language": "English",
        "accent": "Australian", 
        "tags": ["casual", "conversational", "relaxed"],
        "groq_voice": "Calum-PlayAI"  # Male, casual voice
    },
    {
        "id": "v4",
        "name": "Emma",
        "gender": "female",
        "language": "English", 
        "accent": "American",
        "tags": ["energetic", "youthful", "upbeat"],
        "groq_voice": "Cheyenne-PlayAI"  # Female, energetic voice
    },
    {
        "id": "v5",
        "name": "Sam",
        "gender": "neutral",
        "language": "English",
        "tags": ["neutral", "balanced", "clear"],
        "groq_voice": "Quinn-PlayAI"  # Neutral voice
    },
    {
        "id": "v6",
        "name": "Hiroshi",
        "gender": "male",
        "language": "Japanese", 
        "tags": ["professional", "calm", "measured"],
        "groq_voice": "Mikail-PlayAI"  # Male, professional voice
    },
    {
        "id": "v7",
        "name": "Maria",
        "gender": "female",
        "language": "Spanish",
        "accent": "Latin American",
        "tags": ["warm", "friendly", "expressive"], 
        "groq_voice": "Celeste-PlayAI"  # Female, expressive voice
    },
    {
        "id": "v8",
        "name": "Antoine",
        "gender": "male",
        "language": "French",
        "tags": ["sophisticated", "clear", "articulate"],
        "groq_voice": "Angelo-PlayAI"  # Male, sophisticated voice
    },
    # Add more Groq voices to give users more options
    {
        "id": "v9",
        "name": "Ruby",
        "gender": "female",
        "language": "English",
        "accent": "American",
        "tags": ["mature", "authoritative", "news"],
        "groq_voice": "Ruby-PlayAI"  # Female, news anchor style
    },
    {
        "id": "v10",
        "name": "Thunder",
        "gender": "male",
        "language": "English",
        "accent": "American",
        "tags": ["deep", "powerful", "dramatic"],
        "groq_voice": "Thunder-PlayAI"  # Male, deep voice
    },
    {
        "id": "v11",
        "name": "Jennifer",
        "gender": "female",
        "language": "English",
        "accent": "American",
        "tags": ["professional", "clear", "business"],
        "groq_voice": "Jennifer-PlayAI"  # Female, business voice
    },
    {
        "id": "v12",
        "name": "Mason",
        "gender": "male",
        "language": "English",
        "accent": "American",
        "tags": ["young", "friendly", "casual"],
        "groq_voice": "Mason-PlayAI"  # Male, young voice
    }
]

def get_all_voices() -> List[Dict]:
    """Get all available voices"""
    return [
        {
            "id": voice["id"],
            "name": voice["name"], 
            "gender": voice["gender"],
            "language": voice["language"],
            "accent": voice.get("accent"),
            "tags": voice["tags"],
            "preview_url": f"/assets/sounds/voice-preview-{voice['id']}.mp3",
            "available": True
        }
        for voice in AVAILABLE_VOICES
    ]

def get_voice_by_id(voice_id: str) -> Optional[Dict]:
    """Get voice by ID"""
    for voice in AVAILABLE_VOICES:
        if voice["id"] == voice_id:
            return {
                "id": voice["id"],
                "name": voice["name"],
                "gender": voice["gender"], 
                "language": voice["language"],
                "accent": voice.get("accent"),
                "tags": voice["tags"],
                "preview_url": f"/assets/sounds/voice-preview-{voice['id']}.mp3",
                "available": True
            }
    return None

def get_voices_by_language(language: str) -> List[Dict]:
    """Get voices filtered by language"""
    return [
        voice for voice in get_all_voices()
        if voice["language"].lower() == language.lower()
    ]

def get_voices_by_gender(gender: str) -> List[Dict]:
    """Get voices filtered by gender"""
    return [
        voice for voice in get_all_voices()
        if voice["gender"].lower() == gender.lower()
    ]

async def generate_voice_audio(text: str, voice_id: str, speed: float = 1.0, pitch: int = 0, user_id: str = None) -> Dict:
    """
    Generate audio from text using specified voice and settings
    
    Args:
        text: Text to convert to speech
        voice_id: Voice ID to use
        speed: Speaking speed (0.5-2.0) 
        pitch: Voice pitch (-10 to +10)
        user_id: User ID for Cloudinary upload
        
    Returns:
        Dict with audio_url, duration, voice_id, and settings
    """
    try:
        # Find voice configuration
        voice_config = None
        for voice in AVAILABLE_VOICES:
            if voice["id"] == voice_id:
                voice_config = voice
                break
                
        # Fallback to default voice if not found
        if not voice_config:
            print(f"Warning: Voice {voice_id} not found, using default Fritz-PlayAI")
            voice_config = {
                "id": voice_id,
                "name": "Default",
                "groq_voice": "Fritz-PlayAI"
            }
        
        # Use Groq TTS with the mapped voice
        groq_voice = voice_config["groq_voice"]
        print(f"Using Groq voice: {groq_voice} for voice_id: {voice_id}")
        
        # Generate speech using async version with Cloudinary upload
        from services.Media.text_to_speech import generate_speech_async
        result = await generate_speech_async(text, groq_voice, user_id)
        
        if not result:
            raise Exception("Failed to generate audio")
        
        # Calculate adjusted duration for speed
        base_duration = result["duration"]
        adjusted_duration = base_duration / speed  # Adjust for speed
        
        # Return result with Cloudinary URL if available, otherwise fallback URL
        audio_url = result.get("audio_url", f"/media/audio/{os.path.basename(result.get('audio_path', 'unknown.wav'))}")
        
        return {
            "audio_url": audio_url,
            "duration": adjusted_duration,
            "voice_id": voice_id,
            "settings": {
                "speed": speed,
                "pitch": pitch
            },
            "audio_id": result.get("audio_id"),  # For database reference
            "cloudinary_public_id": result.get("cloudinary_public_id")  # For Cloudinary reference
        }
        
    except Exception as e:
        raise Exception(f"Voice generation failed: {str(e)}")

def get_voice_languages() -> List[str]:
    """Get list of available languages"""
    languages = set()
    for voice in AVAILABLE_VOICES:
        languages.add(voice["language"])
    return sorted(list(languages))

def get_voice_genders() -> List[str]:
    """Get list of available genders"""
    genders = set()
    for voice in AVAILABLE_VOICES:
        genders.add(voice["gender"])
    return sorted(list(genders))
