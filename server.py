#python -m fastapi dev .\server.py
#python -m uvicorn main:api --reload
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from api.routes.media_generation import router as media_generation_router
from api.routes.auth import router as auth_router
from api.routes.social import router as social_router
from api.routes.media import router as media_router
from api.routes.trending import router as trending_router
from api.routes.voice import router as voice_router
from api.routes.background import router as background_router
from api.routes.subtitle import router as subtitle_router
from api.routes.video import router as video_router
from api.routes.facebook_pages import router as facebook_pages_router
from api.routes.video_export import router as video_export_router
import uvicorn
import time
import logging
from contextlib import asynccontextmanager
from config import test_connection
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app:FastAPI):
    await test_connection()
    yield

api = FastAPI(
    title="Media Processing API",
    description="API for processing media files with AI",
    version="1.0.0",
    lifespan=lifespan, 
)

@api.middleware("http")
async def log_request_size(request: Request, call_next):
    start_time = time.time()
    content_length = request.headers.get("content-length", "0")
    
    if int(content_length) > 0:
        size_mb = int(content_length) / (1024 * 1024)
        logger.info(f"Request size: {size_mb:.2f} MB for {request.method} {request.url.path}")
    
    response = await call_next(request)
    process_time = time.time() - start_time
    
    if int(content_length) > 1024 * 1024:  # Log for requests > 1MB
        logger.info(f"Large request processed in {process_time:.2f}s")
    
    return response

# Add CORS middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=['Content-Type', 'Authorization'],
)

# Include routers
api.include_router(media_generation_router)
api.include_router(auth_router)
api.include_router(media_router)
api.include_router(social_router)
api.include_router(trending_router)
api.include_router(voice_router)
api.include_router(background_router)
api.include_router(subtitle_router)
api.include_router(video_router)
api.include_router(facebook_pages_router)
api.include_router(video_export_router)

# Request logging middleware với check file size
@api.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Check content length for upload requests
    if request.method == "POST" and request.url.path.startswith("/api/video/upload"):
        content_length = request.headers.get("content-length")
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > 10:  # 10MB limit
                logger.warning(f"Large upload detected: {size_mb:.2f}MB to {request.url.path}")
            else:
                logger.info(f"Upload size: {size_mb:.2f}MB to {request.url.path}")
    
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response
@api.get("/")
def index():
    return {
        "app": "Media Processing API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    uvicorn.run(
        "server:api", 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        # Increase limits for video uploads
        limit_max_requests=1000,
        limit_concurrency=100,
        timeout_keep_alive=30
    )
    
