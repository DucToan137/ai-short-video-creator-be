"""
Utility script to generate sample background images and upload to Cloudinary
Run this once to populate Cloudinary with preset background images
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.background_service import upload_image_to_cloudinary, AVAILABLE_BACKGROUNDS
from services.Media.text_to_image import generate_image
from config import TEMP_DIR
from uuid import uuid4

def generate_and_upload_preset_backgrounds():
    """Generate and upload preset background images to Cloudinary"""
    print("🎨 Generating and uploading preset background images...")
    print("=" * 60)
    
    # Enhanced prompts for each background category
    background_prompts = {
        "bg1": "A minimalist modern workspace with clean desk, laptop, coffee cup, natural lighting, professional and organized",
        "bg2": "Urban cityscape with modern skyscrapers, glass buildings, bustling street life, contemporary architecture",
        "bg3": "Majestic mountain vista with snow-capped peaks, clear blue sky, pristine nature landscape, panoramic view",
        "bg4": "Calm ocean waves on pristine beach, turquoise water, white sand, tropical paradise, peaceful seascape",
        "bg5": "Abstract gradient background in blue tones, modern geometric patterns, digital art, sleek design",
        "bg6": "Cozy coffee shop interior with wooden tables, warm lighting, coffee beans, rustic atmosphere",
        "bg7": "Grand library study hall with tall bookshelves, reading tables, warm amber lighting, academic atmosphere",
        "bg8": "Modern corporate office with glass walls, contemporary furniture, professional business environment",
        "bg9": "Enchanted forest path with tall trees, dappled sunlight, lush green foliage, magical atmosphere",
        "bg10": "Golden sunset beach with palm trees, warm colors, romantic tropical setting, peaceful evening",
        "bg11": "Vibrant abstract geometric shapes and patterns, colorful modern art, contemporary design",
        "bg12": "Night city lights with illuminated skyscrapers, urban nightlife, neon reflections, dynamic cityscape"
    }
    
    uploaded_urls = {}
    
    for bg in AVAILABLE_BACKGROUNDS:
        bg_id = bg["id"]
        bg_title = bg["title"]
        
        print(f"\n🎯 Processing {bg_id}: {bg_title}")
        
        try:
            # Get enhanced prompt
            prompt = background_prompts.get(bg_id, f"Beautiful {bg_title.lower()} background")
            enhanced_prompt = f"{prompt}, high quality, professional photography, 16:9 aspect ratio, suitable for video background"
            
            # Generate image
            output_file = os.path.join(TEMP_DIR, f"{bg_id}_background.png")
            print(f"   🖼️ Generating image...")
            
            result_file = generate_image("flux", enhanced_prompt, output_file)
            
            if result_file and os.path.exists(result_file):
                # Upload to Cloudinary
                print(f"   📤 Uploading to Cloudinary...")
                public_url = upload_image_to_cloudinary(result_file, f"backgrounds/preset")
                uploaded_urls[bg_id] = public_url
                print(f"   ✅ Success: {public_url}")
            else:
                print(f"   ❌ Failed to generate image")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            continue
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"🎉 Upload completed! {len(uploaded_urls)}/{len(AVAILABLE_BACKGROUNDS)} backgrounds uploaded")
    
    if uploaded_urls:
        print("\n📋 Uploaded URLs:")
        for bg_id, url in uploaded_urls.items():
            bg_title = next(bg["title"] for bg in AVAILABLE_BACKGROUNDS if bg["id"] == bg_id)
            print(f"   {bg_id}: {bg_title}")
            print(f"   → {url}")
            print()

def generate_demo_backgrounds():
    """Generate just a few demo backgrounds for testing"""
    print("🎨 Generating demo backgrounds for testing...")
    
    demo_prompts = [
        "A vibrant morning scene with breakfast table, warm sunlight, cozy kitchen atmosphere",
        "Modern minimalist workspace with laptop and coffee, clean professional environment",
        "Beautiful nature landscape with mountains and clear sky, peaceful outdoor setting"
    ]
    
    for i, prompt in enumerate(demo_prompts, 1):
        try:
            print(f"\n🎯 Generating demo background {i}/3...")
            
            output_file = os.path.join(TEMP_DIR, f"demo_bg_{i}.png")
            result_file = generate_image("flux", prompt, output_file)
            
            if result_file and os.path.exists(result_file):
                public_url = upload_image_to_cloudinary(result_file, "backgrounds/demo")
                print(f"✅ Demo background {i} uploaded: {public_url}")
            else:
                print(f"❌ Failed to generate demo background {i}")
                
        except Exception as e:
            print(f"❌ Error generating demo background {i}: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        generate_demo_backgrounds()
    else:
        print("Choose an option:")
        print("1. Generate all preset backgrounds (takes time)")
        print("2. Generate demo backgrounds only")
        choice = input("Enter choice (1 or 2): ")
        
        if choice == "1":
            generate_and_upload_preset_backgrounds()
        elif choice == "2":
            generate_demo_backgrounds()
        else:
            print("Invalid choice. Use 'python upload_backgrounds.py demo' for quick demo.")
