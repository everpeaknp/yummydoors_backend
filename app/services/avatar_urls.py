from __future__ import annotations


def normalize_avatar_url(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    while True:
        updated = False
        for prefix in ("https://", "http://"):
            double_prefix = f"{prefix}{prefix}"
            mixed_prefix = f"{prefix}{'http://' if prefix == 'https://' else 'https://'}"
            if cleaned.startswith(double_prefix) or cleaned.startswith(mixed_prefix):
                cleaned = cleaned[len(prefix):]
                updated = True
                break
        if not updated:
            break

    return cleaned
