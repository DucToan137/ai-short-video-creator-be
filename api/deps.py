from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from services import get_user_by_username
from models import User
from core import verify_token
from jose import JWTError
security = HTTPBearer()

async def get_current_user(credentials:HTTPAuthorizationCredentials =Depends(security))->User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(f"Verifying token: {credentials.credentials[:20]}...")
        payload = verify_token(credentials.credentials,"access")
        print(f"Token payload: {payload}")
        if payload is None:
            print("Token verification returned None")
            raise credentials_exception
        username = payload.get("sub")
        print(f"Username from token: {username}")
        if username is None:
            print("No username in token")
            raise credentials_exception
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception
    except Exception as e:
        print(f"Other error in token verification: {e}")
        raise credentials_exception
    user = await get_user_by_username(username)
    print(f"Found user: {user}")
    if user is None:
        print("User not found in database")
        raise credentials_exception
    return user

