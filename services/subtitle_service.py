from typing import List, Dict, Optional
import os
import json
import re
import subprocess
from uuid import uuid4
from services.Media.speech_to_text import transcribe_audio, convert_to_srt
from services.Media.media_utils import validate_srt_file, fix_srt_format, ffmpeg_path
from config import TEMP_DIR

# Predefined subtitle styles
SUBTITLE_STYLES = {
    "default": {
        "font_family": "Arial",
        "font_size": 16,
        "font_color": "#FFFFFF",
        "background_color": "#000000",
        "background_opacity": 0.7,
        "position": "bottom",
        "outline": True,
        "outline_color": "#000000"
    },
    "modern": {
        "font_family": "Helvetica",
        "font_size": 18,
        "font_color": "#FFFFFF",
        "background_color": "#1F2937",
        "background_opacity": 0.8,
        "position": "bottom",
        "outline": True,
        "outline_color": "#374151"
    },
    "minimal": {
        "font_family": "Arial",
        "font_size": 14,
        "font_color": "#FFFFFF",
        "background_color": "transparent",
        "background_opacity": 0.7,
        "position": "bottom",
        "outline": True,
        "outline_color": "#000000"
    },
    "bold": {
        "font_family": "Arial Black",
        "font_size": 20,
        "font_color": "#FFFF00",
        "background_color": "#000000",
        "background_opacity": 0.9,
        "position": "bottom",
        "outline": True,
        "outline_color": "#FF0000"
    },
    "elegant": {
        "font_family": "Times New Roman",
        "font_size": 16,
        "font_color": "#F8F9FA",
        "background_color": "#2C3E50",
        "background_opacity": 0.75,
        "position": "bottom",
        "outline": False,
        "outline_color": "#000000"
    },
    "gaming": {
        "font_family": "Arial Black",
        "font_size": 18,
        "font_color": "#00FF00",
        "background_color": "#000000",
        "background_opacity": 0.8,
        "position": "bottom",
        "outline": True,
        "outline_color": "#003300"
    },
    "cinematic": {
        "font_family": "Georgia",
        "font_size": 16,
        "font_color": "#FFD700",
        "background_color": "#1A1A1A",
        "background_opacity": 0.9,
        "position": "bottom",
        "outline": True,
        "outline_color": "#333333"
    },
    "neon": {
        "font_family": "Arial",
        "font_size": 17,
        "font_color": "#00FFFF",
        "background_color": "#000033",
        "background_opacity": 0.7,
        "position": "bottom",
        "outline": True,
        "outline_color": "#0066CC"
    }
}


def generate_subtitles_from_script(script_text: str, language: str = "en", max_words_per_segment: int = 5, estimated_duration: float = 30.0) -> Dict:
    """
    Generate subtitles from script text with estimated timing
    
    Args:
        script_text: Script text to create subtitles from
        language: Language code
        max_words_per_segment: Maximum words per subtitle segment
        estimated_duration: Estimated total duration in seconds
        
    Returns:
        Dictionary containing subtitle data
    """
    try:
        # Generate unique ID for this subtitle
        subtitle_id = f"sub_script_{uuid4().hex[:8]}"
        
        # Split script into words
        words = script_text.split()
        if not words:
            raise Exception("Empty script text")
        
        # Create segments with estimated timing
        segments = []
        segment_id = 1
        total_words = len(words)
        
        # Calculate timing per word
        words_per_second = total_words / estimated_duration
        
        for i in range(0, total_words, max_words_per_segment):
            # Get words for this segment
            segment_words = words[i:i + max_words_per_segment]
            segment_text = " ".join(segment_words)
            
            # Calculate timing
            start_time = i / words_per_second
            end_time = min((i + len(segment_words)) / words_per_second, estimated_duration)
            
            # Ensure minimum segment duration
            if end_time - start_time < 1.0:
                end_time = start_time + 1.0
            
            segments.append({
                "id": segment_id,
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "text": segment_text.strip()
            })
            
            segment_id += 1
        
        # Create SRT content
        srt_content = ""
        for seg in segments:
            start_formatted = format_time_for_srt(seg["start_time"])
            end_formatted = format_time_for_srt(seg["end_time"])
            srt_content += f"{seg['id']}\n{start_formatted} --> {end_formatted}\n{seg['text']}\n\n"
        
        # Save SRT file
        srt_file = os.path.join(TEMP_DIR, f"{subtitle_id}.srt")
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write(srt_content)
        
        return {
            "id": subtitle_id,
            "segments": segments,
            "language": language,
            "srt_url": f"/media/subtitles/{subtitle_id}.srt",
            "srt_file_path": srt_file,
            "total_duration": estimated_duration,
            "source": "script"
        }
        
    except Exception as e:
        raise Exception(f"Failed to generate subtitles from script: {str(e)}")

def format_time_for_srt(seconds: float) -> str:
    """Format time in seconds to SRT format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

SUPPORTED_LANGUAGES = ["en", "vi", "es", "fr", "de", "ja", "ko", "zh"]

def generate_subtitles_from_audio(audio_file_path: str, language: str = "auto", max_words_per_segment: int = 5) -> Dict:
    """
    Generate subtitles from audio file with automatic language detection
    
    Args:
        audio_file_path: Path to audio file
        language: Audio language code or "auto" for auto-detection
        max_words_per_segment: Maximum words per subtitle segment (unused, kept for compatibility)
        
    Returns:
        Dictionary containing subtitle data
    """
    try:
        # Generate unique ID for this subtitle
        subtitle_id = f"sub_{uuid4().hex[:8]}"
        
        # Create SRT file path
        srt_file = os.path.join(TEMP_DIR, f"{subtitle_id}.srt")
        
        # Auto-detect language if specified
        actual_language = language
        if language == "auto":
            print("🌐 Auto-detecting language from audio...")
            # Let the transcription service handle auto-detection
            actual_language = None  # Pass None to enable auto-detection
        
        # Transcribe audio and generate SRT
        transcription_text = transcribe_audio(audio_file_path, srt_file, actual_language)
        
        if not transcription_text or not os.path.exists(srt_file):
            raise Exception("No transcription data received or SRT file not created")
        
        # Get actual audio duration for validation
        try:
            from services.Media.media_utils import get_audio_duration
            actual_audio_duration = get_audio_duration(audio_file_path)
            print(f"🎵 Actual audio duration: {actual_audio_duration:.2f}s")
        except Exception:
            actual_audio_duration = 30  # Default fallback
        
        # Parse and validate SRT file
        segments = parse_srt_file(srt_file)
        
        if segments:
            # Validate and correct timing
            segments = validate_and_correct_timing(segments, actual_audio_duration)
            
            # Re-write corrected SRT file
            corrected_srt_content = generate_srt_from_segments(segments)
            with open(srt_file, "w", encoding="utf-8") as f:
                f.write(corrected_srt_content)
            print(f"✅ SRT timing corrected and saved: {srt_file}")
            
            total_duration = max(segment['end_time'] for segment in segments)
        else:
            print("⚠️ No valid segments found in SRT")
            total_duration = actual_audio_duration
        
        return {
            "id": subtitle_id,
            "segments": segments,
            "language": language,
            "srt_url": f"/media/subtitles/{subtitle_id}.srt",
            "srt_file_path": srt_file,
            "total_duration": total_duration
        }
        
    except Exception as e:
        raise Exception(f"Failed to generate subtitles: {str(e)}")

def parse_srt_file(srt_file_path: str) -> List[Dict]:
    """
    Parse SRT file and return segments
    
    Args:
        srt_file_path: Path to SRT file
        
    Returns:
        List of subtitle segments
    """
    segments = []
    
    try:
        with open(srt_file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Split by double newlines to get individual subtitle blocks
        blocks = content.split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # Parse segment ID
                segment_id = int(lines[0])
                
                # Parse timestamp line
                timestamp_line = lines[1]
                start_str, end_str = timestamp_line.split(' --> ')
                
                start_time = parse_timestamp(start_str)
                end_time = parse_timestamp(end_str)
                
                # Parse text (can be multiple lines)
                text = '\n'.join(lines[2:])
                
                segments.append({
                    "id": segment_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": text
                })
    
    except Exception as e:
        print(f"Error parsing SRT file: {e}")
        return []
    
    return segments

def parse_timestamp(timestamp_str: str) -> float:
    """
    Parse SRT timestamp to seconds
    
    Args:
        timestamp_str: Timestamp in format HH:MM:SS,mmm
        
    Returns:
        Time in seconds
    """
    try:
        time_part, ms_part = timestamp_str.split(',')
        h, m, s = map(int, time_part.split(':'))
        ms = int(ms_part)
        
        return h * 3600 + m * 60 + s + ms / 1000
    except:
        return 0.0

def update_subtitle_segments(subtitle_id: str, segments: List[Dict]) -> Dict:
    """
    Update subtitle segments
    
    Args:
        subtitle_id: Subtitle ID
        segments: Updated segments
        
    Returns:
        Updated subtitle data
    """
    try:
        # Generate new SRT file
        srt_file = os.path.join(TEMP_DIR, f"{subtitle_id}.srt")
        
        srt_content = ""
        for segment in segments:
            start_time = format_timestamp(segment["start_time"])
            end_time = format_timestamp(segment["end_time"])
            
            srt_content += f"{segment['id']}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{segment['text']}\n\n"
        
        # Write updated SRT file
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        # Calculate total duration
        total_duration = max(seg["end_time"] for seg in segments) if segments else 0
        
        return {
            "id": subtitle_id,
            "segments": segments,
            "srt_url": f"/media/subtitles/{subtitle_id}.srt",
            "srt_file_path": srt_file,
            "total_duration": total_duration
        }
        
    except Exception as e:
        raise Exception(f"Failed to update subtitles: {str(e)}")

def format_timestamp(seconds: float) -> str:
    """
    Format seconds to SRT timestamp format
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp HH:MM:SS,mmm
    """
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = int(seconds / 60) % 60
    h = int(seconds / 3600)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def apply_subtitles_to_video(video_file_path: str, subtitle_id: str, style: Dict = None) -> str:
    """
    Apply subtitles to video with styling
    
    Args:
        video_file_path: Path to video file
        subtitle_id: Subtitle ID
        style: Subtitle styling options
        
    Returns:
        Path to video with subtitles
    """
    try:
        # Get subtitle file
        srt_file = os.path.join(TEMP_DIR, f"{subtitle_id}.srt")
        
        if not os.path.exists(srt_file):
            raise Exception(f"Subtitle file not found: {srt_file}")
        
        # Apply default style if none provided
        if not style:
            style = SUBTITLE_STYLES["default"]
        
        # Generate output path
        output_path = os.path.join(TEMP_DIR, f"subtitled_{uuid4().hex[:8]}.mp4")
        
        # Apply subtitles using existing function
        result_path = add_subtitles(video_file_path, srt_file, output_path)
        
        return result_path
        
    except Exception as e:
        raise Exception(f"Failed to apply subtitles: {str(e)}")
    
    
def convert_hex_to_ass(hex_color: str) -> str:
    """Convert hex color to ASS format (BGR)"""
    if not hex_color.startswith('#'):
        hex_color = '#' + hex_color
    # Remove '#' and convert to BGR format for ASS
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"&H{b:02x}{g:02x}{r:02x}"
    
def get_ffmpeg_subtitle_style(style_input="default") -> str:
    """
    Convert subtitle style to FFmpeg subtitle filter parameters
    
    Args:
        style_input: Style name (string) or SubtitleStyle object
        
    Returns:
        FFmpeg force_style parameter string
    """
    print(f"🎨 Processing style input: {type(style_input)} - {style_input}")
    
    # Handle both string style name and SubtitleStyle object
    if isinstance(style_input, str):
        # String style name - lookup in predefined styles
        style_name = style_input
        if style_name not in SUBTITLE_STYLES:
            print(f"⚠️ Unknown subtitle style '{style_name}', using 'default'")
            style_name = "default"
        style = SUBTITLE_STYLES[style_name]
        print(f"🎨 Using predefined style: {style_name}")
    elif hasattr(style_input, 'fontFamily') or hasattr(style_input, 'font_family'):
        # SubtitleStyle object from frontend
        style = {
            "font_family": getattr(style_input, 'fontFamily', getattr(style_input, 'font_family', 'Arial')),
            "font_size": getattr(style_input, 'fontSize', getattr(style_input, 'font_size', 16)),
            "font_color": getattr(style_input, 'fontColor', getattr(style_input, 'font_color', '#FFFFFF')),
            "background_color": getattr(style_input, 'backgroundColor', getattr(style_input, 'background_color', '#000000')),
            "background_opacity": getattr(style_input, 'backgroundOpacity', getattr(style_input, 'background_opacity', 0.7)),
            "position": getattr(style_input, 'position', 'bottom'),
            "outline": getattr(style_input, 'outline', True),
            "outline_color": getattr(style_input, 'outlineColor', getattr(style_input, 'outline_color', '#000000'))
        }
        print(f"🎨 Using custom style object: {getattr(style_input, 'name', 'custom')}")
    elif isinstance(style_input, dict):
        # Dictionary style object
        style = {
            "font_family": style_input.get('fontFamily', style_input.get('font_family', 'Arial')),
            "font_size": style_input.get('fontSize', style_input.get('font_size', 16)),
            "font_color": style_input.get('fontColor', style_input.get('font_color', '#FFFFFF')),
            "background_color": style_input.get('backgroundColor', style_input.get('background_color', '#000000')),
            "background_opacity": style_input.get('backgroundOpacity', style_input.get('background_opacity', 0.7)),
            "position": style_input.get('position', 'bottom'),
            "outline": style_input.get('outline', True),
            "outline_color": style_input.get('outlineColor', style_input.get('outline_color', '#000000'))
        }
        print(f"🎨 Using dictionary style: {style_input.get('name', 'custom')}")
    else:
        print(f"⚠️ Invalid style input type: {type(style_input)}, using 'default'")
        style = SUBTITLE_STYLES["default"]
    
    print(f"📝 Final style config: {style}")
    
    # Convert hex colors to ASS format (BGR)
    primary_color = convert_hex_to_ass(style["font_color"])
    back_color = convert_hex_to_ass(style["background_color"])
    outline_color = convert_hex_to_ass(style["outline_color"])
    
    # Calculate background alpha (0-255, where 0 is fully opaque, 255 is fully transparent)
    bg_alpha = int((1.0 - style["background_opacity"]) * 255)
    
    # Build force_style string
    force_style_parts = [
        f"FontName={style['font_family']}",
        f"FontSize={style['font_size']}",
        f"PrimaryColour={primary_color}",
        f"BackColour={back_color}",
        f"BackgroundAlpha=&H{bg_alpha:02x}",
    ]
    
    # Add outline if enabled
    if style["outline"]:
        force_style_parts.extend([
            "OutlineColour=" + outline_color,
            "Outline=1"
        ])
    else:
        force_style_parts.append("Outline=0")
    
    # Position mapping
    alignment_map = {
        "top": "8",      # Top center
        "middle": "5",   # Middle center
        "bottom": "2"    # Bottom center
    }
    alignment = alignment_map.get(style["position"], "2")
    force_style_parts.append(f"Alignment={alignment}")
    
    force_style_string = ",".join(force_style_parts)
    print(f"🎨 Generated FFmpeg style: {force_style_string}")
    
    return force_style_string


def add_subtitles(video_path, subtitle_path, output_path=None, subtitle_style="default"):
    """Add subtitles to a video using FFmpeg with improved error handling and custom styling"""
    if not output_path:
        output_path = os.path.join(TEMP_DIR, f"sub_{os.path.basename(video_path)}")
    
    print(f"🎬 Adding subtitles:")
    print(f"   Video: {video_path} (exists: {os.path.exists(video_path)})")
    print(f"   Subtitles: {subtitle_path} (exists: {os.path.exists(subtitle_path)})")
    print(f"   Output: {output_path}")
    print(f"   Style: {subtitle_style}")
    
    # Validate inputs
    if not os.path.exists(video_path):
        raise Exception(f"Video file not found: {video_path}")
    if not os.path.exists(subtitle_path):
        raise Exception(f"Subtitle file not found: {subtitle_path}")
    
    try:
        # Check if FFmpeg is available
        if not os.path.exists(ffmpeg_path):
            raise Exception(f"FFmpeg not found at: {ffmpeg_path}")
        
        # Convert paths to absolute paths with forward slashes for FFmpeg
        video_path_abs = video_path.replace('\\', '/')
        subtitle_path_abs = subtitle_path.replace('\\', '/')
        output_path_abs = output_path.replace('\\', '/')
        
        # Validate subtitle file format
        if not validate_srt_file(subtitle_path):
            print("⚠️  Invalid SRT format, attempting to fix...")
            fixed_srt_path = fix_srt_format(subtitle_path)
            if fixed_srt_path:
                subtitle_path_abs = os.path.abspath(fixed_srt_path).replace('\\', '/')
            else:
                raise Exception("Could not fix SRT format")
        
        # Get FFmpeg style string for the selected style
        ffmpeg_style = get_ffmpeg_subtitle_style(subtitle_style)
        
        # Build FFmpeg command with custom subtitle styling
        command = [
            ffmpeg_path,
            "-i", video_path_abs,  # Input video
            "-vf", f"subtitles='{subtitle_path_abs}':force_style='{ffmpeg_style}'",  # Subtitle filter with custom styling
            "-c:a", "copy",  # Copy audio without re-encoding
            "-c:v", "libx264",  # Re-encode video for subtitle embedding
            "-preset", "fast",  # Fast encoding preset
            "-crf", "23",  # Good quality
            "-y",  # Overwrite output file if it exists
            output_path_abs  # Output video
        ]

        print(f"🔧 FFmpeg command: {' '.join(command)}")
        
        # Run with timeout and better error capture
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True, 
            timeout=300,  # 5 minute timeout
            encoding='utf-8',  # Force UTF-8 encoding
            errors='replace'  # Replace problematic characters
        )
        
        # Verify output file was created and has reasonable size
        if os.path.exists(output_path):
            output_size = os.path.getsize(output_path)
            if output_size > 1000:  # At least 1KB
                print(f"✅ Subtitles added successfully: {output_path}")
                print(f"   Output size: {output_size:,} bytes ({output_size/1024/1024:.2f} MB)")
                return output_path
            else:
                raise Exception(f"Output file too small: {output_size} bytes")
        else:
            raise Exception("Output file was not created")
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg timeout - subtitle processing took too long")
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e}")
        if e.stderr:
            print(f"   FFmpeg stderr: {e.stderr}")
        if e.stdout:
            print(f"   FFmpeg stdout: {e.stdout}")
        
        # Try alternative method with simpler subtitle embedding
        print("🔄 Trying alternative subtitle method...")
        return add_subtitles_alternative(video_path, subtitle_path, output_path, subtitle_style)
        
    except Exception as e:
        print(f"❌ Error adding subtitles: {e}")
        return None

def add_subtitles_alternative(video_path, subtitle_path, output_path, subtitle_style="default"):
    """Alternative subtitle method using different FFmpeg approach"""
    try:
        video_path_abs = os.path.abspath(video_path).replace('\\', '/')
        subtitle_path_abs = os.path.abspath(subtitle_path).replace('\\', '/')
        output_path_abs = os.path.abspath(output_path).replace('\\', '/')
        
        # Get style string (simpler version for fallback)
        ffmpeg_style = get_ffmpeg_subtitle_style(subtitle_style)
        
        # Simpler command with styling
        command = [
            ffmpeg_path,
            "-i", video_path_abs,
            "-vf", f"subtitles={subtitle_path_abs}:force_style='{ffmpeg_style}'",  # Include styling in fallback
            "-c:a", "copy",
            "-y",
            output_path_abs
        ]
        
        print(f"🔄 Alternative command: {' '.join(command)}")
        
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True, 
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f"✅ Alternative subtitle method successful: {output_path}")
            return output_path
        else:
            print("❌ Alternative method also failed")
            return None
            
    except Exception as e:
        print(f"❌ Alternative subtitle method failed: {e}")
        return None

def get_available_subtitle_styles() -> List[Dict]:
    """Get list of available subtitle styles"""
    return [
        {"name": name, **style} 
        for name, style in SUBTITLE_STYLES.items()
    ]

def get_supported_languages() -> List[str]:
    """Get list of supported languages"""
    return SUPPORTED_LANGUAGES

def delete_subtitle_files(subtitle_id: str):
    """Delete subtitle files"""
    try:
        srt_file = os.path.join(TEMP_DIR, f"{subtitle_id}.srt")
        if os.path.exists(srt_file):
            os.remove(srt_file)
    except Exception as e:
        print(f"Error deleting subtitle files: {e}")

def generate_subtitle_preview(segments: List[Dict], style: Dict = None) -> str:
    """
    Generate a preview of how subtitles will look
    
    Args:
        segments: Subtitle segments
        style: Styling options
        
    Returns:
        HTML preview content
    """
    if not style:
        style = SUBTITLE_STYLES["default"]
    
    preview_html = f"""
    <div style="
        background-color: {style['background_color']};
        opacity: {style['background_opacity']};
        color: {style['font_color']};
        font-family: {style['font_family']};
        font-size: {style['font_size']}px;
        padding: 8px 16px;
        border-radius: 4px;
        text-align: center;
        {'text-shadow: 1px 1px 2px ' + style['outline_color'] + ';' if style.get('outline') else ''}
    ">
        {segments[0]['text'] if segments else 'Sample subtitle text'}
    </div>
    """
    
    return preview_html

def generate_srt_content(text: str, duration: float, words_per_segment: int = 8) -> str:
    """
    Generate SRT subtitle content from text with estimated timing
    
    Args:
        text: The text to convert to subtitles
        duration: Total duration of the audio/video in seconds
        words_per_segment: Number of words per subtitle segment
        
    Returns:
        SRT formatted subtitle content
    """
    # Clean and split text into words
    words = re.findall(r'\S+', text)
    total_words = len(words)
    
    if total_words == 0:
        return ""
    
    # Calculate timing per word
    time_per_word = duration / total_words
    
    # Group words into segments
    segments = []
    for i in range(0, total_words, words_per_segment):
        segment_words = words[i:i + words_per_segment]
        start_time = i * time_per_word
        end_time = min((i + len(segment_words)) * time_per_word, duration)
        
        segments.append({
            "text": " ".join(segment_words),
            "start": start_time,
            "end": end_time
        })
    
    # Generate SRT content
    srt_content = ""
    for i, segment in enumerate(segments, 1):
        start_time_str = format_srt_time(segment["start"])
        end_time_str = format_srt_time(segment["end"])
        
        srt_content += f"{i}\n"
        srt_content += f"{start_time_str} --> {end_time_str}\n"
        srt_content += f"{segment['text']}\n\n"
    
    return srt_content

def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def validate_and_correct_timing(segments, actual_audio_duration):
    """
    Validate and correct subtitle timing to ensure it matches audio duration
    
    Args:
        segments: List of subtitle segments with timing
        actual_audio_duration: Actual duration of audio file
        
    Returns:
        Corrected list of segments
    """
    if not segments:
        return segments
    
    print(f"📊 Validating timing for {len(segments)} segments")
    print(f"   Audio duration: {actual_audio_duration:.2f}s")
    
    # Check if timing is reasonable
    last_end_time = max(segment['end_time'] for segment in segments)
    print(f"   Last subtitle ends at: {last_end_time:.2f}s")
    
    # If subtitles extend way beyond audio, scale them down
    if last_end_time > actual_audio_duration * 1.1:  # 10% tolerance
        print(f"⚠️  Subtitles extend beyond audio, scaling down...")
        scale_factor = actual_audio_duration / last_end_time
        print(f"   Scale factor: {scale_factor:.3f}")
        
        for segment in segments:
            segment['start_time'] *= scale_factor
            segment['end_time'] *= scale_factor
        
        print(f"✅ Timing scaled to match audio duration")
    
    # Ensure no overlapping and minimum gaps
    corrected_segments = []
    for i, segment in enumerate(segments):
        corrected_segment = segment.copy()
        
        # Ensure minimum duration
        min_duration = 0.5  # 500ms minimum
        duration = segment['end_time'] - segment['start_time']
        if duration < min_duration:
            corrected_segment['end_time'] = segment['start_time'] + min_duration
        
        # Ensure no overlap with next segment
        if i < len(segments) - 1:
            next_start = segments[i + 1]['start_time']
            if corrected_segment['end_time'] > next_start - 0.1:  # 100ms gap
                corrected_segment['end_time'] = next_start - 0.1
        
        # Ensure doesn't exceed audio duration
        if corrected_segment['end_time'] > actual_audio_duration:
            corrected_segment['end_time'] = actual_audio_duration
        
        # Final validation
        if corrected_segment['start_time'] < corrected_segment['end_time']:
            corrected_segments.append(corrected_segment)
        else:
            print(f"⚠️  Skipping invalid segment {i+1}: start >= end")
    
    print(f"✅ Validated {len(corrected_segments)}/{len(segments)} segments")
    return corrected_segments

def generate_srt_from_segments(segments):
    """
    Generate SRT content from segments
    
    Args:
        segments: List of segments with timing and text
        
    Returns:
        SRT formatted string
    """
    srt_content = ""
    
    for i, segment in enumerate(segments, 1):
        start_time_str = format_srt_time(segment['start_time'])
        end_time_str = format_srt_time(segment['end_time'])
        
        srt_content += f"{i}\n"
        srt_content += f"{start_time_str} --> {end_time_str}\n"
        srt_content += f"{segment['text']}\n\n"
    
    return srt_content
