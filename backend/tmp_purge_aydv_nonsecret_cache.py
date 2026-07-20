from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "aydv_vigilantes_nonsecret_mapping.json"
ENV_CANDIDATES = [
    ROOT / ".env_imagekit copy",
    ROOT / ".env_imagekit",
    ROOT.parent / ".env_imagekit copy",
    ROOT.parent / ".env_imagekit",
]
PURGE_ENDPOINT = "https://api.imagekit.io/v1/files/purge"
STATUS_ENDPOINT = "https://api.imagekit.io/v1/files/purge/{request_id}"


def load_private_key(env_file: Path) -> str:
    data = env_file.read_text(encoding="utf-8", errors="ignore")
    for line in data.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == "private_key":
            return v.strip().strip('"').strip("'")
    raise RuntimeError("private_key no encontrado en .env_imagekit copy")


def resolve_env_file() -> Path:
    for candidate in ENV_CANDIDATES:
        if candidate.exists():
            return candidate
    raise RuntimeError("No se encontro .env_imagekit(. copy) en rutas esperadas")


def main() -> int:
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    urls = sorted({str(v).strip() for v in mapping.values() if str(v).strip()})
    urls = [u for u in urls if "ik.imagekit.io" in (urlparse(u).netloc or "").lower()]

    env_file = resolve_env_file()
    private_key = load_private_key(env_file)
    auth = (private_key, "")

    print(f"ENV_FILE={env_file}")
    print(f"TOTAL_URLS={len(urls)}")

    queued: list[tuple[str, str]] = []
    failed = 0

    for idx, url in enumerate(urls, start=1):
        try:
            resp = requests.post(
                PURGE_ENDPOINT,
                auth=auth,
                json={"url": url},
                timeout=30,
            )
            if resp.status_code >= 400:
                failed += 1
                print(f"[{idx}/{len(urls)}] FAIL queue status={resp.status_code} url={url}")
                continue
            payload = resp.json()
            request_id = str(payload.get("requestId") or "")
            if not request_id:
                failed += 1
                print(f"[{idx}/{len(urls)}] FAIL queue no-requestId url={url}")
                continue
            queued.append((url, request_id))
            print(f"[{idx}/{len(urls)}] QUEUED request_id={request_id}")
        except Exception as exc:
            failed += 1
            print(f"[{idx}/{len(urls)}] FAIL queue exc={exc}")

    print(f"QUEUED_OK={len(queued)} QUEUE_FAIL={failed}")

    # One-pass status check (without waits)
    done = 0
    pending = 0
    status_fail = 0

    for idx, (_url, request_id) in enumerate(queued, start=1):
        try:
            resp = requests.get(STATUS_ENDPOINT.format(request_id=request_id), auth=auth, timeout=30)
            if resp.status_code >= 400:
                status_fail += 1
                print(f"[status {idx}/{len(queued)}] FAIL status={resp.status_code} request_id={request_id}")
                continue
            payload = resp.json()
            status = str(payload.get("status") or "")
            if status.lower() == "completed":
                done += 1
            else:
                pending += 1
            print(f"[status {idx}/{len(queued)}] {status} request_id={request_id}")
        except Exception as exc:
            status_fail += 1
            print(f"[status {idx}/{len(queued)}] FAIL exc={exc} request_id={request_id}")

    print(f"STATUS_COMPLETED={done} STATUS_PENDING={pending} STATUS_FAIL={status_fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
