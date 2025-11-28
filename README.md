# AI Short Video Creator - Backend

## 📋 Project Description

A comprehensive backend API for an AI-powered short video creation platform built with FastAPI and Python. This system leverages multiple AI services (Google Gemini, DeepSeek, Together AI, OpenRouter) to automatically generate professional short-form videos from text prompts, complete with AI-generated visuals, voice narration, subtitles, and seamless social media integration.

## 🚀 Key Features

### AI-Powered Content Generation

- **Text Generation**: AI-powered script generation with Wikipedia integration for factual accuracy
- **Text-to-Image**: Generate custom images using Flux and Gemini models
- **Multiple Art Styles**: Support for 15+ styles (Ghibli, watercolor, manga, realistic, cartoon, etc.)
- **Text-to-Speech**: 30+ premium voice options from Gemini API
- **Smart Content**: Context-aware content generation with source attribution

### Video Creation & Processing

- **Single & Multi-Scene Videos**: Create videos with one or multiple background images
- **Automatic Subtitles**: AI-powered transcription and subtitle generation
- **Customizable Styles**: Multiple subtitle styles and positioning options
- **Scene Transitions**: Configurable transition effects and durations
- **Flexible Inputs**: Support for custom backgrounds, audio, and scripts

### Trending Topics Integration

- **Real-Time Trends**: Discover trending topics across categories
- **Smart Search**: Category-based filtering and autocomplete
- **Topic Suggestions**: AI-powered content ideas
- **Popularity Ranking**: Trend score calculation and sorting

### Social Media Integration

- **Multi-Platform Publishing**: Direct upload to Facebook, TikTok, and YouTube
- **Facebook Pages**: Manage and publish to multiple Facebook pages
- **Analytics Dashboard**: Track views, reactions, comments, and shares
- **OAuth Authentication**: Secure social media account linking

### Media Management

- **Cloud Storage**: Cloudinary integration for reliable media hosting
- **User Organization**: User-based media library and collections
- **Type Validation**: Automatic media type detection and validation
- **Download & Preview**: Media download and streaming capabilities

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.115+
- **Runtime**: Python 3.12+
- **Database**: MongoDB with Motor (async driver)
- **Authentication**: JWT with python-jose, OAuth 2.0
- **Cloud Storage**: Cloudinary
- **AI Services**:
  - Google Gemini (text, image, TTS)
  - DeepSeek (text generation)
  - Together AI (Flux image generation)
  - OpenRouter, Groq (alternative text models)
- **Video Processing**: FFmpeg, imageio-ffmpeg
- **Email**: SMTP with email-validator
- **Task Scheduling**: schedule library for trending topics
- **Development**: Uvicorn, python-dotenv

## 📁 Project Structure

```
Software-Design-BE/
├── api/
│   ├── routes/              # API endpoints
│   │   ├── auth.py          # Authentication & user management
│   │   ├── media.py         # Media resource management
│   │   ├── media_generation.py  # AI content generation
│   │   ├── video.py         # Video creation & processing
│   │   ├── social.py        # Social media integration
│   │   ├── trending.py      # Trending topics API
│   │   ├── voice.py         # Voice & TTS management
│   │   ├── background.py    # Background images
│   │   ├── subtitle.py      # Subtitle processing
│   │   ├── facebook_pages.py    # Facebook page management
│   │   └── video_export.py  # Video export & sharing
│   └── deps.py              # Dependency injection
├── config/                  # Configuration files
│   ├── mongodb_config.py    # Database connection
│   ├── cloudinary_config.py # Cloud storage setup
│   └── app_config.py        # Application settings
├── core/
│   └── security.py          # Security utilities
├── models/                  # Database models
│   ├── user.py              # User schema
│   ├── media.py             # Media schema
│   ├── video.py             # Video schema
│   ├── social.py            # Social integration schema
│   └── trending_topic.py    # Trending topic schema
├── schemas/                 # Pydantic request/response schemas
│   ├── user.py
│   ├── media.py
│   ├── social.py
│   ├── subtitle.py
│   ├── voice.py
│   └── trending_topic.py
├── services/                # Business logic layer
│   ├── Auth/                # Authentication services
│   │   ├── FacebookAuth.py
│   │   ├── GoogleAuth.py
│   │   └── TikTokAuth.py
│   ├── Media/               # Media processing services
│   │   ├── text_generation.py
│   │   ├── text_to_image.py
│   │   ├── text_to_speech.py
│   │   ├── speech_to_text.py
│   │   ├── media_utils.py
│   │   └── wikipedia_service.py
│   ├── SocialNetwork/       # Social media services
│   │   ├── Facebook.py
│   │   ├── TikTok.py
│   │   └── Youtube.py
│   ├── trending_topics.py   # Trending topic logic
│   ├── voice_service.py     # Voice management
│   └── subtitle_service.py  # Subtitle generation
├── scheduler/               # Background tasks
│   └── trending_scheduler.py
├── temp/                    # Temporary file storage
├── server.py                # FastAPI application entry point
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```

## 🔧 Installation

1. **Clone the repository**

```bash
git clone https://github.com/DucToan137/ai-short-video-creator-be.git
cd ai-short-video-creator-be
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
   Create a `.env` file in the root directory:

```env
# MongoDB
MONGODB_URI=your_mongodb_connection_string
DATABASE_NAME=your_database_name

# Authentication
AUTH_SECRET_KEY=your_auth_secret_key

# Cloudinary (Media Storage)
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret

# AI Service Keys
OPENROUTER_KEY=your_openrouter_key
CAMB_KEY=your_camb_key
TOGETHER_KEY=your_together_key
GROQ_KEY=your_groq_key
GEMINI_KEY=your_gemini_key

# OAuth (Social Login)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/user/google/callback

FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_app_secret
FACEBOOK_REDIRECT_URI=http://localhost:8000/user/facebook/callback

# Application
FRONTEND_URL=http://localhost:3000
```

4. **Start the server**

```bash
# Development mode with auto-reload
python -m fastapi dev server.py

# or with Uvicorn
python -m uvicorn server:api --reload

# Production mode
python server.py
```

The API will run at `http://localhost:8000`

## 📚 API Endpoints

### Authentication Routes (`/user`)

- `POST /user/register` - User registration
- `POST /user/login` - User login (email/password)
- `GET /user/google/login` - Google OAuth login
- `GET /user/google/callback` - Google OAuth callback
- `GET /user/facebook/login` - Facebook OAuth login
- `GET /user/facebook/callback` - Facebook OAuth callback
- `GET /user/profile` - Get current user profile
- `PUT /user/profile` - Update user profile

### Media Generation Routes (`/media`)

- `POST /media/generate-text` - Generate text with AI (DeepSeek/Gemini)
- `POST /media/tts` - Convert text to speech
- `POST /media/generate-image` - Generate images with AI (Flux/Gemini)
- `POST /media/transcribe` - Transcribe audio to text/SRT
- `POST /media/create-video` - Create video from image and audio

### Video Routes (`/api/video`)

- `POST /api/video/create-complete` - Create complete video from script
- `POST /api/video/create-from-components` - Create video from existing media
- `GET /api/video/download/{video_id}` - Download video file
- `GET /api/video/preview/{video_id}` - Get video preview URL
- `GET /api/video/validate-media/{media_id}` - Validate media type

### Media Management Routes (`/api/media`)

- `GET /api/media` - List user's media files
- `POST /api/media/upload` - Upload media file
- `GET /api/media/{media_id}` - Get media details
- `DELETE /api/media/{media_id}` - Delete media file
- `GET /api/media/filter` - Filter media by type

### Trending Topics Routes (`/api/trending`)

- `GET /api/trending` - Get trending topics (paginated)
- `GET /api/trending/search` - Search trending topics
- `GET /api/trending/categories` - Get available categories
- `GET /api/trending/suggest` - Get topic suggestions
- `POST /api/trending` - Create trending topic (admin)
- `PUT /api/trending/{topic_id}` - Update trending topic (admin)
- `DELETE /api/trending/{topic_id}` - Delete trending topic (admin)

### Voice Routes (`/api/voice`)

- `GET /api/voice/list` - List available voices
- `GET /api/voice/{voice_id}` - Get voice details

### Background Routes (`/api/background`)

- `GET /api/background` - List background images
- `POST /api/background/upload` - Upload background image
- `GET /api/background/categories` - Get background categories

### Subtitle Routes (`/api/subtitle`)

- `POST /api/subtitle/generate` - Generate subtitles from audio
- `POST /api/subtitle/add-to-video` - Add subtitles to video
- `GET /api/subtitle/styles` - Get available subtitle styles

### Social Media Routes (`/api/social`)

- `POST /api/social/facebook/upload` - Upload video to Facebook
- `POST /api/social/tiktok/upload` - Upload video to TikTok
- `POST /api/social/youtube/upload` - Upload video to YouTube
- `GET /api/social/{platform}/stats/{video_id}` - Get video statistics

### Facebook Pages Routes (`/api/facebook-pages`)

- `GET /api/facebook-pages` - List user's Facebook pages
- `GET /api/facebook-pages/{page_id}` - Get page details

### Video Export Routes (`/api/export`)

- `POST /api/export/publish` - Publish video to multiple platforms
- `GET /api/export/status/{export_id}` - Get export status

## 🔐 API Documentation

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🎨 Supported Features

### Image Styles

Ghibli, Watercolor, Manga, Pixar, Sci-Fi, Oil Painting, Dark, LEGO, Realistic, Cartoon, Vintage, Minimalist, Fantasy, Pop Art, Impressionist

### Voice Options

30+ voices including: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Aoede, and more

### Subtitle Styles

Multiple customizable subtitle styles with position and appearance options

### Video Settings

- Configurable scene duration (min/max)
- Transition effects and duration
- Custom dimensions (720x1280 default)
- Multi-scene support

## 🗄️ Database Models

- **User**: User accounts with social credentials
- **Media**: Media files (images, audio, video)
- **Video**: Generated videos with metadata
- **TrendingTopic**: Trending content topics
- **Social**: Social media integration data

## 🔒 Security Features

- JWT-based authentication
- OAuth 2.0 integration (Google, Facebook)
- Password hashing with bcrypt
- CORS configuration
- Request size validation
- User-based access control

## 📄 License

This project is licensed under the MIT License.
