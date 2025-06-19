from typing import List, Dict, Optional
import os
from services.Media.text_to_speech import generate_speech
from config import TEMP_DIR
from uuid import uuid4

# Voice data mapping from frontend mockdata
AVAILABLE_VOICES = [
    {
        "id": "v1",
        "name": "Alex",
        "gender": "male", 
        "language": "English",
        "accent": "American",
        "tags": ["clear", "professional", "authoritative"],
        "groq_voice": "Fritz-PlayAI"  # Default Groq voice
    },
    {
        "id": "v2", 
        "name": "Sophie",
        "gender": "female",
        "language": "English", 
        "accent": "British",
        "tags": ["warm", "friendly", "engaging"],
        "groq_voice": "Fritz-PlayAI"
    },
    {
        "id": "v3",
        "name": "Michael", 
        "gender": "male",
        "language": "English",
        "accent": "Australian", 
        "tags": ["casual", "conversational", "relaxed"],
        "groq_voice": "Fritz-PlayAI"
    },
    {
        "id": "v4",
        "name": "Emma",
        "gender": "female",
        "language": "English", 
        "accent": "American",
        "tags": ["energetic", "youthful", "upbeat"],
        "groq_voice": "Fritz-PlayAI"
    },
    {
        "id": "v5",
        "name": "Sam",
        "gender": "neutral",
        "language": "English",
        "tags": ["neutral", "balanced", "clear"],
        "groq_voice": "Fritz-PlayAI"
    },
    {
        "id": "v6",
        "name": "Hiroshi",
        "gender": "male",
        "language": "Japanese", 
        "tags": ["professional", "calm", "measured"],
        "groq_voice": "Fritz-PlayAI"
    },
    {
        "id": "v7",
        "name": "Maria",
        "gender": "female",
        "language": "Spanish",
        "accent": "Latin American",
        "tags": ["warm", "friendly", "expressive"], 
        "groq_voice": "Fritz-PlayAI"
    },
    {
        "id": "v8",
        "name": "Antoine",
        "gender": "male",
        "language": "French",
        "tags": ["sophisticated", "clear", "articulate"],
        "groq_voice": "Fritz-PlayAI"
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

def generate_voice_audio(text: str, voice_id: str, speed: float = 1.0, pitch: int = 0) -> Dict:
    """
    Generate audio from text using specified voice and settings
    
    Args:
        text: Text to convert to speech
        voice_id: Voice ID to use
        speed: Speaking speed (0.5-2.0) 
        pitch: Voice pitch (-10 to +10)
        
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
                
        if not voice_config:
            raise ValueError(f"Voice {voice_id} not found")
        
        # Generate audio file
        output_file = os.path.join(TEMP_DIR, f"voice_{voice_id}_{uuid4()}.wav")
        
        # Use Groq TTS with the mapped voice
        groq_voice = voice_config["groq_voice"]
        result_file = generate_speech(text, output_file, groq_voice)
        
        if not result_file or not os.path.exists(result_file):
            raise Exception("Failed to generate audio file")
        
        # Calculate estimated duration (rough estimation)
        word_count = len(text.split())
        base_duration = word_count * 0.5  # ~0.5 seconds per word
        adjusted_duration = base_duration / speed  # Adjust for speed
        
        # In a real implementation, you would:
        # 1. Apply speed/pitch modifications using audio processing libraries
        # 2. Upload to cloud storage and get permanent URL
        # 3. Get actual audio duration
        
        return {
            "audio_url": f"/media/audio/{os.path.basename(result_file)}",
            "duration": adjusted_duration,
            "voice_id": voice_id,
            "settings": {
                "speed": speed,
                "pitch": pitch
            },
            "local_file": result_file  # For internal use
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
