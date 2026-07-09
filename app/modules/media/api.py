from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from typing import Literal

from app.services.cloudinary_service import CloudinaryService
from app.modules.auth.deps import get_current_user
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/media", tags=["Media"])

class MediaUploadResponse(BaseModel):
    url: str

ALLOWED_FOLDERS = {
    "restaurant_covers",
    "restaurant_logos",
    "menu_items",
    "categories",
    "promos",
    "avatars",
    "restaurant_gallery",
}

@router.post("/upload", response_model=ApiResponse[MediaUploadResponse])
async def upload_media(
    file: UploadFile = File(...),
    folder_type: str = Form(...),
    current_user = Depends(get_current_user)
):
    if folder_type not in ALLOWED_FOLDERS:
        raise HTTPException(status_code=400, detail=f"Invalid folder_type. Must be one of {ALLOWED_FOLDERS}")
        
    try:
        url = await CloudinaryService.upload_image(file, folder_type)
        return ApiResponse(data=MediaUploadResponse(url=url), message="Upload successful")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
