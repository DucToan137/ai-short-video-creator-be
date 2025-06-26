from models import User
from schemas import VideoUpLoadRequest
from fastapi import HTTPException, status
from services import check_and_refresh_tiktok_credentials,download_video_media_from_cloud
import math
import httpx


async def upload_video_to_tiktok(user:User,upload_request:VideoUpLoadRequest)->str:
    try:
        access_token = await check_and_refresh_tiktok_credentials(user)
        print("access_token", access_token)
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
        creator_info = await check_creator_info(access_token)
        print ("Creator info: ", creator_info)
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        post_info ={
            "title": upload_request.title,
            "privacy_level":"SELF_ONLY",
            "disable_duet":creator_info.get("duet_disabled", False),
            "disable_comment": creator_info.get("comment_disabled", False),
            "disable_stitch": creator_info.get("stitch_disabled", False),
            "video_cover_timestamp_ms":1000
        }
        video_size = len(video_stream.getvalue())
        chunk_size = min(10485760, video_size)
        total_chunk_count = math.ceil(video_size / chunk_size)  # 10 MB per chunk
        
        source_info ={
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunk_count
        }
        init_data ={
            "post_info": post_info,
            "source_info": source_info
        }
        print("Init data: ", init_data)
        headers ={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(init_url, json=init_data, headers=headers)
            print("Response: ",response.status_code, response.text)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to initialize TikTok video upload: {response.text}"
            )
        result = response.json()
        print ("Debug result ",result)
        
        if result.get("error", {}).get("code") != "ok":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to initialize TikTok video upload: {result.get('error', {}).get('message', 'Unknown error')}"
            )
        publish_id = result["data"]["publish_id"]
        upload_url = result["data"]["upload_url"]
        video_stream.seek(0)
        bytes_sent = 0
        chunk_number = 0
        async with httpx.AsyncClient() as client:
            while bytes_sent < video_size:
                chunk_data = video_stream.read(chunk_size)
                chunk_len = len(chunk_data)
                start_byte = bytes_sent
                end_byte = bytes_sent + chunk_len - 1
                upload_headers = {
                    "Content-Type": "video/mp4",
                    "Content-Length": str(chunk_len),
                    "Content-Range": f"bytes {start_byte}-{end_byte}/{video_size}"
                }
                upload_reponse = await client.put(
                    upload_url,
                    content=chunk_data,
                    headers=upload_headers
                )
                if upload_reponse.status_code not in [200, 201, 202]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to upload video chunk {chunk_number + 1}: {upload_reponse.text}"
                    )
                bytes_sent += chunk_len
                chunk_number += 1
        return "No link available for TikTok uploads, video uploaded successfully."
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to upload video to TikTok: {str(e)}"
        )
async def check_creator_info(access_token: str):
    url = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch creator info: {response.text}"
            )
        result = response.json()
        if result.get("error", {}).get("code") != "ok":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Creator info error: {result.get('error', {}).get('message', 'Unknown error')}"
            )
        return result["data"]  
