import asyncio
from app.services.cloudinary_service import CloudinaryService
from fastapi import UploadFile
import io
from starlette.datastructures import Headers

async def test_upload():
    with open('/home/ramon/projects/everacy/yummydoors_desktop/public/hero.png', 'rb') as f:
        file = UploadFile(filename='hero.png', file=f, headers=Headers({'content-type': 'image/png'}))
        url = await CloudinaryService.upload_image(file, 'categories')
        print('Upload URL:', url)

asyncio.run(test_upload())
