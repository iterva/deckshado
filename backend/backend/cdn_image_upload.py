import os
import re
from typing import BinaryIO

import requests

from .cloudinary_upload import CloudinaryUploadError, upload_image_to_cloudinary


class CdnImageUploadError(Exception):
    """Raised when uploading an image to the configured CDN fails."""


def _provider() -> str:
    return (os.environ.get("CDN_PROVIDER") or "imagekit").strip().lower()


def _split_csv_env(name: str) -> list[str]:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _collect_imagekit_private_keys() -> list[str]:
    csv_keys = _split_csv_env("IMAGEKIT_PRIVATE_KEYS")
    if csv_keys:
        return csv_keys

    keys: list[str] = []
    primary = (os.environ.get("IMAGEKIT_PRIVATE_KEY") or "").strip()
    if primary:
        keys.append(primary)

    idx = 2
    while idx <= 10:
        key = (os.environ.get(f"IMAGEKIT_PRIVATE_KEY_{idx}") or "").strip()
        if key:
            keys.append(key)
        idx += 1

    if not keys:
        raise CdnImageUploadError(
            "ImageKit no esta configurado en el servidor (faltan IMAGEKIT_PRIVATE_KEY/IMAGEKIT_PRIVATE_KEYS)."
        )

    return keys


def _sanitize_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value or "")
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "file"


def _sanitize_folder(folder: str) -> str:
    parts = [part for part in (folder or "").split("/") if part]
    safe_parts = [_sanitize_part(part) for part in parts]
    return "/".join(safe_parts)


def _sanitize_filename(filename: str) -> str:
    raw_name = (filename or "upload.jpg").strip()
    if "." in raw_name:
        base, ext = raw_name.rsplit(".", 1)
        ext = ext.strip().lower() or "jpg"
    else:
        base, ext = raw_name, "jpg"
    return f"{_sanitize_part(base)}.{ext}"


def _upload_image_to_imagekit(file_obj: BinaryIO, *, folder: str) -> str:
    filename = _sanitize_filename(getattr(file_obj, "name", "upload.jpg"))
    content_type = getattr(file_obj, "content_type", "application/octet-stream")
    safe_folder = _sanitize_folder(folder)
    keys = _collect_imagekit_private_keys()

    data = {
        "fileName": filename,
        "folder": f"/{safe_folder}" if safe_folder else "/",
        "useUniqueFileName": "false",
        "overwriteFile": "true",
    }

    last_error: Exception | None = None
    for idx, private_key in enumerate(keys, 1):
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        try:
            response = requests.post(
                "https://upload.imagekit.io/api/v1/files/upload",
                auth=(private_key, ""),
                data=data,
                files={"file": (filename, file_obj, content_type)},
                timeout=30,
            )
        except requests.RequestException as exc:
            last_error = CdnImageUploadError(f"Error al conectar con ImageKit: {exc}")
            continue

        payload = {}
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code >= 300:
            detail = ""
            if isinstance(payload, dict):
                detail = str(payload.get("message") or payload.get("help") or "")
            if not detail:
                detail = (response.text or "").strip()[:300]
            message = detail or "ImageKit rechazo la subida de la imagen."

            has_next = idx < len(keys)
            if has_next and "upload limit exceeded" in message.lower():
                last_error = CdnImageUploadError(message)
                continue
            raise CdnImageUploadError(message)

        url = (payload.get("url") or "").strip() if isinstance(payload, dict) else ""
        if not url:
            raise CdnImageUploadError("ImageKit no devolvio URL para la imagen subida.")
        return url

    if last_error:
        raise last_error
    raise CdnImageUploadError("No fue posible subir la imagen a ImageKit.")


def upload_image_to_cdn(file_obj: BinaryIO, *, folder: str) -> str:
    provider = _provider()
    if provider == "imagekit":
        return _upload_image_to_imagekit(file_obj, folder=folder)
    if provider == "cloudinary":
        try:
            return upload_image_to_cloudinary(file_obj, folder=folder)
        except CloudinaryUploadError as exc:
            raise CdnImageUploadError(str(exc)) from exc
    raise CdnImageUploadError(f"CDN_PROVIDER no soportado para subida de imagenes: {provider}")