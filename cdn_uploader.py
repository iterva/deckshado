import os
import re
import threading
from typing import Iterable, Optional
from urllib.parse import quote

import requests


class CdnConfigError(RuntimeError):
    pass


_UPLOAD_GUARD_LOCK = threading.Lock()
_UPLOAD_CALLS = 0
_UPLOAD_BYTES = 0


def get_provider() -> str:
    # Default provider is Cloudinary (can be overridden with CDN_PROVIDER).
    return (os.environ.get("CDN_PROVIDER") or "cloudinary").strip().lower()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise CdnConfigError(f"Missing required environment variable: {name}")
    return value


def _env_is_truthy(name: str) -> bool:
    value = (os.environ.get(name) or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _parse_optional_positive_int_env(name: str) -> Optional[int]:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise CdnConfigError(f"Invalid integer in {name}: {raw}") from exc
    if value < 0:
        raise CdnConfigError(f"{name} must be >= 0")
    return value


def _enforce_upload_guard(next_upload_bytes: int) -> None:
    global _UPLOAD_CALLS, _UPLOAD_BYTES

    if _env_is_truthy("CDN_UPLOADS_DISABLED"):
        raise RuntimeError("CDN guard: uploads are disabled by CDN_UPLOADS_DISABLED")

    max_calls = _parse_optional_positive_int_env("CDN_MAX_UPLOAD_CALLS")
    max_bytes = _parse_optional_positive_int_env("CDN_MAX_UPLOAD_BYTES")

    with _UPLOAD_GUARD_LOCK:
        if max_calls is not None and _UPLOAD_CALLS >= max_calls:
            raise RuntimeError(
                f"CDN guard: max upload calls reached ({_UPLOAD_CALLS}/{max_calls})"
            )
        if max_bytes is not None and (_UPLOAD_BYTES + next_upload_bytes) > max_bytes:
            raise RuntimeError(
                "CDN guard: max upload bytes would be exceeded "
                f"({_UPLOAD_BYTES + next_upload_bytes}/{max_bytes})"
            )

        # Conservative accounting: reserve budget before uploading to avoid overage race conditions.
        _UPLOAD_CALLS += 1
        _UPLOAD_BYTES += max(0, int(next_upload_bytes))


def _split_public_id(public_id: str, default_ext: str) -> tuple[str, str]:
    clean = (public_id or "").strip("/")
    if not clean:
        raise ValueError("public_id is required")

    if "/" in clean:
        folder, name = clean.rsplit("/", 1)
    else:
        folder, name = "", clean

    if "." in name:
        filename = name
    else:
        filename = f"{name}.{default_ext.lstrip('.')}"

    return folder, filename


def _sanitize_imagekit_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value or "")
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "file"


def _sanitize_imagekit_folder(folder: str) -> str:
    parts = [p for p in (folder or "").split("/") if p]
    safe_parts = [_sanitize_imagekit_part(p) for p in parts]
    return "/".join(safe_parts)


def _sanitize_imagekit_filename(filename: str, default_ext: str) -> str:
    ext = default_ext.lstrip(".").lower() or "png"
    base = filename
    if "." in filename:
        base, maybe_ext = filename.rsplit(".", 1)
        if maybe_ext:
            ext = maybe_ext.lower()
    return f"{_sanitize_imagekit_part(base)}.{ext}"


def _split_csv_env(name: str) -> list[str]:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _collect_imagekit_accounts() -> list[tuple[str, str]]:
    """
    Returns [(private_key, url_endpoint), ...] for ImageKit accounts.

    Supported config modes:
    1) CSV lists (recommended for N accounts):
       IMAGEKIT_PRIVATE_KEYS=key1,key2
       IMAGEKIT_URL_ENDPOINTS=https://ik.imagekit.io/a,https://ik.imagekit.io/b
    2) Numbered variables:
       IMAGEKIT_PRIVATE_KEY / IMAGEKIT_URL_ENDPOINT
       IMAGEKIT_PRIVATE_KEY_2 / IMAGEKIT_URL_ENDPOINT_2
       IMAGEKIT_PRIVATE_KEY_3 / IMAGEKIT_URL_ENDPOINT_3
    """
    csv_keys = _split_csv_env("IMAGEKIT_PRIVATE_KEYS")
    csv_endpoints = _split_csv_env("IMAGEKIT_URL_ENDPOINTS")
    if csv_keys or csv_endpoints:
        if len(csv_keys) != len(csv_endpoints):
            raise CdnConfigError(
                "IMAGEKIT_PRIVATE_KEYS and IMAGEKIT_URL_ENDPOINTS must have the same number of entries"
            )
        if not csv_keys:
            raise CdnConfigError("IMAGEKIT_PRIVATE_KEYS / IMAGEKIT_URL_ENDPOINTS are empty")
        return [(k, e.rstrip("/")) for k, e in zip(csv_keys, csv_endpoints)]

    accounts: list[tuple[str, str]] = []

    primary_key = (os.environ.get("IMAGEKIT_PRIVATE_KEY") or "").strip()
    primary_endpoint = (os.environ.get("IMAGEKIT_URL_ENDPOINT") or "").strip()
    if primary_key or primary_endpoint:
        if not primary_key or not primary_endpoint:
            raise CdnConfigError(
                "Both IMAGEKIT_PRIVATE_KEY and IMAGEKIT_URL_ENDPOINT are required for primary ImageKit account"
            )
        accounts.append((primary_key, primary_endpoint.rstrip("/")))

    idx = 2
    while idx <= 10:
        key = (os.environ.get(f"IMAGEKIT_PRIVATE_KEY_{idx}") or "").strip()
        endpoint = (os.environ.get(f"IMAGEKIT_URL_ENDPOINT_{idx}") or "").strip()
        if key or endpoint:
            if not key or not endpoint:
                raise CdnConfigError(
                    f"Both IMAGEKIT_PRIVATE_KEY_{idx} and IMAGEKIT_URL_ENDPOINT_{idx} are required"
                )
            accounts.append((key, endpoint.rstrip("/")))
        idx += 1

    if not accounts:
        raise CdnConfigError(
            "Missing ImageKit credentials. Configure IMAGEKIT_PRIVATE_KEY + IMAGEKIT_URL_ENDPOINT "
            "or IMAGEKIT_PRIVATE_KEYS + IMAGEKIT_URL_ENDPOINTS"
        )

    return accounts


def _cloudinary_base_url() -> str:
    cloud_name = _require_env("CLOUDINARY_CLOUD_NAME")
    return f"https://res.cloudinary.com/{cloud_name}/image/upload"


def _imagekit_base_url() -> str:
    return _collect_imagekit_accounts()[0][1]


def _r2_public_base_url() -> str:
    base = (_require_env("R2_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if not base.startswith("http"):
        raise CdnConfigError("R2_PUBLIC_BASE_URL must be an absolute URL")
    return base


def _r2_s3_endpoint() -> str:
    account_id = _require_env("R2_ACCOUNT_ID").strip()
    return f"https://{account_id}.r2.cloudflarestorage.com"


def _normalize_r2_key(public_id: str, default_ext: str) -> str:
    clean = (public_id or "").strip("/")
    if not clean:
        raise ValueError("public_id is required")

    name = clean.rsplit("/", 1)[-1]
    if "." not in name:
        clean = f"{clean}.{default_ext.lstrip('.') or 'png'}"
    return clean


def build_public_url(public_id: str, extension: str) -> str:
    clean_id = (public_id or "").strip("/")
    ext = (extension or "").lstrip(".").lower()
    if not clean_id or not ext:
        raise ValueError("public_id and extension are required")

    if get_provider() == "r2":
        return f"{_r2_public_base_url()}/{clean_id}.{ext}"
    if get_provider() == "imagekit":
        return f"{_imagekit_base_url()}/{clean_id}.{ext}"
    return f"{_cloudinary_base_url()}/{clean_id}.{ext}"


def candidate_public_urls(public_id: str, extensions: Iterable[str]) -> list[str]:
    out = []
    clean_id = (public_id or "").strip("/")
    if not clean_id:
        return out

    if get_provider() == "imagekit":
        try:
            endpoints = [ep for _, ep in _collect_imagekit_accounts()]
        except Exception:
            endpoints = [_imagekit_base_url()]

        for endpoint in endpoints:
            for ext in extensions:
                ext_clean = (ext or "").lstrip(".").lower()
                if ext_clean:
                    out.append(f"{endpoint}/{clean_id}.{ext_clean}")
        return out

    if get_provider() == "r2":
        try:
            base = _r2_public_base_url()
        except Exception:
            return out

        for ext in extensions:
            ext_clean = (ext or "").lstrip(".").lower()
            if ext_clean:
                out.append(f"{base}/{clean_id}.{ext_clean}")
        return out

    for ext in extensions:
        try:
            out.append(build_public_url(public_id, ext))
        except Exception:
            continue
    return out


def upload_bytes(
    content: bytes,
    public_id: str,
    default_ext: str = "png",
    mime_type: Optional[str] = None,
    overwrite: bool = True,
) -> str:
    _enforce_upload_guard(len(content or b""))

    provider = get_provider()
    if provider == "r2":
        return _upload_r2_bytes(content, public_id, default_ext, mime_type)
    if provider == "imagekit":
        return _upload_imagekit_bytes(content, public_id, default_ext, mime_type, overwrite)
    if provider == "cloudinary":
        return _upload_cloudinary_bytes(content, public_id, overwrite)
    raise CdnConfigError(f"Unsupported CDN_PROVIDER: {provider}")


def upload_file(file_path: str, public_id: str, overwrite: bool = True) -> str:
    with open(file_path, "rb") as f:
        content = f.read()

    ext = os.path.splitext(file_path)[1].lstrip(".").lower() or "png"
    mime_type = None
    if ext == "png":
        mime_type = "image/png"
    elif ext in {"jpg", "jpeg"}:
        mime_type = "image/jpeg"
    elif ext == "webp":
        mime_type = "image/webp"

    return upload_bytes(
        content,
        public_id=public_id,
        default_ext=ext,
        mime_type=mime_type,
        overwrite=overwrite,
    )


def _upload_cloudinary_bytes(content: bytes, public_id: str, overwrite: bool) -> str:
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=_require_env("CLOUDINARY_CLOUD_NAME"),
        api_key=_require_env("CLOUDINARY_API_KEY"),
        api_secret=_require_env("CLOUDINARY_API_SECRET"),
        secure=True,
    )

    result = cloudinary.uploader.upload(
        content,
        public_id=public_id,
        overwrite=overwrite,
        resource_type="image",
    )
    return result["secure_url"]


def _upload_imagekit_bytes(
    content: bytes,
    public_id: str,
    default_ext: str,
    mime_type: Optional[str],
    overwrite: bool,
) -> str:
    accounts = _collect_imagekit_accounts()
    last_error: Exception | None = None

    for idx, (private_key, _endpoint) in enumerate(accounts, 1):
        try:
            return _upload_imagekit_bytes_single(
                content=content,
                public_id=public_id,
                default_ext=default_ext,
                mime_type=mime_type,
                overwrite=overwrite,
                private_key=private_key,
            )
        except Exception as exc:
            last_error = exc
            is_quota = "upload limit exceeded" in str(exc).lower()
            has_next = idx < len(accounts)
            if has_next and is_quota:
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError("ImageKit upload failed: no accounts configured")


def _upload_imagekit_bytes_single(
    content: bytes,
    public_id: str,
    default_ext: str,
    mime_type: Optional[str],
    overwrite: bool,
    private_key: str,
) -> str:
    folder, filename = _split_public_id(public_id, default_ext)
    folder = _sanitize_imagekit_folder(folder)
    filename = _sanitize_imagekit_filename(filename, default_ext)

    data = {
        "fileName": filename,
        "folder": f"/{folder}" if folder else "/",
        "useUniqueFileName": "false",
        "overwriteFile": "true" if overwrite else "false",
    }
    files = {
        "file": (filename, content, mime_type or "application/octet-stream"),
    }

    resp = requests.post(
        "https://upload.imagekit.io/api/v1/files/upload",
        auth=(private_key, ""),
        data=data,
        files=files,
        timeout=120,
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"ImageKit upload failed ({resp.status_code}): {resp.text[:300]}")

    body = resp.json()
    url = body.get("url")
    if not url:
        raise RuntimeError("ImageKit upload succeeded but no URL in response")
    return url


def _upload_r2_bytes(
    content: bytes,
    public_id: str,
    default_ext: str,
    mime_type: Optional[str],
) -> str:
    import boto3

    key = _normalize_r2_key(public_id, default_ext)
    bucket = _require_env("R2_BUCKET").strip()

    client = boto3.client(
        "s3",
        endpoint_url=_r2_s3_endpoint(),
        aws_access_key_id=_require_env("R2_ACCESS_KEY_ID").strip(),
        aws_secret_access_key=_require_env("R2_SECRET_ACCESS_KEY").strip(),
        region_name="auto",
    )

    put_kwargs = {
        "Bucket": bucket,
        "Key": key,
        "Body": content,
    }
    if mime_type:
        put_kwargs["ContentType"] = mime_type

    client.put_object(**put_kwargs)

    safe_key = quote(key, safe="/-_.~")
    return f"{_r2_public_base_url()}/{safe_key}"
