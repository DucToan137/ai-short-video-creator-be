from fastapi import APIRouter,HTTPException,Form,Response,Request,Depends,status,File,UploadFile
from fastapi.responses import RedirectResponse
from models import User
from schemas import UserResponse, UserCreate, UserLogin, UserUpdate, ChangePassword, Token
from api.deps import get_current_user
from services import create_user,authenticate_user,\
    get_google_oauth_url,handle_google_oauth_callback,\
    get_facebook_oauth_url,handle_facebook_oauth_callback
from services.Auth.User import update_user, change_password
from core import create_access_token,create_refresh_token,verify_token
from config import app_config
from config.cloudinary_config import cloudinary_config
import cloudinary.uploader

router = APIRouter(prefix="/user", tags=["Authentication"])
ACCESS_TOKEN_EXPIRE_MINUTES = app_config.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = app_config.REFRESH_TOKEN_EXPIRE_DAYS
FRONTEND_URL = app_config.FRONTEND_URL
@router.post("/register",response_model=UserResponse)
async def register_user(user: UserCreate):
    try:
        new_user = await create_user(user)
        new_user_response = new_user.model_dump(exclude={"password"})
        return UserResponse(
            **new_user_response
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the user: {str(e)}"
        )
@router.post("/login",response_model=Token)
async def login_user(response:Response,user_client: UserLogin):
    try:
        user = await authenticate_user(user_client)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
                
            )
        access_token =create_access_token(data={"sub":user.username,"id":user.id})
        refresh_token =create_refresh_token(data={"sub":user.username,"id":user.id})
        response.set_cookie(
            key= "refresh_token",
            value=refresh_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # days to seconds
            httponly=True,
            samesite="Strict",
            secure=False
        )
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
          )  
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login: {str(e)}"
        )
@router.get("/google/auth")
async def google_auth():
    try:
        auth_url =await get_google_oauth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while getting Google OAuth URL: {str(e)}"
        )
@router.get("/google/callback")
async def google_callback(code: str,response:Response):
    try: 
        user =await handle_google_oauth_callback(code)
        access_token =create_access_token(data={"sub":user.username,"id":user.id})
        refresh_token =create_refresh_token(data={"sub":user.username,"id":user.id})
        response.set_cookie(
            key= "refresh_token",
            value=refresh_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # days to seconds
            httponly=True,
            samesite="Strict",
            secure=False
        )
        frontend_url = f"{FRONTEND_URL}#access_token={access_token}"
        return RedirectResponse(
            url=frontend_url
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the user: {str(e)}"
        )
@router.get("/facebook/auth")
async def facebook_auth():
    try:
        auth_url= await get_facebook_oauth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while getting Facebook OAuth URL: {str(e)}"
        )
@router.get("/facebook/callback")
async def facebook_callback(code:str,response:Response):
    try:
        user = await handle_facebook_oauth_callback(code)
        access_token = create_access_token(data={"sub": user.username, "id": user.id})
        refresh_token = create_refresh_token(data={"sub": user.username, "id": user.id})
        response.set_cookie(
            key= "refresh_token",
            value=refresh_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # days to seconds
            httponly=True,
            samesite="Strict",
            secure=False
        )
        frontend_url = f"{FRONTEND_URL}#access_token={access_token}"
        return RedirectResponse(
            url=frontend_url
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the user: {str(e)}"
        )
@router.post("/logout")
async def logout_user(response: Response):
    try:
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            samesite="Strict",
            secure=False
        )
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while logging out: {str(e)}"
        )
    
@router.post("/refresh", response_model=Token)
async def refresh_token(request:Request):
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found"
            )
        payload = verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("id")
        username = payload.get("sub")
        if not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        new_access_token = create_access_token(data={"sub": username, "id": user_id})
        return Token(
           access_token=new_access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while logging out: {str(e)}"
        )
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.model_dump(exclude={"password"}))

@router.put("/update", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)):
    updated_user = await update_user(current_user.id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    try:
        result = cloudinary.uploader.upload(
            file.file,
            folder="avatars",
            public_id=f"user_{current_user.id}",
            overwrite=True,
            resource_type="image"
        )
        return {"url": result["secure_url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
@router.post("/change-password")
async def change_password_endpoint(
    req: ChangePassword,
    current_user: User = Depends(get_current_user)
):
    await change_password(current_user.id, req.current_password, req.new_password)
    return {"message": "Password changed successfully"}