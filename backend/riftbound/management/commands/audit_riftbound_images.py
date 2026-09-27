"""
Audita las imágenes de las cartas Riftbound sin asumir dónde están alojadas
(ImageKit de cualquier cuenta, Cloudinary, CDN oficial, piltoverarchive...).

Para cada carta activa revisa las URLs que ya tiene guardadas
(`cdn_image_url`, `image_url`, `image_url_small`) y las clasifica:

  ok       -> responde 2xx
  missing  -> responde 404 o 410 (el archivo no existe)
  unknown  -> cualquier otra cosa (403, 405, 5xx, timeout...): NO se toca

Con `--fix` solo vacía `cdn_image_url` cuando es `missing` Y la carta tiene otra
URL `ok` a la que caer. Nunca inventa ni reescribe URLs hacia otro host, así que
no pisa cartas que ya se sirven desde Cloudinary u otra cuenta de ImageKit.

Siempre escribe un CSV con el detalle para revisarlo.

Uso:
    python manage.py audit_riftbound_images --csv imagenes.csv
    python manage.py audit_riftbound_images --set OGN --csv imagenes.csv
    python manage.py audit_riftbound_images --fix --csv imagenes.csv
"""
import csv
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand

from riftbound.models import RiftboundCard

MISSING_STATUSES = {404, 410}
URL_FIELDS = ("cdn_image_url", "image_url", "image_url_small")


def check_url(session: requests.Session, url: str, timeout: int) -> str:
    """Devuelve 'ok', 'missing' o 'unknown:<detalle>'."""
    try:
        resp = session.head(url, timeout=timeout, allow_redirects=True)
        status = resp.status_code
        # Algunos CDN no aceptan HEAD: confirmar con un GET de 1 byte.
        if status not in MISSING_STATUSES and not 200 <= status < 300:
            resp = session.get(url, timeout=timeout, allow_redirects=True, stream=True,
                               headers={"Range": "bytes=0-0"})
            status = resp.status_code
            resp.close()
    except requests.RequestException as exc:
        return f"unknown:{type(exc).__name__}"
    if 200 <= status < 300:
        return "ok"
    if status in MISSING_STATUSES:
        return "missing"
    return f"unknown:{status}"


def host_of(url: str) -> str:
    parsed = urlparse(url)
    first_segment = parsed.path.strip("/").split("/")[0] if parsed.path else ""
    # ImageKit usa el primer segmento como id de cuenta: distinguir cuentas.
    return f"{parsed.netloc}/{first_segment}" if "imagekit.io" in parsed.netloc else parsed.netloc


class Command(BaseCommand):
    help = "Revisa las URLs de imagen guardadas de cada carta Riftbound (cualquier host)."

    def add_arguments(self, parser):
        parser.add_argument("--set", default="", help="Filtrar por código de set (ej: OGN).")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--workers", type=int, default=16)
        parser.add_argument("--timeout", type=int, default=10)
        parser.add_argument("--csv", default="riftbound_images_audit.csv")
        parser.add_argument(
            "--fix", action="store_true",
            help="Vaciar cdn_image_url cuando da 404/410 y hay otra URL que sí funciona.",
        )

    def handle(self, *args, **opts):
        qs = RiftboundCard.objects.filter(is_active=True).select_related("set").order_by("card_number")
        if opts["set"]:
            qs = qs.filter(set__code=opts["set"].strip().upper())
        cards = list(qs[: opts["limit"]] if opts["limit"] else qs)

        urls = {getattr(c, f).strip() for c in cards for f in URL_FIELDS if (getattr(c, f) or "").strip()}
        self.stdout.write(f"{len(cards)} cartas, {len(urls)} URLs distintas a revisar...")

        session = requests.Session()
        session.headers["User-Agent"] = "deckshado-riftbound-image-audit/1.0"
        timeout = max(3, opts["timeout"])
        url_list = sorted(urls)
        with ThreadPoolExecutor(max_workers=max(1, opts["workers"])) as pool:
            results = dict(zip(url_list, pool.map(lambda u: check_url(session, u, timeout), url_list)))

        rows, to_clear = [], []
        by_host = Counter()
        for card in cards:
            status = {}
            for field in URL_FIELDS:
                url = (getattr(card, field) or "").strip()
                status[field] = results[url] if url else ""
                if url:
                    by_host[(host_of(url), results[url].split(":")[0])] += 1

            has_working_fallback = any(status[f] == "ok" for f in URL_FIELDS if f != "cdn_image_url")
            action = ""
            if status["cdn_image_url"] == "missing":
                action = "vaciar_cdn" if has_working_fallback else "sin_respaldo"
                if has_working_fallback:
                    to_clear.append(card)
            elif not any(s == "ok" for s in status.values()):
                action = "sin_imagen_funcional"

            if action or any(s and s != "ok" for s in status.values()):
                rows.append([
                    card.card_number, card.name, action,
                    card.cdn_image_url, status["cdn_image_url"],
                    card.image_url, status["image_url"],
                    card.image_url_small, status["image_url_small"],
                ])

        with open(opts["csv"], "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "card_number", "name", "accion",
                "cdn_image_url", "estado_cdn", "image_url", "estado_image_url",
                "image_url_small", "estado_image_url_small",
            ])
            writer.writerows(rows)

        self.stdout.write("\nEstado por host:")
        for (host, state), count in sorted(by_host.items()):
            self.stdout.write(f"  {host:45} {state:8} {count}")

        actions = Counter(r[2] for r in rows if r[2])
        self.stdout.write(f"\nAcciones: {dict(actions)} · CSV: {opts['csv']}")

        if not opts["fix"]:
            self.stdout.write(self.style.WARNING("Solo auditoría (usa --fix para vaciar las cdn_image_url rotas)."))
            return

        for card in to_clear:
            RiftboundCard.objects.filter(pk=card.pk).update(cdn_image_url="")
        self.stdout.write(self.style.SUCCESS(f"{len(to_clear)} cdn_image_url vaciadas."))
