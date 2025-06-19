from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from schemas.background import (
    BackgroundResponse, 
    BackgroundListResponse,
    BackgroundGenerationRequest, 
    BackgroundGenerationResponse
)
from services.background_service import (
    get_all_backgrounds,
    get_background_by_id,
    get_backgrounds_by_category,
    get_backgrounds_by_tags,
    get_free_backgrounds,
    get_premium_backgrounds,
    get_background_categories,
    search_backgrounds,
    generate_custom_background,
    get_recommended_backgrounds
)
import os

router = APIRouter(prefix="/backgrounds", tags=["Background Management"])

@router.get("/", response_model=BackgroundListResponse)
async def get_backgrounds(
    category: Optional[str] = Query(None, description="Filter by category"),
    premium: Optional[bool] = Query(None, description="Filter by premium status"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit number of results")
):
    """Get all available backgrounds with optional filtering"""
    try:
        if category:
            backgrounds = get_backgrounds_by_category(category)
        elif premium is not None:
            backgrounds = get_premium_backgrounds() if premium else get_free_backgrounds()
        elif tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            backgrounds = get_backgrounds_by_tags(tag_list)
        else:
            backgrounds = get_all_backgrounds()
        
        # Apply limit if specified
        if limit:
            backgrounds = backgrounds[:limit]
            
        categories = get_background_categories()
        
        return BackgroundListResponse(
            backgrounds=[BackgroundResponse(**bg) for bg in backgrounds],
            total=len(backgrounds),
            categories=categories
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backgrounds: {str(e)}")

@router.get("/search", response_model=BackgroundListResponse)
async def search_backgrounds_endpoint(
    q: str = Query(..., description="Search query"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Limit number of results")
):
    """Search backgrounds by title, category, or tags"""
    try:
        backgrounds = search_backgrounds(q)
        
        if limit:
            backgrounds = backgrounds[:limit]
            
        categories = get_background_categories()
        
        return BackgroundListResponse(
            backgrounds=[BackgroundResponse(**bg) for bg in backgrounds],
            total=len(backgrounds),
            categories=categories
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/categories")
async def get_background_categories_endpoint():
    """Get list of available background categories"""
    try:
        categories = get_background_categories()
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@router.get("/recommended")
async def get_recommended_backgrounds_endpoint(
    script_content: Optional[str] = Query(None, description="Script content for recommendations"),
    voice_id: Optional[str] = Query(None, description="Selected voice ID"),
    script_images: Optional[str] = Query(None, description="JSON string of image prompts from script"),
    limit: Optional[int] = Query(8, ge=1, le=20, description="Number of recommendations")
):
    """Get recommended backgrounds based on script content, voice, and generated image prompts"""
    try:
        # Parse script_images if provided
        image_prompts = None
        if script_images:
            import json
            try:
                image_prompts = json.loads(script_images)
                if not isinstance(image_prompts, list):
                    raise ValueError("script_images must be a JSON array")
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid script_images format: {str(e)}")
        
        backgrounds = await get_recommended_backgrounds(script_content, voice_id, image_prompts)
        
        if limit:
            backgrounds = backgrounds[:limit]
            
        return {
            "recommendations": [BackgroundResponse(**bg) for bg in backgrounds],
            "total": len(backgrounds),
            "generated_from_script": bool(image_prompts and len(image_prompts) > 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@router.post("/generate-from-script")
async def generate_backgrounds_from_script_endpoint(
    script_images: List[str] = Query(..., description="List of image prompts from script generation"),
    style: Optional[str] = Query("realistic", description="Generation style"),
    limit: Optional[int] = Query(3, ge=1, le=5, description="Maximum number of backgrounds to generate")
):
    """Generate backgrounds specifically from script image prompts"""
    try:
        if not script_images or len(script_images) == 0:
            raise HTTPException(status_code=400, detail="script_images cannot be empty")
        
        # Limit the number of images to process
        images_to_process = script_images[:limit]
        
        from services.background_service import generate_backgrounds_from_script_images
        generated_backgrounds = await generate_backgrounds_from_script_images(images_to_process, style)
        
        return {
            "backgrounds": [BackgroundResponse(**bg) for bg in generated_backgrounds],
            "total": len(generated_backgrounds),
            "generated_count": len(generated_backgrounds),
            "requested_count": len(images_to_process)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate backgrounds from script: {str(e)}")

@router.get("/{background_id}", response_model=BackgroundResponse)
async def get_background(background_id: str):
    """Get background by ID"""
    background = get_background_by_id(background_id)
    if not background:
        raise HTTPException(status_code=404, detail="Background not found")
    
    return BackgroundResponse(**background)

@router.post("/generate", response_model=BackgroundGenerationResponse)
async def generate_background(request: BackgroundGenerationRequest):
    """Generate custom background using AI"""
    try:
        result = generate_custom_background(
            prompt=request.prompt,
            style=request.style or "realistic",
            resolution=request.resolution or "1080x1920"
        )
        
        return BackgroundGenerationResponse(
            id=result["id"],
            image_url=result["image_url"],
            prompt=result["prompt"],
            style=result["style"],
            resolution=result["resolution"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Background generation failed: {str(e)}")

@router.get("/image/{background_id}/{filename}")
async def get_background_image(background_id: str, filename: str):
    """Serve background image files"""
    # This endpoint serves the background image files
    # In a production environment, you'd typically use a CDN or cloud storage
    from config import TEMP_DIR
    import os
    
    file_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Background image not found")
    
    return FileResponse(
        file_path,
        media_type="image/png",
        filename=filename
    )

@router.get("/preview/{background_id}")
async def get_background_preview(background_id: str):
    """Get background preview information"""
    background = get_background_by_id(background_id)
    if not background:
        raise HTTPException(status_code=404, detail="Background not found")
    
    return {
        "id": background["id"],
        "title": background["title"],
        "category": background["category"],
        "preview_url": background["image_url"],
        "description": f"A {background['category'].lower()} background: {background['title']}"
    }
