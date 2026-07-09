import os
import uuid
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv

# Load variables from .env into os.environ
load_dotenv()

class CloudinaryService:
    @staticmethod
    def _configure_cloudinary():
        try:
            import cloudinary
            import cloudinary.uploader
        except ModuleNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail="Cloudinary dependency is not installed on the server.",
            ) from exc

        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        if not all([cloud_name, api_key, api_secret]):
            raise HTTPException(
                status_code=500,
                detail="Cloudinary is not configured on the server.",
            )

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )
        return cloudinary.uploader

    @staticmethod
    async def upload_image(file: UploadFile, folder_name: str) -> str:
        """
        Uploads an image to Cloudinary in the Yummydoors/{folder_name} directory.
        Returns the public secure URL.
        """
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        uploader = CloudinaryService._configure_cloudinary()

        # Determine the full folder path (e.g., Yummydoors/promos)
        base_folder = os.getenv("CLOUDINARY_DEFAULT_FOLDER", "Yummydoors")
        full_folder_path = f"{base_folder}/{folder_name}"

        try:
            from PIL import Image
            import io

            # Read file contents
            contents = await file.read()
            
            # Open image with Pillow
            img = Image.open(io.BytesIO(contents))
            
            # Convert to RGB if it's RGBA or P to avoid issues when saving as JPEG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            # Resize if dimensions are too large (e.g. max 2048x2048)
            img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            
            # Save compressed image to BytesIO
            img_byte_arr = io.BytesIO()
            # 85 is a good balance between quality and file size
            img.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
            img_byte_arr.seek(0)
            
            # Use original name with .jpg extension for the public_id
            original_name = (file.filename or "upload").rsplit('.', 1)[0]
            unique_filename = f"{uuid.uuid4().hex[:8]}_{original_name.replace(' ', '_')}"

            # Cloudinary reliably creates subfolders if they are part of the public_id
            full_public_id = f"{full_folder_path}/{unique_filename}"

            response = uploader.upload(
                img_byte_arr,
                public_id=full_public_id,
                resource_type="image",
                format="jpg",
            )
            return response.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")
