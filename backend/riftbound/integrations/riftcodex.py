from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator

import requests
from django.utils import timezone
from django.utils.dateparse import parse_datetime


TYPE_MAP: dict[str, str] = {
    "Unit": "unit",
    "Spell": "spell",
    "Gear": "gear",
    "Legend": "legend",
    "Rune": "rune",
    "Battlefield": "battlefield",
    "Champion": "champion",
}


RARITY_MAP: dict[str, str] = {
    "Common": "common",
    "Uncommon": "uncommon",
    "Rare": "rare",
    "Epic": "epic",
    "Legendary": "legendary",
    "Champion": "champion",
    "Promo": "promo",
    # El modelo local no tiene showcase, por lo que cae a "other".
    "Showcase": "other",
}


ALLOWED_INDEX_TYPES: tuple[str, ...] = (
    "keywords",
    "card-names",
    "card-types",
    "card-supertypes",
    "domains",
    "rarities",
    "artists",
    "energy",
    "might",
    "power",
    "tags",
)


@dataclass(slots=True)
class RiftcodexPage:
    items: list[dict[str, Any]]
    page: int
    pages: int
    size: int
    total: int


class RiftcodexClient:
    """Cliente HTTP reutilizable para api.riftcodex.com."""

    def __init__(
        self,
        base_url: str = "https://api.riftcodex.com",
        timeout: int = 30,
        max_retries: int = 3,
        backoff_seconds: float = 0.6,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                res = self.session.get(url, params=params, timeout=self.timeout)
                if res.status_code >= 500:
                    raise requests.HTTPError(f"{res.status_code} en {url}")
                res.raise_for_status()
                data = res.json()
                if not isinstance(data, dict):
                    raise ValueError("La respuesta JSON no es un objeto")
                return data
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    break
                time.sleep(self.backoff_seconds * attempt)

        raise RuntimeError(f"Error consultando Riftcodex {url}: {last_exc}")

    def fetch_cards_page(self, page: int = 1, size: int = 100) -> RiftcodexPage:
        data = self._request_json("/cards", params={"page": page, "size": size})
        items = data.get("items") or []
        if not isinstance(items, list):
            items = []

        return RiftcodexPage(
            items=items,
            page=int(data.get("page") or page),
            pages=max(1, int(data.get("pages") or 1)),
            size=int(data.get("size") or size),
            total=int(data.get("total") or len(items)),
        )

    def fetch_index(self, index_type: str) -> dict[str, Any]:
        """Obtiene un indice desde /index/<type>."""
        if index_type not in ALLOWED_INDEX_TYPES:
            raise ValueError(f"Indice no soportado: {index_type}")

        data = self._request_json(f"/index/{index_type}")
        values = data.get("values")
        if not isinstance(values, list):
            values = []

        return {
            "type": str(data.get("type") or index_type),
            "total": int(data.get("total") or len(values)),
            "values": values,
        }

    def search_cards(
        self,
        query: str,
        set_id: str | None = None,
        size: int = 25,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Busqueda fulltext remota en /cards/search (WIP en Riftcodex)."""
        params: dict[str, Any] = {
            "query": query,
            "size": max(1, min(100, size)),
            "page": max(1, page),
        }
        if set_id:
            params["set_id"] = set_id
        data = self._request_json("/cards/search", params=params)
        items = data.get("items") or []
        return [x for x in items if isinstance(x, dict)]

    def search_cards_by_name(
        self,
        fuzzy: str | None = None,
        exact: str | None = None,
        set_id: str | None = None,
        size: int = 25,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Busqueda por nombre en /cards/name usando fuzzy o exact."""
        if not fuzzy and not exact:
            return []

        params: dict[str, Any] = {
            "size": max(1, min(100, size)),
            "page": max(1, page),
        }
        if fuzzy:
            params["fuzzy"] = fuzzy
        if exact:
            params["exact"] = exact
        if set_id:
            params["set_id"] = set_id

        data = self._request_json("/cards/name", params=params)
        items = data.get("items") or []
        return [x for x in items if isinstance(x, dict)]

    def iter_all_cards(self, size: int = 100, request_pause_seconds: float = 0.0) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            payload = self.fetch_cards_page(page=page, size=size)
            for item in payload.items:
                if isinstance(item, dict):
                    yield item

            if payload.page >= payload.pages:
                break

            page += 1
            if request_pause_seconds > 0:
                time.sleep(request_pause_seconds)


def parse_riftcodex_updated_on(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = parse_datetime(value)
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone=timezone.utc)
    return dt


def normalize_riftbound_card_number(riftbound_id: str, signature: bool = False) -> str:
    """
    Convierte riftbound_id (ej: unl-060a-219) al formato local (UNL-060a).
    Si es signature card agrega sufijo *.
    """
    value = (riftbound_id or "").strip()
    if not value:
        return ""

    parts = value.split("-")
    if len(parts) >= 2:
        normalized = f"{parts[0].upper()}-{parts[1]}"
    else:
        normalized = value.upper()

    if signature:
        normalized += "*"
    return normalized


def map_card_type(value: str | None) -> str:
    return TYPE_MAP.get(value or "", "other")


def map_card_rarity(value: str | None) -> str:
    return RARITY_MAP.get(value or "", "other")
