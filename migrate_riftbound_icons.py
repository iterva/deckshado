"""
Descarga los iconos de Riftbound desde cdn.piltoverarchive.com
y los sube a Cloudinary bajo `riftbound/icons/<kind>/<code>`.
Luego actualiza `RiftboundIcon.cdn_image_url` en la BD.

Uso:
    python migrate_riftbound_icons.py
"""
import io
import os
import sys
import django
import requests
import cloudinary
import cloudinary.uploader

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from riftbound.models import RiftboundIcon  # noqa: E402

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "dmvu6tuee"),
    api_key=os.environ.get("CLOUDINARY_API_KEY", "618467334728855"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", "egB_Ypv0wdVVBL2oRhUaoHr8bY8"),
    secure=True,
)


def slugify(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s).strip("_").lower()


def main():
    icons = list(RiftboundIcon.objects.all())
    print(f"[+] {len(icons)} iconos en BD")
    ok = 0
    skip = 0
    fail = 0
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 deckshado-icon-migrator/1.0",
    })

    for i, icon in enumerate(icons, 1):
        if icon.cdn_image_url:
            print(f"  [{i}/{len(icons)}] [{icon.kind}] {icon.code} ya tiene cdn, skip")
            skip += 1
            continue
        if not icon.image_url:
            print(f"  [{i}/{len(icons)}] [{icon.kind}] {icon.code} sin image_url, skip")
            skip += 1
            continue

        public_id = f"riftbound/icons/{icon.kind}/{slugify(icon.code)}"
        print(f"  [{i}/{len(icons)}] {icon.image_url} -> {public_id}", end=" ... ", flush=True)
        try:
            r = session.get(icon.image_url, timeout=20)
            r.raise_for_status()
            buf = io.BytesIO(r.content)
            buf.name = f"{slugify(icon.code)}.webp"
            result = cloudinary.uploader.upload(
                buf,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
            )
            cdn = result["secure_url"]
            icon.cdn_image_url = cdn
            icon.save(update_fields=["cdn_image_url"])
            print("OK")
            ok += 1
        except Exception as e:
            print(f"ERROR: {e}")
            fail += 1

    print(f"\n[OK] subidos={ok}  saltados={skip}  errores={fail}")


if __name__ == "__main__":
    main()
