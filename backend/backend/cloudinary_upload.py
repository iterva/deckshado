import hashlib
import os
import time
from typing import BinaryIO
from urllib.parse import unquote, urlparse

import requests


class CloudinaryUploadError(Exception):
    """Raised when uploading an image to Cloudinary fails."""



def _resolve_cloudinary_credentials() -> tuple[str, str, str]:
    cloud_name = (os.environ.get("CLOUDINARY_CLOUD_NAME") or "").strip()
    api_key = (os.environ.get("CLOUDINARY_API_KEY") or "").strip()
    api_secret = (os.environ.get("CLOUDINARY_API_SECRET") or "").strip()

    cloudinary_url = (os.environ.get("CLOUDINARY_URL") or "").strip()
    if cloudinary_url and (not cloud_name or not api_key or not api_secret):
        parsed = urlparse(cloudinary_url)
        if parsed.scheme == "cloudinary":
            if not api_key:
                api_key = unquote(parsed.username or "").strip()
            if not api_secret:
                api_secret = unquote(parsed.password or "").strip()
            if not cloud_name:
                cloud_name = (parsed.hostname or parsed.path.strip("/"))

    # Keep a safe default cloud name for legacy environments that only store API key/secret.
    if not cloud_name:
        cloud_name = "drw7y27sm"

    if not api_key or not api_secret:
        raise CloudinaryUploadError(
            "Cloudinary no esta configurado en el servidor (faltan CLOUDINARY_API_KEY/CLOUDINARY_API_SECRET)."
        )

    return cloud_name, api_key, api_secret



def _build_signature(params: dict[str, str], api_secret: str) -> str:
    normalized = {k: str(v) for k, v in params.items() if v not in (None, "")}
    payload = "&".join(f"{k}={normalized[k]}" for k in sorted(normalized.keys()))
    return hashlib.sha1(f"{payload}{api_secret}".encode("utf-8")).hexdigest()



def upload_image_to_cloudinary(
    file_obj: BinaryIO,
    *,
    folder: str,
) -> str:
    cloud_name, api_key, api_secret = _resolve_cloudinary_credentials()
    timestamp = str(int(time.time()))
    sign_params = {
        "folder": folder,
        "timestamp": timestamp,
    }
    signature = _build_signature(sign_params, api_secret)

    filename = getattr(file_obj, "name", "upload.jpg")
    content_type = getattr(file_obj, "content_type", "application/octet-stream")

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    data = {
        "api_key": api_key,
        "timestamp": timestamp,
        "folder": folder,
        "signature": signature,
    }

    try:
        response = requests.post(
            url,
            data=data,
            files={"file": (filename, file_obj, content_type)},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise CloudinaryUploadError(f"Error al conectar con Cloudinary: {exc}") from exc

    payload = {}
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400:
        detail = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
        raise CloudinaryUploadError(detail or "Cloudinary rechazo la subida de la imagen.")

    secure_url = (payload.get("secure_url") or "").strip() if isinstance(payload, dict) else ""
    if not secure_url:
        raise CloudinaryUploadError("Cloudinary no devolvio secure_url para la imagen subida.")
    return secure_url
