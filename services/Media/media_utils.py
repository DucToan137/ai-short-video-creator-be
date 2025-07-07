import subprocess
import imageio_ffmpeg
import os
import tempfile
from config import TEMP_DIR
import cloudinary
import cloudinary.uploader
from datetime import datetime
from typing import Optional, Dict
from config import media_collection
from models.media import MediaModel, MediaType
from bson import ObjectId
from io import BytesIO
import httpx

media_colt = media_collection()
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
async def upload_media(file_path: str, user_id: str, folder: str = "media", resource_type: str = "auto", 
                 prompt: str = None, metadata: Dict = None, quality: str = "high", title: str = None) -> Dict:
    """
    Upload media to Cloudinary and save metadata to MongoDB
    
    Args:
        file_path: Path to local file
        user_id: ID of the user uploading the media
        folder: Cloudinary folder
        resource_type: auto, image, video, raw
        prompt: Media prompt
        metadata: Additional metadata
        
    Returns:
        Dictionary with upload result and database ID
    """
    # Get filename for the prompt if not provided
    if not prompt:
        prompt = os.path.basename(file_path)
    
    # Upload to Cloudinary with high quality settings
    try:
        upload_options = {
            "folder": folder,
            "resource_type": resource_type,
            "unique_filename": True
        }
        
        # For video uploads, use quality-based settings
        if resource_type == "video":
            # Quality-based settings for Cloudinary
            quality_settings = {
                "high": {
                    "quality": "auto:best",
                    "bit_rate": "2m",
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "audio_frequency": 44100
                },
                "medium": {
                    "quality": "auto:good",
                    "bit_rate": "1m",
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "audio_frequency": 44100
                },
                "low": {
                    "quality": "auto:low",
                    "bit_rate": "500k",
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "audio_frequency": 22050
                }
            }
            
            selected_quality = quality_settings.get(quality, quality_settings["high"])
            
            upload_options.update({
                **selected_quality,
                "eager": [
                    {
                        "format": "mp4",
                        **selected_quality
                    }
                ],
                "eager_async": False  # Wait for processing to complete
            })
            
            print(f"Using {quality} quality settings for video upload: {selected_quality}")
        
        upload_result = cloudinary.uploader.upload(
            file_path,
            **upload_options
        )
        print(f"Uploaded {file_path} to Cloudinary with high quality settings")
    except Exception as e:
        raise Exception(f"Failed to upload media to Cloudinary: {str(e)}")

    # Determine media type
    media_type = MediaType.TEXT
    if resource_type == "image" or (resource_type == "auto" and upload_result.get("resource_type") == "image"):
        media_type = MediaType.IMAGE
    elif resource_type == "video" or (resource_type == "auto" and upload_result.get("resource_type") == "video"):
        media_type = MediaType.VIDEO
    elif upload_result.get("format") in ["mp3", "wav", "ogg"]:
        media_type = MediaType.AUDIO
    
    # Convert user_id to ObjectId for MongoDB storage
    try:
        # Handle special system users
        if user_id in ["system", "preview_user", "anonymous"]:
            # Generate a special ObjectId for system users, or use a fixed ObjectId
            # Using a fixed ObjectId for "system" to avoid duplicates
            system_user_ids = {
                "system": "000000000000000000000001",
                "preview_user": "000000000000000000000002", 
                "anonymous": "000000000000000000000003"
            }
            user_id_obj = ObjectId(system_user_ids.get(user_id, "000000000000000000000001"))
            print(f"🔧 Using special ObjectId for {user_id}: {user_id_obj}")
        elif isinstance(user_id, str):
            user_id_obj = ObjectId(user_id)
        else:
            user_id_obj = user_id
    except Exception as e:
        # If conversion fails, create a default system ObjectId
        print(f"⚠️ Failed to convert user_id '{user_id}' to ObjectId: {e}")
        user_id_obj = ObjectId("000000000000000000000001")  # Default system user
        print(f"🔧 Using default system ObjectId: {user_id_obj}")
    
    # Create media document
    media_doc = MediaModel(
        user_id=str(user_id_obj),  # Store as string in Pydantic model
        title=title or upload_result.get("original_filename", "Untitled"),
        content=prompt,
        media_type=media_type,
        url=upload_result["secure_url"],
        public_id=upload_result["public_id"],
        metadata=metadata or {},
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Insert into MongoDB
    if not media_collection:
        raise Exception("Media collection is not initialized")
    try:
        media_dict = media_doc.model_dump(by_alias=True, exclude_unset=True)
        # Remove _id field completely to let MongoDB generate it
        media_dict.pop("_id", None)
        
        # Convert user_id back to ObjectId for MongoDB storage
        media_dict["user_id"] = user_id_obj
        
        result = await media_collection().insert_one(media_dict)
        print(f"Inserted media document into MongoDB with ID {result.inserted_id}")
    except Exception as e:
        raise Exception(f"Failed to insert media into MongoDB: {str(e)}")

    return {
        "id": str(result.inserted_id),
        "public_id": upload_result["public_id"],
        "url": upload_result["secure_url"],
        "media_type": media_type
    }

async def get_media_by_id(media_id: str) -> Optional[Dict]:
    """Get media by ID"""
    try:
        # Try to convert to ObjectId, if fails, use as string (for custom IDs)
        try:
            query_id = ObjectId(media_id)
            media = await media_collection().find_one({"_id": query_id})
        except:
            # If not a valid ObjectId, try searching by custom ID or string ID
            media = await media_collection().find_one({"id": media_id})
        
        if media:
            media["id"] = str(media.get("_id", media.get("id", media_id)))
            if "user_id" in media and media["user_id"]:
                media["user_id"] = str(media["user_id"])
            if "_id" in media:
                del media["_id"]
        return media
    except Exception as e:
        print(f"Error getting media: {e}")
        return None

async def get_media_by_user(user_id: str, page: int = 1, size: int = 10, media_type: Optional[MediaType] = None) -> Dict:
    """Get media by user ID with pagination and optional filtering"""
    try:
        skip = (page - 1) * size
        
        # Build query filter - try both ObjectId and string format
        try:
            user_id_obj = ObjectId(user_id)
            # Query for both ObjectId and string format of user_id
            user_query = {
                "$or": [
                    {"user_id": user_id_obj},
                    {"user_id": user_id}
                ]
            }
        except:
            # If user_id is not a valid ObjectId, only query by string
            user_query = {"user_id": user_id}
            
        query_filter = user_query
        if media_type:
            query_filter = {
                "$and": [
                    user_query,
                    {"media_type": media_type.value}
                ]
            }
        
        # Get total count
        total = await media_collection().count_documents(query_filter)
        
        # Get media with pagination
        cursor = media_collection().find(query_filter).skip(skip).limit(size).sort("created_at", -1)
        media_list = []
        
        async for media in cursor:
            media["id"] = str(media["_id"])
            media["user_id"] = str(media["user_id"])
            del media["_id"]
            media_list.append(media)
            
        return {
            "media": media_list,
            "total": total,
            "page": page,
            "size": size
        }
    except Exception as e:
        print(f"Error getting user media: {e}")
        return {"media": [], "total": 0, "page": page, "size": size}

async def update_media(media_id: str, user_id: str, update_data: Dict) -> Optional[Dict]:
    """Update media metadata"""
    try:
        # Add updated timestamp
        update_data["updated_at"] = datetime.now()
        
        # Try both ObjectId and string format for user_id
        try:
            user_id_obj = ObjectId(user_id)
            query_filter = {
                "_id": ObjectId(media_id),
                "$or": [
                    {"user_id": user_id_obj},
                    {"user_id": user_id}
                ]
            }
        except:
            query_filter = {"_id": ObjectId(media_id), "user_id": user_id}
        
        result = await media_collection().update_one(
            query_filter,
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await get_media_by_id(media_id)
        return None
    except Exception as e:
        print(f"Error updating media: {e}")
        return None

async def delete_media(media_id: str, user_id: str) -> bool:
    """Delete media from Cloudinary and MongoDB"""
    try:
        # Try both ObjectId and string format for user_id
        try:
            user_id_obj = ObjectId(user_id)
            query_filter = {
                "_id": ObjectId(media_id),
                "$or": [
                    {"user_id": user_id_obj},
                    {"user_id": user_id}
                ]
            }
        except:
            query_filter = {"_id": ObjectId(media_id), "user_id": user_id}
        
        # Get media to get public_id
        media = await media_collection().find_one(query_filter)
        if not media:
            return False
            
        # Delete from Cloudinary
        cloudinary.uploader.destroy(media["public_id"])
        
        # Delete from MongoDB
        result = await media_collection().delete_one(query_filter)
        
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting media: {e}")
        return False

def create_video(image_path, audio_path, output_path=None):
    """Create a video from an image and audio using FFmpeg"""
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    if not output_path:
        output_path = os.path.join(TEMP_DIR, f"{os.path.splitext(os.path.basename(image_path))[0]}.mp4")
    
    print(f"Creating video with:")
    print(f"  Image: {image_path} (exists: {os.path.exists(image_path)})")
    print(f"  Audio: {audio_path} (exists: {os.path.exists(audio_path)})")
    print(f"  Output: {output_path}")
    
    try:
        command = [
            ffmpeg_path,
            "-loop", "1",  # Loop the image
            "-i", image_path,  # Input image
            "-i", audio_path,  # Input audio
            "-c:v", "libx264",  # Video codec
            "-tune", "stillimage",  # Optimize for still images
            "-c:a", "aac",  # Audio codec
            "-b:a", "192k",  # Audio bitrate
            "-pix_fmt", "yuv420p",  # Pixel format
            "-shortest",  # Match video duration to audio
            "-y",  # Overwrite output file if it exists
            output_path  # Output file
        ]

        print(f"FFmpeg command: {' '.join(command)}")
        subprocess.run(command, check=True)
        print(f"Video created successfully: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error creating video: {e}")
        return None

def validate_srt_file(srt_path):
    """Validate SRT file format"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Basic SRT validation
        if not content:
            return False
        
        # Check for basic SRT structure
        lines = content.split('\n')
        has_numbers = False
        has_timestamps = False
        
        for line in lines:
            line = line.strip()
            if line.isdigit():
                has_numbers = True
            elif '-->' in line:
                has_timestamps = True
                
        return has_numbers and has_timestamps
        
    except Exception as e:
        print(f"SRT validation error: {e}")
        return False

def fix_srt_format(srt_path):
    """Attempt to fix common SRT format issues"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix common issues
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Fix timestamp format (ensure comma instead of period)
                if '-->' in line:
                    line = line.replace('.', ',')
                fixed_lines.append(line)
        
        # Write fixed version
        fixed_path = srt_path.replace('.srt', '_fixed.srt')
        with open(fixed_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fixed_lines) + '\n')
        
        print(f"✅ Fixed SRT saved to: {fixed_path}")
        return fixed_path
        
    except Exception as e:
        print(f"SRT fix error: {e}")
        return None

def upload_video_to_cloud(video_path, title=None, description=None):
    """Create video and upload to Cloudinary"""
    # Upload to Cloudinary
    result = upload_media(
        video_path, 
        folder="videos",
        resource_type="video",
        title=title,
        description=description
    )
    
    # Clean up temporary file
    if os.path.exists(video_path) and video_path.startswith(TEMP_DIR):
        os.remove(video_path)
        
    return result


async def download_video_media_from_cloud(media_id:str) ->BytesIO|None:
    try:
        video = BytesIO()
        media = await get_media_by_id(media_id)
        if not media or not media.get("url"):
            return None
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", media.get("url")) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(8192):
                    video.write(chunk)
        video.seek(0)
        return video
    except Exception as e:
        return None

def create_multi_scene_video(image_paths, audio_path, output_path=None, 
                           min_scene_duration=3.0, max_scene_duration=8.0, 
                           transition_duration=0.5, enable_transitions=True):
    """
    Create an advanced multi-scene video from multiple images and audio using FFmpeg
    
    Args:
        image_paths: List of image file paths
        audio_path: Path to audio file
        output_path: Output video path (optional)
        min_scene_duration: Minimum duration per scene in seconds
        max_scene_duration: Maximum duration per scene in seconds
        transition_duration: Duration of transitions between scenes
        enable_transitions: Whether to add crossfade transitions
    """
    if not output_path:
        output_path = os.path.join(TEMP_DIR, f"multiscene_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
    
    print(f"🎬 Creating advanced multi-scene video with:")
    print(f"  📁 Images: {len(image_paths)} images")
    for i, img in enumerate(image_paths):
        print(f"     {i+1}. {os.path.basename(img)} (exists: {os.path.exists(img)})")
    print(f"  🎵 Audio: {audio_path} (exists: {os.path.exists(audio_path)})")
    print(f"  ⏱️ Scene duration: {min_scene_duration}s - {max_scene_duration}s")
    print(f"  🎞️ Transitions: {'Enabled' if enable_transitions else 'Disabled'}")
    print(f"  📤 Output: {output_path}")
    
    # Force multi-scene even with 1 image if user explicitly wants it
    # Only fallback to single image if there's a real problem
    
    try:
        # Get accurate audio duration using ffprobe
        audio_duration = get_audio_duration(audio_path)
        print(f"🎵 Audio duration detected: {audio_duration:.2f}s ({audio_duration/60:.2f} minutes)")
        
        if audio_duration <= 0:
            print("❌ Invalid audio duration, using fallback")
            return create_video(image_paths[0], audio_path, output_path) if image_paths else None
        
        # Calculate optimal scene arrangement
        scene_plan = calculate_scene_timing(image_paths, audio_duration, 
                                          min_scene_duration, max_scene_duration, 
                                          transition_duration if enable_transitions else 0)
        
        if not scene_plan:
            print("❌ No scene plan generated, using fallback")
            return create_video(image_paths[0], audio_path, output_path) if image_paths else None
        
        print(f"📋 Scene plan: {len(scene_plan)} scenes")
        for i, scene in enumerate(scene_plan):
            print(f"  Scene {i+1}: {os.path.basename(scene['image'])} -> {scene['duration']:.2f}s (start: {scene['start_time']:.2f}s)")
        
        # Debug: Show detailed scene planning information
        debug_scene_plan(scene_plan, audio_duration, transition_duration if enable_transitions else 0)
        
        # Create video using appropriate method
        if enable_transitions and len(scene_plan) > 1:
            print("🎞️ Creating video with transitions...")
            result = create_video_with_transitions(scene_plan, audio_path, output_path, transition_duration)
        else:
            print("🎬 Creating video with simple concatenation...")
            result = create_video_simple_concat(scene_plan, audio_path, output_path)
        
        if result and os.path.exists(result):
            print(f"✅ Multi-scene video created successfully: {result}")
            return result
        else:
            print("❌ Multi-scene video creation failed, using fallback")
            return create_video(image_paths[0], audio_path, output_path) if image_paths else None
        
    except Exception as e:
        print(f"Error creating multi-scene video: {e}")
        # Fallback to single image video
        if image_paths:
            print(f"Falling back to single image video using: {image_paths[0]}")
            return create_video(image_paths[0], audio_path, output_path)
        return None


def get_audio_duration(audio_path):
    """Get accurate audio duration using multiple methods"""
    if not os.path.exists(audio_path):
        print(f"⚠️ Audio file does not exist: {audio_path}")
        return 30.0
    
    print(f"🔍 Getting duration for audio file: {audio_path}")
    
    # Method 1: Try ffprobe (most accurate)
    ffprobe_path = imageio_ffmpeg.get_ffmpeg_exe().replace('ffmpeg', 'ffprobe')
    
    # Try standard ffprobe path first
    if not os.path.exists(ffprobe_path):
        # Try alternative paths
        ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        alt_ffprobe = os.path.join(ffmpeg_dir, 'ffprobe.exe')
        if os.path.exists(alt_ffprobe):
            ffprobe_path = alt_ffprobe
    
    if os.path.exists(ffprobe_path):
        try:
            cmd = [
                ffprobe_path,
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            print(f"🔧 Trying ffprobe: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10, encoding='utf-8', errors='replace')
            duration = float(result.stdout.strip())
            print(f"✅ ffprobe detected duration: {duration:.2f}s")
            return duration
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
            print(f"⚠️ ffprobe failed: {e}")
    else:
        print(f"⚠️ ffprobe not found at: {ffprobe_path}")
    
    # Method 1.5: Try ffmpeg info without processing
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        cmd = [ffmpeg_path, "-i", audio_path, "-hide_banner"]
        print(f"🔧 Trying ffmpeg info: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
        
        # Parse duration from stderr (where ffmpeg outputs info)
        import re
        duration_pattern = r"Duration:\s*(\d+):(\d+):(\d+\.\d+)"
        duration_match = re.search(duration_pattern, result.stderr)
        if duration_match:
            h, m, s = duration_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)
            print(f"✅ ffmpeg info detected duration: {duration:.2f}s")
            return duration
        else:
            print(f"⚠️ Could not parse duration from ffmpeg info: {result.stderr[:200]}...")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print(f"⚠️ ffmpeg info failed: {e}")
    
    # Method 2: Try ffmpeg with detailed output parsing
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        cmd = [ffmpeg_path, "-i", audio_path, "-f", "null", "-", "-hide_banner"]
        print(f"🔧 Trying ffmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace')
        
        # Parse duration from ffmpeg output - multiple patterns
        import re
        
        # Pattern 1: Duration line
        duration_pattern = r"Duration:\s*(\d+):(\d+):(\d+\.\d+)"
        duration_match = re.search(duration_pattern, result.stderr)
        if duration_match:
            h, m, s = duration_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)
            print(f"✅ ffmpeg (Duration) detected: {duration:.2f}s")
            return duration
        
        # Pattern 2: time= in processing output
        time_pattern = r"time=(\d+):(\d+):(\d+\.\d+)"
        time_matches = re.findall(time_pattern, result.stderr)
        if time_matches:
            # Get the last time entry (final duration)
            h, m, s = time_matches[-1]
            duration = int(h) * 3600 + int(m) * 60 + float(s)
            print(f"✅ ffmpeg (time=) detected: {duration:.2f}s")
            return duration
            
        print(f"⚠️ Could not parse duration from ffmpeg output: {result.stderr[:200]}...")
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print(f"⚠️ ffmpeg failed: {e}")
    
    # Method 3: Try to get file size and estimate (very rough fallback)
    try:
        file_size = os.path.getsize(audio_path)
        # Very rough estimate: assume 128kbps average bitrate
        # This is just a backup estimation
        estimated_duration = file_size / (128 * 1024 / 8)  # bytes / (bitrate in bytes/sec)
        estimated_duration = max(10.0, min(estimated_duration, 300.0))  # Clamp between 10s and 5min
        print(f"⚠️ Using rough file size estimation: {estimated_duration:.2f}s (file size: {file_size} bytes)")
        return estimated_duration
    except Exception as e:
        print(f"⚠️ File size estimation failed: {e}")
    
    # Final fallback - but log it clearly
    print(f"❌ All duration detection methods failed, using fallback: 30.0s")
    return 30.0


def calculate_scene_timing(image_paths, audio_duration, min_duration, max_duration, transition_duration):
    """
    Calculate optimal timing for each scene to exactly match audio duration
    NEW STRATEGY: Always distribute images evenly without repetition unless absolutely necessary
    
    Args:
        image_paths: List of image file paths
        audio_duration: Total audio duration in seconds
        min_duration: Minimum duration per scene (will be ignored to fit all images)
        max_duration: Maximum duration per scene (used as threshold for repetition)
        transition_duration: Duration of transitions between scenes
    
    Returns:
        List of scene dictionaries with image path, duration, and start_time
    """
    if not image_paths or audio_duration <= 0:
        return []
    
    print(f"🎯 Scene Planning (Equal Distribution Strategy):")
    print(f"   Images available: {len(image_paths)}")
    print(f"   Audio duration: {audio_duration:.2f}s ({audio_duration/60:.2f} minutes)")
    print(f"   Min scene duration: {min_duration}s")
    print(f"   Max scene duration: {max_duration}s")
    print(f"   Transition duration: {transition_duration}s")
    
    scenes = []
    
    # Calculate total transition time needed (between scenes)
    total_transition_time = max(0, (len(image_paths) - 1) * transition_duration)
    available_scene_time = audio_duration - total_transition_time
    
    # If transitions take too much time, reduce or disable them
    if available_scene_time <= 0 or available_scene_time < len(image_paths) * 1.0:
        print("⚠️ Disabling transitions - not enough time")
        transition_duration = 0
        total_transition_time = 0
        available_scene_time = audio_duration
    
    # ALWAYS USE EQUAL DISTRIBUTION STRATEGY
    # Calculate scene duration by dividing available time equally among all images
    # Each image appears exactly once, regardless of audio duration
    equal_scene_duration = available_scene_time / len(image_paths)
    
    print(f"   Available scene time: {available_scene_time:.2f}s")
    print(f"   Equal scene duration: {equal_scene_duration:.2f}s per image")
    
    # Always use each image exactly once - no repetition regardless of audio length
    image_list = image_paths
    scene_duration = equal_scene_duration
    
    print(f"   ✅ ALWAYS using equal distribution: each image gets {scene_duration:.2f}s")
    
    if scene_duration < min_duration:
        print(f"   ℹ️ Scene duration {scene_duration:.2f}s is below minimum {min_duration}s, but keeping it to show all images exactly once")
    elif scene_duration > max_duration:
        print(f"   ℹ️ Scene duration {scene_duration:.2f}s is above maximum {max_duration}s, but keeping it to show all images exactly once")
    
    print(f"   Final strategy: ALWAYS Equal distribution (no image repetition)")
    print(f"   Final scene duration: {scene_duration:.2f}s")
    print(f"   Final image count: {len(image_list)} (each image used exactly once)")
    
    # Create scenes with exact timing
    current_time = 0.0
    
    for i, image_path in enumerate(image_list):
        # For the last scene, adjust duration to end exactly at audio duration
        # accounting for transitions
        if i == len(image_list) - 1:
            # Calculate remaining time considering we won't add transition after last scene
            remaining_time = audio_duration - current_time
            effective_duration = remaining_time
        else:
            effective_duration = scene_duration
        
        # Ensure minimum duration (but prioritize fitting all images)
        if effective_duration < 0.5:
            effective_duration = 0.5
        
        scenes.append({
            'image': image_path,
            'duration': effective_duration,
            'start_time': current_time
        })
        
        image_name = os.path.basename(image_path)
        end_time = current_time + effective_duration
        print(f"   Scene {i+1:2d}: {image_name:20s} | {effective_duration:6.2f}s | {current_time:6.2f}s -> {end_time:6.2f}s")
        
        current_time += effective_duration
        
        # Add transition time (except for last scene)
        if i < len(image_list) - 1 and transition_duration > 0:
            current_time += transition_duration
        
        # Safety check - don't exceed audio duration
        if current_time >= audio_duration:
            break
    
    # Final verification
    total_calculated_time = sum(scene['duration'] for scene in scenes)
    print(f"   📊 Total calculated time: {total_calculated_time:.2f}s")
    print(f"   📊 Target audio time: {audio_duration:.2f}s")
    print(f"   📊 Time difference: {abs(total_calculated_time - audio_duration):.2f}s")
    
    # Check for image repetition
    unique_images = set(scene['image'] for scene in scenes)
    if len(unique_images) < len(scenes):
        repetition_factor = len(scenes) / len(unique_images)
        print(f"   🔄 Image repetition: {repetition_factor:.1f}x (using {len(unique_images)} unique images for {len(scenes)} scenes)")
    else:
        print(f"   ✅ Perfect: Each image used exactly once")
    
    return scenes


def create_video_with_transitions(scene_plan, audio_path, output_path, transition_duration):
    """Create video with crossfade transitions between scenes"""
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    
    try:
        # Build complex filter for transitions
        inputs = []
        filter_complex = []
        
        # Add all images as inputs
        for i, scene in enumerate(scene_plan):
            inputs.extend(["-loop", "1", "-t", str(scene['duration'] + transition_duration), "-i", scene['image']])
        
        # Add audio input
        inputs.extend(["-i", audio_path])
        audio_index = len(scene_plan)
        
        # Build filter chain for crossfades
        current_output = "0:v"
        
        for i in range(1, len(scene_plan)):
            # Scale and format each input
            filter_complex.append(f"[{i-1}:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i-1}]")
            filter_complex.append(f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]")
            
            # Create crossfade
            if i == 1:
                filter_complex.append(f"[v0][v1]xfade=transition=fade:duration={transition_duration}:offset={scene_plan[0]['duration']}[vout{i}]")
                current_output = f"vout{i}"
            else:
                offset = sum(s['duration'] for s in scene_plan[:i]) + (i-1) * transition_duration
                filter_complex.append(f"[{current_output}][v{i}]xfade=transition=fade:duration={transition_duration}:offset={offset}[vout{i}]")
                current_output = f"vout{i}"
        
        # If only one scene, just scale it
        if len(scene_plan) == 1:
            filter_complex = [f"[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[vout]"]
            current_output = "vout"
        
        # Build final command - ensure exact audio duration
        cmd = [ffmpeg_path] + inputs + [
            "-filter_complex", ";".join(filter_complex),
            "-map", f"[{current_output}]",
            "-map", f"{audio_index}:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(get_audio_duration(audio_path)),  # Ensure exact audio duration
            "-y",
            output_path
        ]
        
        print(f"Creating video with transitions...")
        subprocess.run(cmd, check=True)
        
        print(f"Video with transitions created successfully: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error creating video with transitions: {e}")
        # Fallback to simple concatenation
        return create_video_simple_concat(scene_plan, audio_path, output_path)


def create_video_simple_concat(scene_plan, audio_path, output_path):
    """Create video by concatenating scenes without transitions"""
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    scene_videos = []
    concat_file = None
    
    print(f"🎬 Creating video from {len(scene_plan)} scenes...")
    
    try:
        # Create individual scene videos
        for i, scene in enumerate(scene_plan):
            if not os.path.exists(scene['image']):
                print(f"⚠️ Warning: Image {scene['image']} does not exist, skipping")
                continue
            
            scene_video = os.path.join(TEMP_DIR, f"scene_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            
            print(f"   Creating scene {i+1}/{len(scene_plan)}: {os.path.basename(scene['image'])} ({scene['duration']:.2f}s)")
            
            cmd = [
                ffmpeg_path,
                "-loop", "1",
                "-t", str(scene['duration']),
                "-i", scene['image'],
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-r", "25",
                "-y",
                scene_video
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
                scene_videos.append(scene_video)
                print(f"   ✅ Scene {i+1} created: {os.path.basename(scene_video)}")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Failed to create scene {i+1}: {e}")
                if e.stderr:
                    print(f"   FFmpeg error: {e.stderr[:200]}...")
                continue
        
        if not scene_videos:
            raise Exception("No scene videos were created successfully")
        
        print(f"🔗 Concatenating {len(scene_videos)} scene videos...")
        
        # Create concat file
        concat_file = os.path.join(TEMP_DIR, f"concat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(concat_file, 'w', encoding='utf-8') as f:
            for video in scene_videos:
                video_path = os.path.abspath(video).replace('\\', '/')
                f.write(f"file '{video_path}'\n")
        
        print(f"📝 Concat file created: {concat_file}")
        
        # Get exact audio duration
        audio_duration = get_audio_duration(audio_path)
        
        # Concatenate and add audio - ensure exact audio duration
        final_cmd = [
            ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v",  # Take video from concat
            "-map", "1:a",  # Take audio from audio file
            "-t", str(audio_duration),  # Ensure exact audio duration
            "-avoid_negative_ts", "make_zero",  # Handle timestamp issues
            "-y",
            output_path
        ]
        
        print(f"🎵 Final concatenation with audio...")
        print(f"   Command: {' '.join(final_cmd)}")
        
        result = subprocess.run(final_cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        # Verify output file
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Video created successfully: {output_path}")
            print(f"   File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        else:
            raise Exception("Output file was not created")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error creating concatenated video: {e}")
        # Log more details for debugging
        if hasattr(e, 'stderr') and e.stderr:
            print(f"   FFmpeg error: {e.stderr}")
        raise e
        
    finally:
        # Cleanup temp files
        print("🧹 Cleaning up temporary files...")
        for video in scene_videos:
            if os.path.exists(video):
                try:
                    os.remove(video)
                    print(f"   Removed: {os.path.basename(video)}")
                except Exception as e:
                    print(f"   Failed to remove {video}: {e}")
        
        if concat_file and os.path.exists(concat_file):
            try:
                os.remove(concat_file)
                print(f"   Removed: {os.path.basename(concat_file)}")
            except Exception as e:
                print(f"   Failed to remove {concat_file}: {e}")


def cleanup_temp_file(file_path: str):
    """
    Clean up a single temporary file
    
    Args:
        file_path: Path to the file to delete
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {e}")


def cleanup_temp_files(file_paths: list):
    """
    Clean up multiple temporary files
    
    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        cleanup_temp_file(file_path)

async def check_media_of_user(user_id:str, media_id:str) -> bool:
    try:
        # Try both ObjectId and string format for user_id
        try:
            user_id_obj = ObjectId(user_id)
            query_filter = {
                "_id": ObjectId(media_id),
                "$or": [
                    {"user_id": user_id_obj},
                    {"user_id": user_id}
                ]
            }
        except:
            query_filter = {"_id": ObjectId(media_id), "user_id": user_id}
            
        media = await media_collection().find_one(query_filter)
        return media is not None
    except Exception as e:
        print(f"Error checking media ownership: {e}")
        return False

def debug_scene_plan(scene_plan, audio_duration, transition_duration=0):
    """Debug function to display detailed scene planning information"""
    print(f"\n📋 Scene Plan Debug Information:")
    print(f"  Audio Duration: {audio_duration:.2f}s")
    print(f"  Total Scenes: {len(scene_plan)}")
    print(f"  Transition Duration: {transition_duration:.2f}s")
    
    total_scene_time = 0
    total_transition_time = 0
    
    for i, scene in enumerate(scene_plan):
        scene_num = i + 1
        image_name = os.path.basename(scene['image'])
        duration = scene['duration']
        start_time = scene['start_time']
        end_time = start_time + duration
        
        print(f"  Scene {scene_num:2d}: {image_name:20s} | {duration:6.2f}s | {start_time:6.2f}s -> {end_time:6.2f}s")
        
        total_scene_time += duration
        if i < len(scene_plan) - 1:  # Not the last scene
            total_transition_time += transition_duration
    
    total_video_time = total_scene_time + total_transition_time
    time_difference = abs(total_video_time - audio_duration)
    
    print(f"\n  📊 Summary:")
    print(f"    Total Scene Time: {total_scene_time:.2f}s")
    print(f"    Total Transition Time: {total_transition_time:.2f}s")
    print(f"    Total Video Time: {total_video_time:.2f}s")
    print(f"    Audio Duration: {audio_duration:.2f}s")
    print(f"    Time Difference: {time_difference:.2f}s")
    print(f"    Timing Accuracy: {'✅ Perfect' if time_difference < 0.1 else '⚠️  Needs adjustment' if time_difference < 1.0 else '❌ Poor'}")
    
    # Check for image repetition
    unique_images = set(scene['image'] for scene in scene_plan)
    if len(unique_images) < len(scene_plan):
        repetition_factor = len(scene_plan) / len(unique_images)
        print(f"    Image Repetition: {repetition_factor:.1f}x (using {len(unique_images)} unique images for {len(scene_plan)} scenes)")
    else:
        print(f"    Image Usage: Each image used once")
    
    print()