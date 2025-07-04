from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models.user import User
from api.deps import get_current_user
from schemas.social import (
    FacebookPageListResponse, 
    FacebookPageVideoUploadRequest,
    VideoStatsResponse
)
from services.SocialNetwork.FacebookPageService import FacebookPageService
from services import get_media_by_id

router = APIRouter(prefix="/facebook-pages", tags=["Facebook Pages"])

facebook_page_service = FacebookPageService()

@router.get("/", response_model=FacebookPageListResponse)
async def get_user_facebook_pages(current_user: User = Depends(get_current_user)):
    """
    Get list of Facebook Pages that user can manage
    """
    try:
        # Check if user has linked Facebook account
        if not current_user.social_credentials.get('facebook'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need to link your Facebook account before using this feature"
            )
        
        pages = await facebook_page_service.get_user_pages(current_user)
        return pages
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/upload-video")
async def upload_video_to_facebook_page(
    upload_request: FacebookPageVideoUploadRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Upload video to Facebook Page
    """
    try:
        # Check if user has linked Facebook account
        if not current_user.social_credentials.get('facebook'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need to link your Facebook account before using this feature"
            )
        
        # Get user's pages list to verify access permissions
        pages_response = await facebook_page_service.get_user_pages(current_user)
        
        # Find selected page
        selected_page = None
        for page in pages_response.pages:
            if page.page_id == upload_request.page_id:
                selected_page = page
                break
        
        if not selected_page:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this Facebook Page"
            )
        
        # Get video information from media_id
        video_media = await get_media_by_id(upload_request.media_id)
        if not video_media:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Get video URL from media
        video_url = video_media.get('url') or video_media.get('cloudinary_url')
        if not video_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to get video URL"
            )
        
        # Upload video
        result = await facebook_page_service.upload_video_to_page(
            page_id=selected_page.page_id,
            page_access_token=selected_page.page_access_token,
            video_url=video_url,
            title=upload_request.title,
            description=upload_request.description or ""
        )
        
        return {
            "success": True,
            "message": "Video has been successfully uploaded to Facebook Page",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while uploading video: {str(e)}"
        )

@router.get("/video/{video_id}/stats")
async def get_facebook_video_stats(
    video_id: str,
    page_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get video statistics on Facebook Page
    """
    try:
        # Check if user has linked Facebook account
        if not current_user.social_credentials.get('facebook'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need to link your Facebook account before using this feature"
            )
        
        # Get user's pages list to verify access permissions
        pages_response = await facebook_page_service.get_user_pages(current_user)
        
        # Find selected page
        selected_page = None
        for page in pages_response.pages:
            if page.page_id == page_id:
                selected_page = page
                break
        
        if not selected_page:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this Facebook Page"
            )
        
        # Get video statistics
        stats = await facebook_page_service.get_page_video_stats(
            video_id=video_id,
            access_token=selected_page.page_access_token
        )
        
        return {
            "success": True,
            "data": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while getting video statistics: {str(e)}"
        )

@router.delete("/video/{video_id}")
async def delete_facebook_video(
    video_id: str,
    page_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete video from Facebook Page
    """
    try:
        # Check if user has linked Facebook account
        if not current_user.social_credentials.get('facebook'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need to link your Facebook account before using this feature"
            )
        
        # Get user's pages list to verify access permissions
        pages_response = await facebook_page_service.get_user_pages(current_user)
        
        # Find selected page
        selected_page = None
        for page in pages_response.pages:
            if page.page_id == page_id:
                selected_page = page
                break
        
        if not selected_page:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this Facebook Page"
            )
        
        # Delete video
        success = await facebook_page_service.delete_video_from_page(
            video_id=video_id,
            access_token=selected_page.page_access_token
        )
        
        if success:
            return {
                "success": True,
                "message": "Video has been successfully deleted"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to delete video"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting video: {str(e)}"
        )
