from services import check_and_refresh_google_credentials,download_video_media_from_cloud
from models import User,SocialVideoCreate
from schemas import VideoUpLoadRequest,GoogleVideoStatsResponse,SocialPlatform
from googleapiclient.discovery import build,Resource
from googleapiclient.http import MediaIoBaseUpload
from fastapi import HTTPException, status
from .SocialUtils import add_social_video
from datetime import datetime
from typing import List,Any
async def get_youtube_service(user:User) -> Resource:
    credentials = await check_and_refresh_google_credentials(user)
    return build(
        'youtube',
        'v3',
        credentials=credentials
    )
async def upload_video_to_youtube(user:User,upload_request:VideoUpLoadRequest)->str:
    try:
        youtube_service = await get_youtube_service(user)
        body={
            'snippet': {
                'title': upload_request.title,
                'description': upload_request.description,
                'tags': upload_request.tags,
            },
            'status': {
                'privacyStatus': upload_request.privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        video_stream = await download_video_media_from_cloud(upload_request.media_id)
        
        if video_stream is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video media not found"
            )
        if len(video_stream.getvalue()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video media is empty"
            )
        media = MediaIoBaseUpload(
            video_stream,
            chunksize=1024 * 1024,  # 1 MB chunks
            resumable=True,
            mimetype='video/mp4'
        )
        insert_request = youtube_service.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        response= insert_request.execute()
        video_id =response['id']
        social_video_data = SocialVideoCreate(
            user_id=str(user.id),
            platform=SocialPlatform.GOOGLE,
            video_id = upload_request.media_id,
            video_url=video_id
        )
        await add_social_video(social_video_data)
        return f'https://www.youtube.com/watch?v={video_id}'
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video to YouTube: {str(e)}"
        )
async def get_youtube_video_stats(user:User,video_id:str)->GoogleVideoStatsResponse:
    try:
        youtube_service = await get_youtube_service(user)
        request =youtube_service.videos().list(
            part='statistics,snippet',
            id=video_id
        )
        response = request.execute()
        if not response['items']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        video_data = response['items'][0]
        stats = video_data['statistics']
        snippet = video_data['snippet']
        return GoogleVideoStatsResponse(
            platform='google',
            title=snippet.get('title', ''),
            description=snippet.get('description', ''),
            platform_url=f'https://www.youtube.com/watch?v={video_id}',
            view_count=int(stats.get('viewCount', 0)),
            like_count=int(stats.get('likeCount', 0)),
            comment_count=int(stats.get('commentCount', 0)),
            created_at=snippet.get('publishedAt')
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get YouTube video stats: {str(e)}"
        )
        
    
async def get_top_youtube_videos_by_views_and_date(user: User, start_date: datetime, end_date: datetime,type_sta:str, max_results: int = 10) -> List[dict[str, Any]]:
    try:
        youtube_service = await get_youtube_service(user)

        # Lấy uploads playlist ID
        channels_response = youtube_service.channels().list(
            part="contentDetails",
            mine=True
        ).execute()

        if not channels_response['items']:
            raise HTTPException(status_code=404, detail="YouTube channel not found")

        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        video_infos = []
        next_page_token = None

        # Duyệt hết các video trong uploads playlist
        while True:
            playlist_response = youtube_service.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            for item in playlist_response['items']:
                published_at_str = item['snippet']['publishedAt']
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))

                if start_date <= published_at <= end_date:
                    video_infos.append({
                        'id': item['snippet']['resourceId']['videoId'],
                        'publishedAt': published_at
                    })

            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break

        if not video_infos:
            return []

        # Lấy statistics theo batch 50 video/lần
        all_video_stats = []
        for i in range(0, len(video_infos), 50):
            batch_infos = video_infos[i:i+50]
            batch_ids = [v['id'] for v in batch_infos]

            videos_response = youtube_service.videos().list(
                part="statistics,snippet",
                id=",".join(batch_ids)
            ).execute()

            for video in videos_response['items']:
                stats = video['statistics']
                snippet = video['snippet']
                all_video_stats.append(
                    {
                        "title": snippet.get('title', ''),
                        "count": int(stats.get(f'{type_sta}Count', 0)),
                    }
                )
        all_video_stats.sort(key=lambda v: v['count'], reverse=True)
        return all_video_stats[:max_results]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top YouTube videos: {str(e)}")


















    

