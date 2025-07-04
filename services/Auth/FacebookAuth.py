from fastapi import HTTPException,status
from config import user_collection,app_config
from models import User
import requests
from typing import Dict, Any, Optional
from services import get_user_by_email
from .auth_utils import generate_username, generate_password
from core import hash_password
from bson import ObjectId

FACEBOOK_APP_ID =app_config.FACEBOOK_APP_ID
FACEBOOK_APP_SECRET= app_config.FACEBOOK_APP_SECRET
FACEBOOK_REDIRECT_URI= app_config.FACEBOOK_REDIRECT_URI
FACEBOOK_SCOPES=[
    "email",
    "public_profile",
    "pages_manage_posts",
    "pages_read_engagement",
    "publish_video",
    "pages_show_list"
]
collection = user_collection()
async def get_facebook_oauth_url():
    base_url = "https://www.facebook.com/v23.0/dialog/oauth"
    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "scope":",".join(FACEBOOK_SCOPES),
        "response_type": "code",
        "state": "facebook_auth"
    }
    url =f"{base_url}?" +"&".join([f"{key}={value}" for key, value in params.items()])
    return url
async def handle_facebook_oauth_callback(code: str)->User:
    try:
        token_url = "https://graph.facebook.com/v23.0/oauth/access_token"
        token_params={
            "client_id": FACEBOOK_APP_ID,
            "redirect_uri": FACEBOOK_REDIRECT_URI,
            "client_secret": FACEBOOK_APP_SECRET,
            "code": code
        }
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error fetching access token: {token_data['error']['message']}"
            )
        access_token = token_data.get("access_token")
        user_info_url = "https://graph.facebook.com/v23.0/me"
        user_info_params = {
            "fields": "name,email,picture",
            "access_token": access_token
        }
        user_response = requests.get(user_info_url, params=user_info_params)
        user_data = user_response.json()
        if "error" in user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error fetching user info: {user_data['error']['message']}"
            )
        long_lived_token = await get_long_lived_token(access_token)
        user = await process_facebook_user(user_data, long_lived_token)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Facebook OAuth callback failed: {str(e)}"
        )

async def get_long_lived_token(short_token:str)->str:
    url ="https://graph.facebook.com/v23.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": FACEBOOK_APP_ID,
        "client_secret": FACEBOOK_APP_SECRET,
        "fb_exchange_token": short_token
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "error" in data:
        return short_token
    return data["access_token"]

async def process_facebook_user(user:Dict[str,Any],access_token:str)->User:
    email = user.get("email")
    name = user.get("name")
    avatar = user.get("picture", {}).get("data", {}).get("url")
    facebook_id = user.get("id")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not provided by Facebook"
        )
    pages = await get_user_pages(access_token)
    facebook_platform_data = {
        "access_token": access_token,
        "facebook_id": facebook_id,
        "pages": pages
    }
    existing_user =await get_user_by_email(email)
    if existing_user:
        social_credentials = existing_user.social_credentials or {}
        social_credentials["facebook"] = facebook_platform_data
        
        update_data = {
            "social_credentials": social_credentials,
            "type": "facebook" 
        }
        
        await collection.update_one(
            {"_id": existing_user.id},
            {"$set": update_data}
        )
        existing_user.social_credentials = social_credentials
        return existing_user
    else:
        username = await generate_username(email)
        password = generate_password()
        new_user={
            "username": username,
            "email": email,
            "fullName": name,
            "avatar": avatar,
            "type": "facebook", 
            "password": hash_password(password),  
            "social_credentials": {
                "facebook": facebook_platform_data
            }
        }
        result = await collection.insert_one(new_user)
        created_user = await collection.find_one({"_id": result.inserted_id})
        if created_user:
            return User(**created_user)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server error while creating user"
            )


async def get_user_pages(access_token:str)->list:
    url= "https://graph.facebook.com/v23.0/me/accounts"
    params={
        "access_token": access_token,
        "fields": "id,name,access_token"
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "error" in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching user pages: {data['error']['message']}"
        )
    return data.get("data", [])

async def check_facebook_credentials(user: User) -> str:
    if not user.social_credentials or 'facebook' not in user.social_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have Facebook credentials"
        )
    facebook_data = user.social_credentials['facebook']
    access_token = facebook_data.get("access_token")
    debug_url = "https://graph.facebook.com/v23.0/debug_token"
    params = {
        "input_token": access_token,
        "access_token": f"{FACEBOOK_APP_ID}|{FACEBOOK_APP_SECRET}"
    }
    response = requests.get(debug_url, params=params)
    valid_data = response.json()
    if "error" in valid_data or not valid_data.get("data", {}).get("is_valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Facebook credentials are invalid or expired. Please re-authenticate."
        )
    return access_token

async def handle_facebook_callback(code: str, current_user: Optional[User] = None) -> User:
    try:
        # print(f"[DEBUG] Facebook callback - current_user: {current_user.username if current_user else 'None'}")
        # print(f"[DEBUG] Facebook callback - is linking: {current_user is not None}")
        
        token_url = "https://graph.facebook.com/v23.0/oauth/access_token"
        token_params = {
            "client_id": FACEBOOK_APP_ID,
            "redirect_uri": FACEBOOK_REDIRECT_URI,
            "client_secret": FACEBOOK_APP_SECRET,
            "code": code
        }
        token_response = requests.get(token_url, params=token_params)
        token_data = token_response.json()
        
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error fetching access token: {token_data['error']['message']}"
            )
        
        access_token = token_data.get("access_token")
        
        # Get user info
        user_info_url = "https://graph.facebook.com/v23.0/me"
        user_info_params = {
            "fields": "name,email,picture,id",
            "access_token": access_token
        }
        user_response = requests.get(user_info_url, params=user_info_params)
        user_data = user_response.json()
        
        if "error" in user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error fetching user info: {user_data['error']['message']}"
            )
        
        email = user_data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not returned by Facebook")
        long_lived_token = await get_long_lived_token(access_token)
        pages = await get_user_pages(long_lived_token)
        
        facebook_data = {
            "access_token": long_lived_token,
            "facebook_id": user_data.get("id"),
            "pages": pages,
            "email": email,
            "avatar": user_data.get("picture", {}).get("data", {}).get("url")
        }
        
        if current_user:
            # User is already logged in and wants to link Facebook account
            #print(f"[DEBUG] Linking Facebook to user: {current_user.username}")
            
            # Check if this Facebook email already exists in the system
            existing_user = await get_user_by_email(email)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(
                    status_code=400,
                    detail="Facebook email is already linked to another account."
                )
            
            # Check if this Facebook account is already linked via social_credentials
            existing_facebook_user = await collection.find_one({
                "social_credentials.facebook.email": email,
                "_id": {"$ne": ObjectId(current_user.id) if isinstance(current_user.id, str) else current_user.id}
            })
            if existing_facebook_user:
                raise HTTPException(
                    status_code=400,
                    detail="Facebook account is already linked to another user."
                )
            
            # Link Facebook to current user without changing type
            social_credentials = current_user.social_credentials or {}
            social_credentials["facebook"] = facebook_data
            
            user_id = ObjectId(current_user.id) if isinstance(current_user.id, str) else current_user.id
            
            # print(f"[DEBUG] Updating user {user_id} with Facebook credentials")
            result = await collection.update_one(
                {"_id": user_id},
                {"$set": {"social_credentials": social_credentials}}
            )
            # print(f"[DEBUG] Update result: {result.modified_count} documents modified")
            
            current_user.social_credentials = social_credentials
            return current_user
        else:
            # User is logging in via Facebook
            existing_user = await get_user_by_email(email)
            if existing_user:
                # Update existing user with Facebook credentials and set type to "facebook"
                social_credentials = existing_user.social_credentials or {}
                social_credentials["facebook"] = facebook_data
                
                update_data = {
                    "social_credentials": social_credentials,
                    "type": "facebook"
                }
                
                user_object_id = ObjectId(existing_user.id) if isinstance(existing_user.id, str) else existing_user.id
                
                await collection.update_one(
                    {"_id": user_object_id},
                    {"$set": update_data}
                )
                existing_user.social_credentials = social_credentials
                return existing_user
            else:
                # Create new user
                username = await generate_username(email)
                new_user = {
                    "username": username,
                    "email": email,
                    "fullName": user_data.get("name"),
                    "avatar": user_data.get("picture", {}).get("data", {}).get("url"),
                    "type": "facebook",  
                    "password": hash_password(generate_password()),
                    "social_credentials": {
                        "facebook": facebook_data
                    }
                }
                result = await collection.insert_one(new_user)
                created_user = await collection.find_one({"_id": result.inserted_id})
                user = User(**created_user)
                return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Facebook OAuth callback failed: {str(e)}"
        )

