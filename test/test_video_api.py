import sys
import os
import asyncio
import httpx

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.Media.text_to_speech import generate_speech_openai
from services.Media.text_to_image import generate_image_dalle
from api.routes.video import router
from fastapi.testclient import TestClient
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Test data
TEST_SCRIPT = "Hello, this is a test video created with AI technology. This video demonstrates the complete video creation process from script to final output."
TEST_VOICE_ID = "alloy"
TEST_BACKGROUND_PROMPT = "A beautiful sunset over mountains"

async def test_complete_video_creation():
    """Test complete video creation flow"""
    print("🎬 Testing Complete Video Creation Flow")
    print("=" * 50)
    
    try:
        # Step 1: Generate audio
        print("1. Generating audio from script...")
        audio_result = await generate_speech_openai(TEST_SCRIPT, TEST_VOICE_ID)
        if not audio_result:
            print("❌ Failed to generate audio")
            return
        print(f"✅ Audio generated: {audio_result['audio_path']}")
        
        # Step 2: Generate background image
        print("2. Generating background image...")
        image_result = await generate_image_dalle(TEST_BACKGROUND_PROMPT)
        if not image_result:
            print("❌ Failed to generate background image")
            return
        print(f"✅ Background image generated: {image_result['image_path']}")
        
        # Step 3: Upload background to get ID (simulate)
        print("3. Simulating background upload...")
        from services.Media.media_utils import upload_media
        background_upload = await upload_media(
            image_result['image_path'],
            "test_user_id",
            folder="backgrounds",
            resource_type="image",
            prompt=TEST_BACKGROUND_PROMPT
        )
        background_id = background_upload["media"]["id"]
        print(f"✅ Background uploaded with ID: {background_id}")
        
        # Step 4: Test video creation API call (simulation)
        print("4. Testing video creation API...")
        
        # Simulate API request data
        video_params = {
            "script_text": TEST_SCRIPT,
            "voice_id": TEST_VOICE_ID,
            "background_image_id": background_id,
            "subtitle_enabled": True,
            "subtitle_language": "en",
            "subtitle_style": "default"
        }
        
        print(f"   Request params: {video_params}")
        
        # Test the video creation logic (without actual API call due to auth requirements)
        from services.Media.media_utils import create_video, add_subtitles
        from services.subtitle_service import generate_srt_content
        import tempfile
        
        # Create video from image and audio
        video_path = create_video(image_result['image_path'], audio_result['audio_path'])
        if not video_path:
            print("❌ Failed to create video")
            return
        print(f"✅ Video created: {video_path}")
        
        # Add subtitles if enabled
        if video_params["subtitle_enabled"]:
            print("5. Adding subtitles to video...")
            srt_content = generate_srt_content(TEST_SCRIPT, audio_result.get('duration', 30))
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as srt_file:
                srt_file.write(srt_content)
                srt_path = srt_file.name
            
            final_video_path = add_subtitles(video_path, srt_path)
            if final_video_path:
                print(f"✅ Subtitles added: {final_video_path}")
            else:
                print("⚠️ Failed to add subtitles, using original video")
                final_video_path = video_path
            
            # Clean up SRT file
            os.unlink(srt_path)
        else:
            final_video_path = video_path
        
        # Step 6: Upload final video
        print("6. Uploading final video...")
        final_upload = await upload_media(
            final_video_path,
            "test_user_id",
            folder="videos",
            resource_type="video",
            prompt=f"Complete video: {TEST_SCRIPT[:50]}...",
            metadata=video_params
        )
        
        print(f"✅ Final video uploaded: {final_upload['media']['url']}")
        
        # Clean up temporary files
        for temp_file in [audio_result['audio_path'], image_result['image_path'], video_path]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        if final_video_path != video_path and os.path.exists(final_video_path):
            os.unlink(final_video_path)
        
        print("\n🎉 Complete Video Creation Test PASSED!")
        print(f"Final video URL: {final_upload['media']['url']}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def test_video_from_components():
    """Test creating video from existing components"""
    print("\n🔧 Testing Video Creation from Components")
    print("=" * 50)
    
    try:
        # Generate test components first
        print("1. Generating test components...")
        
        # Generate audio
        audio_result = await generate_speech_openai("This is a test for component-based video creation.", TEST_VOICE_ID)
        if not audio_result:
            print("❌ Failed to generate audio")
            return
        
        # Generate image
        image_result = await generate_image_dalle("A serene lake with mountains in the background")
        if not image_result:
            print("❌ Failed to generate image")
            return
        
        # Upload components
        audio_upload = await upload_media(
            audio_result['audio_path'],
            "test_user_id",
            folder="audio",
            resource_type="auto",
            prompt="Test audio component"
        )
        
        image_upload = await upload_media(
            image_result['image_path'],
            "test_user_id",
            folder="backgrounds",
            resource_type="image",
            prompt="Test background component"
        )
        
        print(f"✅ Components uploaded - Audio: {audio_upload['media']['id']}, Image: {image_upload['media']['id']}")
        
        # Test component-based video creation
        print("2. Creating video from components...")
        
        from services.Media.media_utils import create_video
        video_path = create_video(image_result['image_path'], audio_result['audio_path'])
        
        if video_path:
            final_upload = await upload_media(
                video_path,
                "test_user_id",
                folder="videos",
                resource_type="video",
                prompt="Video from components",
                metadata={
                    "audio_file_id": audio_upload['media']['id'],
                    "background_image_id": image_upload['media']['id'],
                    "subtitle_enabled": False
                }
            )
            
            print(f"✅ Video from components created: {final_upload['media']['url']}")
            
            # Clean up
            for temp_file in [audio_result['audio_path'], image_result['image_path'], video_path]:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            print("\n🎉 Component-based Video Creation Test PASSED!")
        else:
            print("❌ Failed to create video from components")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def test_api_endpoints():
    """Test API endpoint structure (without authentication)"""
    print("\n🔗 Testing API Endpoint Structure")
    print("=" * 50)
    
    # Test endpoint availability (will fail due to auth, but we can check structure)
    endpoints_to_test = [
        ("/api/video/create-complete", "POST"),
        ("/api/video/create-from-components", "POST"),
        ("/api/video/preview/test-id", "GET"),
        ("/api/video/download/test-id", "GET"),
    ]
    
    for endpoint, method in endpoints_to_test:
        try:
            if method == "POST":
                response = client.post(endpoint, json={"test": "data"})
            else:
                response = client.get(endpoint)
            
            # We expect 401 (unauthorized) which means the endpoint exists
            if response.status_code == 401:
                print(f"✅ {method} {endpoint} - Endpoint exists (authentication required)")
            elif response.status_code == 422:
                print(f"✅ {method} {endpoint} - Endpoint exists (validation error expected)")
            else:
                print(f"⚠️ {method} {endpoint} - Status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {method} {endpoint} - Error: {e}")
    
    print("\n📋 API Endpoints Test Complete!")

async def main():
    """Run all tests"""
    print("🚀 Starting Video API Tests")
    print("=" * 60)
    
    # Test complete video creation flow
    await test_complete_video_creation()
    
    # Test video creation from components
    await test_video_from_components()
    
    # Test API endpoint structure
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("🏁 All Video API Tests Complete!")

if __name__ == "__main__":
    asyncio.run(main())
