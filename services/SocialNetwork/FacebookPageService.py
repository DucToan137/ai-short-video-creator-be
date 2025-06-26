import requests
import logging
from typing import List, Dict, Any, Optional
from models.user import User
from schemas.social import FacebookPageResponse, FacebookPageListResponse
from config import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_REDIRECT_URI

logger = logging.getLogger(__name__)

class FacebookPageService:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
    
    async def get_user_pages(self, user: User) -> FacebookPageListResponse:
        """
        Lấy danh sách các Facebook Pages mà user có quyền quản lý
        """
        try:
            facebook_credentials = user.social_credentials.get('facebook')
            if not facebook_credentials:
                raise Exception("User has not linked Facebook account")
            
            # Lấy access token từ cấu trúc mới
            access_token = facebook_credentials.get('access_token')
            if not access_token:
                raise Exception("Facebook access token not found")
            
            # Kiểm tra xem đã có pages trong credentials chưa
            existing_pages = facebook_credentials.get('pages', [])
            if existing_pages:
                # Sử dụng pages đã có sẵn
                pages = []
                for page_data in existing_pages:
                    page = FacebookPageResponse(
                        page_id=page_data['id'],
                        page_name=page_data['name'],
                        page_access_token=page_data['access_token'],
                        category=page_data.get('category'),
                        about=page_data.get('about'),
                        picture_url=page_data.get('picture_url'),
                        is_published=page_data.get('is_published', True)
                    )
                    pages.append(page)
                return FacebookPageListResponse(pages=pages)
            
            # Nếu chưa có pages trong credentials, lấy từ Facebook API
            # Lấy danh sách pages
            url = f"{self.base_url}/me/accounts"
            params = {
                'access_token': access_token,
                'fields': 'id,name,access_token,category,about,picture{url},is_published'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            pages = []
            
            for page_data in data.get('data', []):
                page = FacebookPageResponse(
                    page_id=page_data['id'],
                    page_name=page_data['name'],
                    page_access_token=page_data['access_token'],
                    category=page_data.get('category'),
                    about=page_data.get('about'),
                    picture_url=page_data.get('picture', {}).get('data', {}).get('url'),
                    is_published=page_data.get('is_published', True)
                )
                pages.append(page)
            
            return FacebookPageListResponse(pages=pages)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Facebook pages: {str(e)}")
            raise Exception(f"Unable to fetch Facebook pages: {str(e)}")
        except Exception as e:
            logger.error(f"Error in get_user_pages: {str(e)}")
            raise
    
    async def upload_video_to_page(
        self, 
        page_id: str, 
        page_access_token: str, 
        video_url: str, 
        title: str, 
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Upload video lên Facebook Page
        """
        try:
            url = f"{self.base_url}/{page_id}/videos"
            
            # Chuẩn bị data
            data = {
                'access_token': page_access_token,
                'file_url': video_url,
                'title': title,
                'description': description,
                'published': True  # Always publish immediately as public
            }
            
            # Gửi request
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            
            # Lấy thông tin chi tiết của video vừa upload
            video_id = result.get('id')
            video_info = await self.get_video_info(video_id, page_access_token)
            
            return {
                'video_id': video_id,
                'video_info': video_info,
                'upload_success': True
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading video to Facebook page: {str(e)}")
            raise Exception(f"Unable to upload video to Facebook page: {str(e)}")
        except Exception as e:
            logger.error(f"Error in upload_video_to_page: {str(e)}")
            raise
    
    async def get_video_info(self, video_id: str, access_token: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết của video
        """
        try:
            url = f"{self.base_url}/{video_id}"
            params = {
                'access_token': access_token,
                'fields': 'id,title,description,created_time,permalink_url,status,length'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting video info: {str(e)}")
            return {}
    
    async def get_page_video_stats(self, video_id: str, access_token: str) -> Dict[str, Any]:
        """
        Lấy thống kê của video trên Facebook page
        """
        try:
            url = f"{self.base_url}/{video_id}/insights"
            params = {
                'access_token': access_token,
                'metric': 'post_video_views,post_reactions_by_type_total,post_video_complete_views_30s'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            stats = {}
            
            for metric in data.get('data', []):
                metric_name = metric.get('name')
                metric_values = metric.get('values', [])
                
                if metric_values:
                    if metric_name == 'post_video_views':
                        stats['view_count'] = metric_values[0].get('value', 0)
                    elif metric_name == 'post_reactions_by_type_total':
                        stats['reaction_count'] = metric_values[0].get('value', {})
                    elif metric_name == 'post_video_complete_views_30s':
                        stats['complete_views'] = metric_values[0].get('value', 0)
            
            return stats
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting video stats: {str(e)}")
            return {}
    
    async def delete_video_from_page(self, video_id: str, access_token: str) -> bool:
        """
        Xóa video khỏi Facebook page
        """
        try:
            url = f"{self.base_url}/{video_id}"
            params = {
                'access_token': access_token
            }
            
            response = requests.delete(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            return result.get('success', False)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting video: {str(e)}")
            return False
