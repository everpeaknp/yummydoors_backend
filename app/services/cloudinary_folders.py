from __future__ import annotations

import os

DEFAULT_CLOUDINARY_ROOT = "Yummydoors"


def get_cloudinary_root() -> str:
    configured = (os.getenv("CLOUDINARY_DEFAULT_FOLDER") or "").strip()
    root = configured.strip().strip("/") if configured else DEFAULT_CLOUDINARY_ROOT
    return root or DEFAULT_CLOUDINARY_ROOT


def cloudinary_folder(*segments: str) -> str:
    parts = [get_cloudinary_root()]
    for segment in segments:
        cleaned = str(segment).strip().strip("/")
        if cleaned:
            parts.append(cleaned)
    return "/".join(parts)


def cloudinary_client_folder(client_scope: str, *segments: str) -> str:
    # Keep the helper for compatibility, but foldering is now entity-based only.
    return cloudinary_folder(*segments)


def cloudinary_desktop_folder(*segments: str) -> str:
    return cloudinary_folder(*segments)


def cloudinary_mobile_folder(*segments: str) -> str:
    return cloudinary_folder(*segments)


def cloudinary_web_folder(*segments: str) -> str:
    return cloudinary_folder(*segments)
