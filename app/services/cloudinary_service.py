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

        # Read file content safely
        content = await file.read()

        # Determine the full folder path (e.g., Yummydoors/promos)
        base_folder = os.getenv("CLOUDINARY_DEFAULT_FOLDER", "Yummydoors")
        full_folder_path = f"{base_folder}/{folder_name}"

        try:
            # Upload to cloudinary
            # We use a unique public_id to avoid overwriting files with the same original name
            original_name = file.filename or "upload"
            unique_filename = f"{uuid.uuid4().hex[:8]}_{original_name.replace(' ', '_')}"

            response = uploader.upload(
                content,
                folder=full_folder_path,
                public_id=unique_filename,
                resource_type="image",
            )
            return response.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")
