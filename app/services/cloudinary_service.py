import os
import uuid
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv

# Load variables from .env into os.environ
load_dotenv()

# Initialize Cloudinary using environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

class CloudinaryService:
    @staticmethod
    async def upload_image(file: UploadFile, folder_name: str) -> str:
        """
        Uploads an image to Cloudinary in the Yummydoors/{folder_name} directory.
        Returns the public secure URL.
        """
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read file content safely
        content = await file.read()
        
        # Determine the full folder path (e.g., Yummydoors/promos)
        base_folder = os.getenv("CLOUDINARY_DEFAULT_FOLDER", "Yummydoors")
        full_folder_path = f"{base_folder}/{folder_name}"
        
        try:
            # Upload to cloudinary
            # We use a unique public_id to avoid overwriting files with the same original name
            unique_filename = f"{uuid.uuid4().hex[:8]}_{file.filename.replace(' ', '_')}"
            
            response = cloudinary.uploader.upload(
                content,
                folder=full_folder_path,
                public_id=unique_filename,
                resource_type="image"
            )
            return response.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")
