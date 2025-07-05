from groq import Groq
import os
from config import GROQ_KEY
from config import GEMINI_KEY
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
from IPython.display import display
import re

def get_prompt(script="NOT_PROVIDED", language="en"):
    language_instruction = {
        "en": "Transcribe the speech in English",
        "vi": "Phiên âm lời nói bằng tiếng Việt", 
        "es": "Transcribe el habla en español",
        "fr": "Transcrire la parole en français"
    }.get(language, "Transcribe the speech")
    
    return f"""
{language_instruction}. Create accurate subtitles with precise timing.

REQUIREMENTS:
1. Listen carefully to the audio and transcribe EXACTLY what is spoken
2. Create subtitles in standard SRT format
3. Each subtitle should be 3-8 words maximum for readability
4. Timing must be PRECISE - start and end times should match exactly when words are spoken
5. Use format: HH:MM:SS,mmm (hours:minutes:seconds,milliseconds)
6. Number each subtitle sequentially

GIVEN REFERENCE TEXT (if provided): {script}
- Use this as a guide but transcribe what you actually hear
- If the spoken audio differs from the reference, transcribe the audio
- Maintain accurate timing regardless of reference text

OUTPUT FORMAT:
```srt
1
00:00:00,000 --> 00:00:03,500
First subtitle text here

2
00:00:03,500 --> 00:00:07,200
Second subtitle text here
```

Focus on:
- ACCURATE timing that matches speech
- Natural subtitle breaks at sentence/phrase boundaries
- Readable subtitle length (not too long)
- Precise millisecond timing
    """

def transcribe_audio(audio_file, output_srt=None, script="NOT_PROVIDED", language="en"):
    """Transcribe audio to SRT format using Gemini API and optionally create SRT file"""
    client = genai.Client(api_key=GEMINI_KEY)

    myfile = client.files.upload(file=audio_file)
    prompt = get_prompt(script, language)

    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=[prompt, myfile]
    )

    # Dùng regex để trích nội dung JSON từ giữa các dấu ```
    match = re.search(r"```srt\s*(.*?)\s*```", response.text, re.DOTALL)
    if match:
        processed_text = match.group(1).strip()
    else:
        raise ValueError("Không tìm thấy nội dung .srt trong phản hồi.")  

    # If output_srt is provided, create SRT file
    if output_srt and processed_text:
        convert_to_srt(processed_text, output_srt)

    return processed_text

def convert_to_srt(transcription_text, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(transcription_text)

    return output_file