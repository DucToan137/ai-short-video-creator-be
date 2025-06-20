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

def get_prompt(script="NOT_PROVIDED"):
    return f"""
        Generate a transcript of the speech with timestamps in seconds. Given transcript without timestamps: {script}. Group words into subtitle segments (grouping by ~5 words per segment). Follow .srt format.
    """

# def transcribe_audio(audio_file, output_srt=None, language="en"):
#     """Transcribe audio to text using Groq API and optionally create SRT file"""
#     client = Groq(api_key=GROQ_KEY)
    
#     with open(audio_file, "rb") as file:
#         transcription = client.audio.transcriptions.create(
#             file=file,
#             model="distil-whisper-large-v3-en",
#             response_format="verbose_json",
#             timestamp_granularities=["word", "segment"],
#             language=language,
#             temperature=0.0
#         )
    
#     # If output_srt is provided, create SRT file
#     if output_srt and transcription.words:
#         convert_to_srt(transcription.words, output_srt)
        
#     return transcription

def transcribe_audio(audio_file, output_srt=None,script="NOT_PROVIDED", language="en"):
    """Transcribe audio to SRT format using Gemini API and optionally create SRT file"""
    client = genai.Client(api_key=GEMINI_KEY)

    myfile = client.files.upload(file=audio_file)
    prompt= get_prompt(script)

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
    with open(output_file, "w") as f:
        f.write(transcription_text)

    return output_file

# def convert_to_srt(words, output_file):
#     """Convert word-level transcription data to SRT format"""
#     if not words:
#         print("No words data provided")
#         return
        
#     # Group words into subtitle segments
#     segments = []
#     current_segment = []
#     word_count = 0
    
#     for word_data in words:
#         current_segment.append(word_data)
#         word_count += 1
        
#         if word_count == 5:  # Group by 5 words per segment
#             segments.append(current_segment)
#             current_segment = []
#             word_count = 0
            
#     # Add any remaining words
#     if current_segment:
#         segments.append(current_segment)
    
#     # Format time as HH:MM:SS,mmm
#     def format_time(seconds):
#         ms = int((seconds % 1) * 1000)
#         s = int(seconds) % 60
#         m = int(seconds / 60) % 60
#         h = int(seconds / 3600)
#         return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    
#     # Generate SRT content
#     srt_content = ""
#     for i, segment in enumerate(segments, 1):
#         if not segment:
#             continue
            
#         start_time = segment[0]['start']
#         end_time = segment[-1]['end']
#         text = " ".join(item['word'] for item in segment)
        
#         srt_entry = f"{i}\n{format_time(start_time)} --> {format_time(end_time)}\n{text}\n\n"
#         srt_content += srt_entry
    
#     # Write to file
#     with open(output_file, "w") as f:
#         f.write(srt_content)
    
#     return output_file