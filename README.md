# AI Short Video Creator - Backend

Phần backend của hệ thống AI Short Video Creator, cung cấp API để xử lý và tạo video ngắn tự động bằng AI.

## Cài đặt và khởi chạy

- Chạy lệnh sau để cài đặt các thư viện cần thiết
```
pip install -r requirements.txt
```
- Chạy lệnh sau để khởi tạo server
```
python -m fastapi dev .\server.py
```
hoặc
```
python -m uvicorn server:api --reload
```
- Truy cập http://127.0.0.1:8000/docs để thử API
- Cần có file .env chứa các API_KEY để có thể chạy được hệ thống (xem phần "Cấu hình file .env" phía dưới)

## Cấu trúc hệ thống

- `server.py`: File chính khởi chạy FastAPI server với các cấu hình CORS và middleware
- `api/routes/`: Chứa các API endpoint phân theo chức năng:
  - `auth.py`: Xác thực và quản lý người dùng
  - `media.py`: Quản lý media (hình ảnh, âm thanh)
  - `media_generation.py`: Tạo media bằng AI
  - `social.py`: Tích hợp mạng xã hội
  - `trending.py`: API lấy chủ đề trending
  - `voice.py`: Xử lý giọng nói và text-to-speech
  - `background.py`: Quản lý hình nền
  - `subtitle.py`: Xử lý phụ đề
  - `video.py`: Quản lý video
  - `facebook_pages.py`: Tích hợp với Facebook
  - `video_export.py`: Xuất và chia sẻ video

- `config/`: Cấu hình hệ thống
  - `mongodb_config.py`: Kết nối MongoDB
  - `cloudinary_config.py`: Cấu hình Cloudinary để lưu trữ media
  - `app_config.py`: Cấu hình ứng dụng

- `models/`: Định nghĩa cấu trúc dữ liệu
  - `user.py`: Model người dùng
  - `media.py`: Model cho media
  - `video.py`: Model cho video
  - `social.py`: Model cho tích hợp mạng xã hội
  - `trending_topic.py`: Model cho chủ đề trending

- `services/`: Các dịch vụ xử lý logic nghiệp vụ
  - Xử lý media, video, text-to-speech, AI generation, v.v.

## Yêu cầu hệ thống

- Python 3.12+ 
- MongoDB
- Tài khoản Cloudinary (lưu trữ media)
- API keys cho các dịch vụ AI (cấu hình trong file .env)

## Cấu hình file .env

Tạo file .env trong thư mục gốc với các biến môi trường sau:
```
# MongoDB
MONGODB_URI=your_mongodb_connection_string
DATABASE_NAME=your_database_name

# Xác thực
AUTH_SECRET_KEY=your_auth_secret_key

# Cloudinary configs (lưu trữ ảnh và video)
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret

# AI Service Keys
OPENROUTER_KEY=your_openrouter_key
CAMB_KEY=your_camb_key
TOGETHER_KEY=your_together_key
GROQ_KEY=your_groq_key
GEMINI_KEY=your_gemini_key

# OAuth (Đăng nhập với Google, Facebook)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/user/google/callback

FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_app_secret
FACEBOOK_REDIRECT_URI=http://localhost:8000/user/facebook/callback

# URL
FRONTEND_URL=http://localhost:3000
```

## Các API chính

API được phân chia theo chức năng và có thể được xem chi tiết tại `/docs` endpoint sau khi khởi chạy server.

- `/api/auth`: Xác thực và quản lý người dùng
- `/api/media`: Quản lý tài nguyên media
- `/api/trending`: Lấy chủ đề trending
- `/api/video`: Tạo và quản lý video
- `/api/social`: Tích hợp mạng xã hội