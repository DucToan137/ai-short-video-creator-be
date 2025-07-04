from typing import List, Dict, Optional
import os
from services.Media.text_to_image import generate_image
from services.Media.media_utils import upload_media
from config import TEMP_DIR
from uuid import uuid4

# Background data mapping from frontend mockdata
AVAILABLE_BACKGROUNDS = [
    {
        "id": "bg1",
        "title": "Minimalist Workspace",
        "category": "Workspace",
        "tags": ["workspace", "minimalist", "clean", "professional"],
        "premium": False
    },
    {
        "id": "bg2",
        "title": "Urban Cityscape",
        "category": "City",
        "tags": ["city", "urban", "modern", "architecture"],
        "premium": False
    },
    {
        "id": "bg3",
        "title": "Mountain Vista",
        "category": "Nature",
        "tags": ["nature", "mountains", "scenery", "outdoors"],
        "premium": False
    },
    {
        "id": "bg4",
        "title": "Ocean Waves",
        "category": "Nature",
        "tags": ["nature", "ocean", "water", "calming"],
        "premium": False
    },
    {
        "id": "bg5",
        "title": "Abstract Gradient Blue",
        "category": "Abstract",
        "tags": ["abstract", "gradient", "blue", "modern"],
        "premium": False
    },
    {
        "id": "bg6",
        "title": "Coffee Shop Interior",
        "category": "Workspace",
        "tags": ["coffee", "cozy", "indoor", "casual"],
        "premium": False
    },
    {
        "id": "bg7",
        "title": "Library Study Hall",
        "category": "Workspace",
        "tags": ["library", "books", "study", "academic"],
        "premium": True
    },
    {
        "id": "bg8",
        "title": "Modern Office",
        "category": "Workspace",
        "tags": ["office", "corporate", "modern", "business"],
        "premium": True
    },
    {
        "id": "bg9",
        "title": "Forest Path",
        "category": "Nature",
        "tags": ["forest", "trees", "path", "green"],
        "premium": True
    },
    {
        "id": "bg10",
        "title": "Sunset Beach",
        "category": "Nature",
        "tags": ["beach", "sunset", "golden", "peaceful"],
        "premium": True
    },
    {
        "id": "bg11",
        "title": "Abstract Geometric",
        "category": "Abstract",
        "tags": ["geometric", "shapes", "colorful", "modern"],
        "premium": False
    },
    {
        "id": "bg12",
        "title": "Night City Lights",
        "category": "City",
        "tags": ["night", "lights", "cityscape", "vibrant"],
        "premium": True
    }
]

def get_all_backgrounds() -> List[Dict]:
    """Get all available backgrounds"""
    return [
        {
            "id": bg["id"],
            "title": bg["title"],
            "category": bg["category"],
            "image_url": f"/assets/images/backgrounds/{bg['id']}.jpg",
            "thumbnail_url": f"/assets/images/backgrounds/thumbnails/{bg['id']}_thumb.jpg",
            "tags": bg["tags"],
            "premium": bg["premium"],
            "available": True
        }
        for bg in AVAILABLE_BACKGROUNDS
    ]

def get_background_by_id(background_id: str) -> Optional[Dict]:
    """Get background by ID"""
    for bg in AVAILABLE_BACKGROUNDS:
        if bg["id"] == background_id:
            return {
                "id": bg["id"],
                "title": bg["title"],
                "category": bg["category"],
                "image_url": f"/assets/images/backgrounds/{bg['id']}.jpg",
                "thumbnail_url": f"/assets/images/backgrounds/thumbnails/{bg['id']}_thumb.jpg",
                "tags": bg["tags"],
                "premium": bg["premium"],
                "available": True
            }
    return None

def get_backgrounds_by_category(category: str) -> List[Dict]:
    """Get backgrounds filtered by category"""
    return [
        bg for bg in get_all_backgrounds()
        if bg["category"].lower() == category.lower()
    ]

def get_backgrounds_by_tags(tags: List[str]) -> List[Dict]:
    """Get backgrounds filtered by tags"""
    filtered_backgrounds = []
    for bg in get_all_backgrounds():
        # Check if any of the provided tags match the background tags
        if any(tag.lower() in [bt.lower() for bt in bg["tags"]] for tag in tags):
            filtered_backgrounds.append(bg)
    return filtered_backgrounds

def get_free_backgrounds() -> List[Dict]:
    """Get only free backgrounds"""
    return [bg for bg in get_all_backgrounds() if not bg["premium"]]

def get_premium_backgrounds() -> List[Dict]:
    """Get only premium backgrounds"""
    return [bg for bg in get_all_backgrounds() if bg["premium"]]

def get_background_categories() -> List[str]:
    """Get list of available categories"""
    categories = set()
    for bg in AVAILABLE_BACKGROUNDS:
        categories.add(bg["category"])
    return sorted(list(categories))

def search_backgrounds(query: str) -> List[Dict]:
    """Search backgrounds by title, category, or tags"""
    query_lower = query.lower()
    results = []
    
    for bg in get_all_backgrounds():
        # Search in title
        if query_lower in bg["title"].lower():
            results.append(bg)
            continue
            
        # Search in category
        if query_lower in bg["category"].lower():
            results.append(bg)
            continue
            
        # Search in tags
        if any(query_lower in tag.lower() for tag in bg["tags"]):
            results.append(bg)
            continue
    
    return results

async def generate_custom_background(prompt: str, style: str = "realistic", resolution: str = "1080x1920") -> Dict:
    """
    Generate custom background using AI image generation and upload to Cloudinary
    
    Args:
        prompt: Description of the background to generate
        style: Image style (realistic, abstract, cartoon)
        resolution: Image resolution (default 1080x1920 for vertical video)
        
    Returns:
        Dict with generated background info including Cloudinary URL
    """
    try:
        # Parse resolution
        if 'x' in resolution:
            width, height = map(int, resolution.split('x'))
        else:
            width, height = 1080, 1920
        
        # Generate image using existing service
        output_file = os.path.join(TEMP_DIR, f"bg_custom_{uuid4()}.png")
        
        # Use Flux model for background generation
        result_file = generate_image("flux", prompt, style, output_file)
        
        if not result_file or not os.path.exists(result_file):
            raise Exception("Failed to generate background image")
        
        # Upload to Cloudinary using await (now that this is an async function)
        try:
            upload_result = await upload_media(
                result_file,
                "system",  # System user for generated backgrounds
                folder="backgrounds",
                resource_type="image",
                prompt=f"Generated background: {prompt[:100]}",
                metadata={
                    "style": style,
                    "resolution": resolution,
                    "prompt": prompt,
                    "type": "generated_background"
                }            )
            
            print(f"Upload result: {upload_result}")  # Debug logging
            
            # Clean up local file
            if os.path.exists(result_file):
                os.remove(result_file)
            
            # Use the actual database ID from upload_media
            background_id = upload_result["id"]
            
            return {
                "id": background_id,
                "title": f"Custom: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
                "category": "Custom",
                "image_url": upload_result["url"],  # Use URL from upload_result
                "thumbnail_url": upload_result["url"],  # Use same URL for thumbnail
                "tags": ["custom", "generated", style],
                "premium": False,
                "available": True,
                "cloudinary_id": upload_result["id"],
                "public_id": upload_result["public_id"],
                "prompt": prompt,
                "style": style,                
                "resolution": resolution
            }
            
        except Exception as upload_error:
            print(f"Upload error details: {upload_error}")  # Debug logging
            # If upload fails, clean up the file and reraise
            if os.path.exists(result_file):
                os.remove(result_file)
            raise Exception(f"Failed to upload background to cloud: {str(upload_error)}")
        
    except Exception as e:
        raise Exception(f"Background generation failed: {str(e)}")

async def get_recommended_backgrounds(script_content: str = None, selected_voice: str = None, script_images: list = None) -> List[Dict]:
    """
    Get recommended backgrounds based on script content and generated image prompts
    
    Args:
        script_content: Script content to analyze for recommendations
        selected_voice: Selected voice ID for context
        script_images: List of image prompts from script generation
        
    Returns:
        List of recommended backgrounds
    """
    recommendations = []
    
    # If we have image prompts from script generation, create custom backgrounds
    if script_images and len(script_images) > 0:
        print(f"🎨 Generating backgrounds from {len(script_images)} image prompts...")
        
        for i, image_prompt in enumerate(script_images[:3]):  # Limit to 3 custom backgrounds
            try:
                # Generate custom background from image prompt (now async)
                custom_bg = await generate_custom_background(
                    prompt=image_prompt,
                    style="realistic",
                    resolution="1080x1920"
                )
                
                # Update title to be more descriptive
                custom_bg["title"] = f"Scene {i+1}: {image_prompt[:50]}{'...' if len(image_prompt) > 50 else ''}"
                custom_bg["category"] = "Script Generated"
                custom_bg["tags"].extend(["script-based", "ai-generated", f"scene-{i+1}"])
                
                recommendations.append(custom_bg)
                print(f"✅ Generated background {i+1}: {custom_bg['title']}")
                
            except Exception as e:
                print(f"❌ Failed to generate background {i+1}: {str(e)}")
                continue
    
    # Add some default backgrounds based on script content analysis
    if script_content:
        script_lower = script_content.lower()
        
        # Business/Professional content
        if any(keyword in script_lower for keyword in ['business', 'professional', 'corporate', 'office', 'meeting']):
            recommendations.extend(get_backgrounds_by_category("Workspace"))
        
        # Food/Cooking content (like sahur example)
        if any(keyword in script_lower for keyword in ['food', 'sahur', 'breakfast', 'meal', 'cooking', 'kitchen', 'recipe']):
            # Add kitchen and dining related backgrounds
            kitchen_backgrounds = [bg for bg in get_all_backgrounds() if any(tag in bg["tags"] for tag in ["kitchen", "dining", "food", "cozy"])]
            recommendations.extend(kitchen_backgrounds)
        
        # Nature/Wellness content
        if any(keyword in script_lower for keyword in ['nature', 'health', 'wellness', 'meditation', 'peaceful', 'morning']):
            recommendations.extend(get_backgrounds_by_category("Nature"))
        
        # Technology/Modern content
        if any(keyword in script_lower for keyword in ['technology', 'digital', 'modern', 'innovation', 'future']):
            recommendations.extend(get_backgrounds_by_category("Abstract"))
            recommendations.extend(get_backgrounds_by_category("City"))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_recommendations = []
    for bg in recommendations:
        if bg["id"] not in seen:
            seen.add(bg["id"])
            unique_recommendations.append(bg)
    
    # If not enough recommendations, add some defaults
    if len(unique_recommendations) < 6:
        for bg in get_all_backgrounds():
            if len(unique_recommendations) >= 8:
                break
            if bg["id"] not in seen:
                unique_recommendations.append(bg)
                seen.add(bg["id"])
    
    return unique_recommendations[:8]

async def generate_backgrounds_from_script_images(script_images: list, style: str = "realistic") -> List[Dict]:
    """
    Generate multiple backgrounds from script image prompts
    
    Args:
        script_images: List of image prompts from script generation
        style: Image generation style
        
    Returns:
        List of generated background dictionaries
    """
    generated_backgrounds = []
    
    for i, image_prompt in enumerate(script_images):
        try:
            print(f"🎨 Generating background {i+1}/{len(script_images)}: {image_prompt[:50]}...")
            
            # Generate background (now async)
            background = await generate_custom_background(
                prompt=image_prompt,
                style=style,
                resolution="1080x1920"
            )
            
            # Enhance metadata
            background.update({
                "title": f"Script Scene {i+1}",
                "category": "Script Generated",
                "tags": ["script-based", "auto-generated", f"scene-{i+1}", style],
                "script_prompt": image_prompt,
                "scene_number": i + 1
            })
            
            generated_backgrounds.append(background)
            print(f"✅ Background {i+1} generated successfully")
            
        except Exception as e:
            print(f"❌ Failed to generate background {i+1}: {str(e)}")
            continue
    
    return generated_backgrounds
