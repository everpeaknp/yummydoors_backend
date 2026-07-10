from __future__ import annotations


def normalize_avatar_url(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    for prefix in ("https://https://", "http://http://", "https://http://", "http://https://"):
        while cleaned.startswith(prefix):
            cleaned = f"{prefix.split('://', 1)[0]}://{cleaned[len(prefix):]}"

    return cleaned
