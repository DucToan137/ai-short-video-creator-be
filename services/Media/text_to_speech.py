from groq import Groq
from config import GROQ_KEY, TEMP_DIR
import os
import asyncio
from datetime import datetime
import hashlib

# Cache for deduplication
_audio_cache = {}

def generate_speech(text, output_file="speech.wav", voice="Fritz-PlayAI"):
    """Generate speech from text using Groq API"""
    client = Groq(api_key=GROQ_KEY)
    
    model = "playai-tts"
    response_format = "wav"
    
    # Available voices from Groq API
    available_voices = [
        "Aaliyah-PlayAI", "Adelaide-PlayAI", "Angelo-PlayAI", "Arista-PlayAI",
        "Atlas-PlayAI", "Basil-PlayAI", "Briggs-PlayAI", "Calum-PlayAI",
        "Celeste-PlayAI", "Cheyenne-PlayAI", "Chip-PlayAI", "Cillian-PlayAI",
        "Deedee-PlayAI", "Eleanor-PlayAI", "Fritz-PlayAI", "Gail-PlayAI",
        "Indigo-PlayAI", "Jennifer-PlayAI", "Judy-PlayAI", "Mamaw-PlayAI",
        "Mason-PlayAI", "Mikail-PlayAI", "Mitch-PlayAI", "Nia-PlayAI",
        "Quinn-PlayAI", "Ruby-PlayAI", "Thunder-PlayAI"
    ]
    
    # Use Fritz-PlayAI as fallback if voice not in available list
    if voice not in available_voices:
        print(f"Voice '{voice}' not available. Using Fritz-PlayAI as fallback.")
        voice = "Fritz-PlayAI"
    
    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format=response_format
        )
        
        response.write_to_file(output_file)
        return output_file
    except Exception as e:
        # Final fallback to Fritz-PlayAI if anything fails
        if voice != "Fritz-PlayAI":
            print(f"Voice '{voice}' failed: {e}. Trying Fritz-PlayAI...")
            response = client.audio.speech.create(
                model=model,
                voice="Fritz-PlayAI",
                input=text,
                response_format=response_format
            )
            response.write_to_file(output_file)
            return output_file
        else:
            raise e

async def generate_speech_async(text: str, voice_id: str = "Fritz-PlayAI", user_id: str = None):
    """
    Generate speech from text using Groq API (async wrapper)
    Uploads to Cloudinary and returns media info
    """
    try:
        # Create unique output file path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(TEMP_DIR, f"speech_{timestamp}.wav")
        
        # Run the synchronous function in a thread
        def sync_generate():
            return generate_speech(text, output_file, voice_id)
        
        # Execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        audio_path = await loop.run_in_executor(None, sync_generate)
        
        # Estimate duration (rough calculation: ~150 words per minute)
        word_count = len(text.split())
        estimated_duration = max(5, (word_count / 150) * 60)  # minimum 5 seconds
        
        # Upload to Cloudinary if user_id provided
        if user_id:
            from services.Media.media_utils import upload_media
            upload_result = await upload_media(
                audio_path,
                user_id,
                folder="audio",
                resource_type="video",  # For audio files
                prompt=f"Generated speech: {text[:100]}{'...' if len(text) > 100 else ''}",
                metadata={
                    "voice_id": voice_id,
                    "duration": estimated_duration,
                    "word_count": word_count,
                    "type": "generated_speech"
                }
            )
            
            # Clean up local file after upload
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return {
                "audio_path": audio_path,  # Keep for backward compatibility
                "audio_url": upload_result["url"],  # Cloudinary URL
                "audio_id": upload_result["id"],  # Database ID
                "duration": estimated_duration,
                "voice_id": voice_id,
                "cloudinary_public_id": upload_result["public_id"]
            }
        else:
            # Fallback to local file if no user_id
            return {
                "audio_path": audio_path,
                "duration": estimated_duration,
                "voice_id": voice_id
            }
        
    except Exception as e:
        print(f"Error generating speech: {e}")
        return None