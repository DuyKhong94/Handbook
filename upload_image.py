import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

# ⚙️ Cấu hình Cloudinary
cloudinary.config( 
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET"),
    secure=True
)

def upload_image_to_cloudinary(file_path):
    try:
        response = cloudinary.uploader.upload(
            file_path,
            resource_type="auto",   # Cho phép PDF, ảnh, video...
            folder="handbook_reports",  # Tạo thư mục riêng trên Cloudinary
            type="upload"            # Đặt công khai để tải được
        )
        return response.get("secure_url")
    except Exception as e:
        print("❌ Lỗi upload Cloudinary:", e)
        return None