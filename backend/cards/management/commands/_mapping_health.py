import requests
from django.core.management.base import CommandError


def _probe_status(url: str, timeout: int) -> tuple[int | None, str | None]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        status = response.status_code
        if status < 400 and status != 405:
            return status, None

        # Some CDNs reject HEAD; verify with a lightweight GET.
        response = requests.get(url, allow_redirects=True, timeout=timeout, stream=True)
        status = response.status_code
        response.close()
        return status, None
    except requests.RequestException as exc:
        return None, str(exc)


def validate_mapping_urls(
    mapping: dict,
    command,
    label: str,
    *,
    skip_check: bool = False,
    timeout: int = 10,
    max_reported_failures: int = 8,
) -> None:
    if skip_check:
        command.stdout.write(
            command.style.WARNING(f"Skipping URL health check for {label}.")
        )
        return

    if not mapping:
        raise CommandError(
            f"{label}: mapping is empty. Provide/upload valid image URLs first."
        )

    failures = []
    for cloudinary_id, raw_url in mapping.items():
        url = (raw_url or "").strip()
        if not url:
            failures.append((cloudinary_id, "", None, "missing url"))
            continue

        status, err = _probe_status(url, timeout=timeout)
        if err is not None or status is None or status >= 400:
            failures.append((cloudinary_id, url, status, err))

    if failures:
        command.stderr.write(
            command.style.ERROR(
                f"{label}: {len(failures)}/{len(mapping)} URLs failed health checks."
            )
        )
        for cloudinary_id, url, status, err in failures[:max_reported_failures]:
            detail = err or f"HTTP {status}"
            command.stderr.write(f"  - {cloudinary_id}: {detail} ({url})")

        raise CommandError(
            f"{label}: mapping has inaccessible URLs. Fix mapping/upload source or use --skip-url-check explicitly."
        )

    command.stdout.write(
        command.style.SUCCESS(
            f"{label}: validated {len(mapping)} image URLs successfully."
        )
    )
