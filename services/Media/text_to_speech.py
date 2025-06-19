from groq import Groq
from config import GROQ_KEY, TEMP_DIR
import os
import asyncio
from datetime import datetime

def generate_speech(text, output_file="speech.wav", voice="Fritz-PlayAI"):
    """Generate speech from text using Groq API"""
    client = Groq(api_key=GROQ_KEY)
    
    model = "playai-tts"
    response_format = "wav"
    
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format=response_format
    )
    
    response.write_to_file(output_file)
    return output_file

async def generate_speech_async(text: str, voice_id: str = "Fritz-PlayAI"):
    """
    Generate speech from text using Groq API (async wrapper)
    Returns a dictionary with audio_path and duration
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
        
        return {
            "audio_path": audio_path,
            "duration": estimated_duration,
            "voice_id": voice_id
        }
        
    except Exception as e:
        print(f"Error generating speech: {e}")
        return None