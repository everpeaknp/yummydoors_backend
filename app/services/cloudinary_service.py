import os
import uuid
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv

from app.services.cloudinary_folders import cloudinary_client_folder, normalize_client_scope

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
    async def upload_image(file: UploadFile, folder_name: str, client_scope: str = "desktop") -> str:
        """
        Uploads an image to Cloudinary in the Yummydoors/{client_scope}/{folder_name} directory.
        Returns the public secure URL.
        """
        uploader = CloudinaryService._configure_cloudinary()
        normalized_scope = normalize_client_scope(client_scope)

        # Keep uploads grouped under a root folder and a client-specific branch.
        full_folder_path = cloudinary_client_folder(normalized_scope, folder_name)

        try:
            from PIL import Image
            import io

            # Read file contents
            contents = await file.read()
            
            # Open image with Pillow
            img = Image.open(io.BytesIO(contents))
            img.verify()
            img = Image.open(io.BytesIO(contents))
            
            # Remove the JPEG RGB conversion and save as WEBP to preserve transparency
            # Resize if dimensions are too large (e.g. max 2048x2048)
            img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            
            # Save compressed image to BytesIO as WEBP (supports transparency + compression)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='WEBP', quality=85, method=6)
            img_byte_arr.seek(0)
            
            # Use original name with .webp extension for the public_id
            original_name = (file.filename or "upload").rsplit('.', 1)[0]
            unique_filename = f"{uuid.uuid4().hex[:8]}_{original_name.replace(' ', '_')}"

            response = uploader.upload(
                img_byte_arr,
                folder=full_folder_path,
                public_id=unique_filename,
                resource_type="image",
                format="webp",
            )
            return response.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")
