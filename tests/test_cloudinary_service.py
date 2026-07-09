import pytest
from fastapi import UploadFile

from app.services.cloudinary_service import CloudinaryService


class _UploaderStub:
    def __init__(self) -> None:
        self.calls = []

    def upload(self, content, **kwargs):
        self.calls.append((content, kwargs))
        return {"secure_url": "https://cdn.example.com/banner.jpg"}


@pytest.mark.asyncio
async def test_upload_image_uses_returned_uploader_module(monkeypatch):
    uploader = _UploaderStub()
    monkeypatch.setattr(CloudinaryService, "_configure_cloudinary", lambda: uploader)

    upload = UploadFile(
        filename="banner.png",
        file=None,
        headers={"content-type": "image/png"},
    )
    # 1x1 transparent GIF
    valid_gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    upload.file = __import__("io").BytesIO(valid_gif)

    result = await CloudinaryService.upload_image(upload, "promos")

    assert result == "https://cdn.example.com/banner.jpg"
    assert len(uploader.calls) == 1
    assert uploader.calls[0][1]["resource_type"] == "image"
