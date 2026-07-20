import base64
import os
from urllib.parse import urlparse

import requests


def _safe_name(raw: str, fallback: str = "asset") -> str:
    clean = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in (raw or "").strip())
    clean = clean.strip("_")
    return clean[:120] if clean else fallback


def upload_image_url_to_imagekit(source_url: str, imagekit_private_key: str, imagekit_url_endpoint: str, folder: str, file_name: str) -> str:
    api_url = "https://upload.imagekit.io/api/v1/files/upload"
    auth_raw = f"{imagekit_private_key}:".encode("utf-8")
    auth_header = base64.b64encode(auth_raw).decode("ascii")

    payload = {
        "file": source_url,
        "fileName": _safe_name(file_name),
        "folder": folder,
        "useUniqueFileName": "false",
        "overwriteFile": "true",
        "overwriteAITags": "true",
        "overwriteTags": "true",
        "overwriteCustomMetadata": "true",
    }

    response = requests.post(
        api_url,
        data=payload,
        headers={"Authorization": f"Basic {auth_header}"},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    url = body.get("url")
    if not url:
        raise ValueError("ImageKit no devolvió URL")
    return url


def host_from_url(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
