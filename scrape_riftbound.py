"""
Scraper de cartas Riftbound desde piltoverarchive.com (Next.js + RSC).

Cada página /cards?page=N renderiza 48 celdas. La data viaja como "RSC flight":
una secuencia de líneas `<id>:<value>` dentro de scripts `__next_f.push`.
Cada celda de carta es un valor que empieza con `["$","$L7a","<UUID>",{...}]`
y referencia 5 sub-chunks (`$LXX`) con stats, descripción, info, etc.

Uso:
    python scrape_riftbound.py --pages 1-21 --out riftbound_cards.json
    python scrape_riftbound.py --pages 1 -v
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

import requests

BASE = "https://piltoverarchive.com"
LIST_URL = BASE + "/cards"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

CHUNK_RE = re.compile(
    r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', re.DOTALL
)
LINE_RE = re.compile(r'^([0-9a-f]+):(.+)$', re.MULTILINE)
# El ID del componente de celda cambia entre deploys de piltoverarchive
# (antes $L7a, hoy $L46…). Aceptamos cualquier referencia $L<hex> seguida
# de un UUID y validamos después que la celda contenga una imagen de carta.
CARD_CELL_RE = re.compile(r'^\["\$","\$L[0-9a-f]+","([0-9a-f-]{36})",\{', re.DOTALL)
CARD_IMAGE_RE = re.compile(
    r'(?:cdn\.piltoverarchive\.com/(?:cards|temporary|missing)/|piltoverarchive\.b-cdn\.net/)'
)
COLOR_NAMES = ("Fury", "Calm", "Mind", "Body", "Chaos", "Order")


@dataclass
class CardData:
    card_number: str = ""
    external_id: str = ""
    name: str = ""
    set_code: str = ""
    set_name: str = ""
    variant: str = ""
    rarity: str = ""
    card_type: str = ""
    supertype: str = ""
    subtypes: list = field(default_factory=list)
    colors: list = field(default_factory=list)
    energy: int | None = None
    power: int | None = None
    might: int | None = None
    description: str = ""
    flavor: str = ""
    image_url: str = ""
    image_url_small: str = ""
    artist: str = ""
    source_url: str = ""


def fetch_page(page: int, session: requests.Session, retries: int = 3) -> str:
    url = f"{LIST_URL}?page={page}"
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = session.get(url, headers=DEFAULT_HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:  # noqa: BLE001
            last_exc = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"No pude descargar {url}: {last_exc}")


def collect_flight_text(html: str) -> str:
    parts = []
    for m in CHUNK_RE.finditer(html):
        try:
            decoded = json.loads('"' + m.group(1) + '"')
        except Exception:  # noqa: BLE001
            decoded = (
                m.group(1).replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
            )
        parts.append(decoded)
    # Importante: concatenamos SIN separador. Next.js puede partir un mismo
    # chunk (`<id>:<value>`) entre varios `__next_f.push` y un "\n" extra
    # cortaría el valor a la mitad para LINE_RE.
    return "".join(parts)


def index_chunks(flight: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in LINE_RE.finditer(flight):
        out[m.group(1)] = m.group(2)
    return out


def parse_int(s) -> int | None:
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


KEYWORD_IMG_RE = re.compile(
    r'"src":"https://cdn\.piltoverarchive\.com/(description_keywords|icons)/'
    r'([^."/]+)\.(?:svg|webp|png)"'
)


def clean_description(raw: str) -> str:
    """Convierte el JSX serializado en texto plano. Las imágenes inline de
    keywords/iconos quedan como tokens [TAG] (su `alt`)."""
    text = raw
    # 1) Cada componente <img kw-…>{ "src":"...", "alt":"[X]", ... } se reduce a [X]
    text = re.sub(
        r'\["?\$"?,\s*"img"[^]]*?"alt":"\[([^\]]+)\]"[^}]*\}\]',
        lambda m: f"[{m.group(1)}]",
        text, flags=re.DOTALL,
    )
    # 2) Componentes <i italic-N>{children:[...]} → conservar el contenido
    text = re.sub(r'\["?\$"?,\s*"i"[^]]*?"children":\[(.*?)\]\}\]', r"\1", text, flags=re.DOTALL)
    # 3) Quedan listas anidadas y strings JSON. Extraemos las cadenas literales
    #    (incluyendo \n) en orden y las concatenamos.
    pieces: list[str] = []
    # Iteramos pares "..."  y los valores [TAG] que acabamos de inyectar.
    # Estrategia simple: tokenize alterando entre strings y "[TAG]" tokens.
    pattern = re.compile(r'"((?:[^"\\]|\\.)*)"|\[([A-Z0-9_-]+)\]')
    for m in pattern.finditer(text):
        if m.group(1) is not None:
            s = m.group(1)
            # Filtra atributos JSX típicos
            if s in {
                "$", "img", "i", "p", "div", "span", "src", "alt", "width",
                "height", "loading", "eager", "style", "draggable",
                "verticalAlign", "middle", "display", "inline", "key",
                "className", "children", "1.5em", "auto", "object-cover",
                "object-contain", "false", "true",
            }:
                continue
            if s.startswith("kw-") or s.startswith("italic-"):
                continue
            if s.startswith("text-") or s.startswith("flex"):
                continue
            if re.match(r"^https?://", s):
                continue
            if s.startswith("$") or s.startswith("@"):
                continue
            pieces.append(s)
        else:
            pieces.append(f"[{m.group(2)}]")
    out = "".join(pieces)
    out = out.replace("\\n", "\n")
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def parse_info_chunk(text: str) -> dict:
    out: dict[str, str] = {}
    for m in re.finditer(
        r'"children":"([^"]+):"\s*\}\s*\][^\[]{0,300}?\["?\$"?,\s*"span"[^{]*?\{[^}]*?"children":"([^"]+)"',
        text, re.DOTALL,
    ):
        out[m.group(1).strip()] = m.group(2).strip()
    return out


def parse_stats_chunk(text: str) -> dict:
    out: dict[str, int | None] = {}
    for label in ("Energy", "Power", "Might"):
        m = re.search(
            rf'"children":"{label}"\s*\}}\s*\].*?"children":(\d+)',
            text, re.DOTALL,
        )
        if m:
            out[label.lower()] = parse_int(m.group(1))
    return out


def parse_color_and_rarity(text: str) -> tuple[list[str], str | None]:
    colors = sorted({
        c.lower() for c in re.findall(
            rf'"alt":"({"|".join(COLOR_NAMES)})"', text,
        )
    })
    rar = None
    rm = re.search(r'/rarities/([a-zA-Z_-]+)\.', text)
    if rm:
        rar = rm.group(1).lower()
    return colors, rar


SUBTYPE_BLACKLIST = {
    "Energy", "Power", "Might", "Description",
    "Card Information", "Set", "Variant", "Card Number", "Artist",
}


def parse_badges(text: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r'"children":"([^"]{1,40})"\}', text):
        v = m.group(1)
        if v in SUBTYPE_BLACKLIST or v.endswith(":"):
            continue
        if v.startswith("$") or v.startswith("https:"):
            continue
        if v in COLOR_NAMES:
            continue
        out.append(v)
    return out


def _balanced_slice(text: str, start: int) -> str:
    """Devuelve el slice de `text` desde `start` (que apunta a `[` o `{`)
    hasta el carácter de cierre balanceado, ignorando corchetes dentro de
    cadenas JSON. Se usa para extraer el cuerpo completo de una celda de
    carta que vive inline dentro de otro chunk (sin id propio)."""
    if start >= len(text) or text[start] not in "[{":
        return ""
    open_c = text[start]
    close_c = "]" if open_c == "[" else "}"
    depth = 0
    i = start
    in_str = False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == open_c:
                depth += 1
            elif ch == close_c:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1
    return text[start:]


CELL_SIGNATURE_RE = re.compile(
    r'\["\$","\$L[0-9a-f]+","([0-9a-f-]{36})",'
)


def iter_card_cells(flight: str):
    """Recorre el flight completo y entrega todas las celdas de carta,
    estén o no en su propio chunk de top-level. Cada celda es una tupla
    `(external_id, full_cell_value)`."""
    seen: set[str] = set()
    for m in CELL_SIGNATURE_RE.finditer(flight):
        uid = m.group(1)
        if uid in seen:
            continue
        cell = _balanced_slice(flight, m.start())
        if not cell:
            continue
        if not CARD_IMAGE_RE.search(cell):
            continue
        seen.add(uid)
        yield uid, cell


def extract_cards(flight: str, source_url: str, verbose: bool = False) -> list[CardData]:
    chunks = index_chunks(flight)
    cards: list[CardData] = []

    for uid, value in iter_card_cells(flight):
        c = CardData(external_id=uid, source_url=source_url)

        # Imagen + alt (nombre)
        im = re.search(
            r'"src":"(https://(?:cdn\.piltoverarchive\.com|piltoverarchive\.b-cdn\.net)/[^"]+\.(?:webp|png|jpg))"',
            value,
        )
        if im:
            c.image_url = im.group(1)
        nm = re.search(r'"alt":"([^"]+)"', value)
        if nm:
            c.name = nm.group(1)

        # Resolver referencias $LXX (depth 4): cada card cell apunta a chunks
        # de stats/desc/info y algunos referencian a su vez chunks atómicos
        # (rarity image). Profundizamos para alcanzar variantes showcase
        # cuyo "Card Number" vive bastante más profundo en el árbol.
        seen = set()
        ordered_refs: list[str] = []
        depth0 = re.findall(r'"\$L([0-9a-f]+)"', value)
        queue = list(depth0)
        depth = 0
        while queue and depth < 6:
            next_queue: list[str] = []
            for r in queue:
                if r in seen:
                    continue
                seen.add(r)
                ordered_refs.append(r)
                sub = chunks.get(r, "")
                if sub:
                    next_queue.extend(re.findall(r'"\$L([0-9a-f]+)"', sub))
            queue = next_queue
            depth += 1

        for ref in ordered_refs:
            sub = chunks.get(ref, "")
            if not sub:
                continue

            if '"children":"Energy"' in sub or '"children":"Might"' in sub:
                stats = parse_stats_chunk(sub)
                if "energy" in stats:
                    c.energy = stats["energy"]
                if "power" in stats:
                    c.power = stats["power"]
                if "might" in stats:
                    c.might = stats["might"]

            if "Card Number:" in sub:
                info = parse_info_chunk(sub)
                if (n := info.get("Card Number")):
                    c.card_number = n
                    if "-" in n and not c.set_code:
                        c.set_code = n.split("-")[0]
                if (s := info.get("Set")):
                    c.set_name = s
                if (v := info.get("Variant")):
                    c.variant = v
                if (a := info.get("Artist")):
                    c.artist = a

            if '"children":"Description"' in sub:
                dm = re.search(
                    r'whitespace-pre-line"\s*,\s*"children":(\[.+)',
                    sub, re.DOTALL,
                )
                if dm:
                    c.description = clean_description(dm.group(1))

            if "/colors/" in sub or "/rarities/" in sub:
                cols, rar = parse_color_and_rarity(sub)
                if cols:
                    c.colors = sorted(set(c.colors) | set(cols))
                if rar and not c.rarity:
                    c.rarity = rar

            # Badges genéricos (subtypes / tags)
            if (
                '"children":"' in sub
                and "/colors/" not in sub
                and "Card Number:" not in sub
                and '"children":"Energy"' not in sub
                and '"children":"Description"' not in sub
            ):
                badges = parse_badges(sub)
                if 1 <= len(badges) <= 6:
                    c.subtypes = list(dict.fromkeys((c.subtypes or []) + badges))

        infer_card_type(c)

        # Rarity / colores: vienen inline dentro de la propia celda (badges
        # del modal) en el deploy actual. Intentamos siempre con `value`.
        if not c.rarity or not c.colors:
            cols, rar = parse_color_and_rarity(value)
            if cols and not c.colors:
                c.colors = sorted(set(cols))
            if rar and not c.rarity:
                c.rarity = rar

        # Fallback: algunas celdas tienen el modal inline (sin refs $L
        # para Card Number/Description/Stats). Si todavía no tenemos
        # número de carta, extraemos lo que podamos directamente del
        # contenido de la celda.
        if not c.card_number:
            # 1) URL del CDN: /cards/<CODE>.webp -> CODE = card_number
            if c.image_url:
                im = re.search(r'/cards/([A-Z]{2,4}-\d{2,4}[A-Za-z0-9_-]*)\.', c.image_url)
                if im:
                    c.card_number = im.group(1)
                    c.set_code = c.card_number.split("-")[0]
            # 2) Bloque "Card Number:" inline en la propia celda
            if not c.card_number and "Card Number:" in value:
                info = parse_info_chunk(value)
                if (n := info.get("Card Number")):
                    c.card_number = n
                    if "-" in n and not c.set_code:
                        c.set_code = n.split("-")[0]
                if (s := info.get("Set")) and not c.set_name:
                    c.set_name = s
                if (v := info.get("Variant")) and not c.variant:
                    c.variant = v
                if (a := info.get("Artist")) and not c.artist:
                    c.artist = a

            # Si la URL es de "temporary/..." y aún no hay número, marcamos
            # como variante showcase con id provisional para no perderla.
            if not c.card_number and c.image_url and "/temporary/" in c.image_url:
                c.card_number = f"SHOWCASE-{c.external_id[:8]}"
                c.set_code = "SHOWCASE"
                c.variant = c.variant or "showcase"

            # Stats / descripción / colores inline (best effort)
            if "Card Number:" in value:
                if (c.energy is None or c.power is None or c.might is None):
                    stats = parse_stats_chunk(value)
                    if "energy" in stats and c.energy is None:
                        c.energy = stats["energy"]
                    if "power" in stats and c.power is None:
                        c.power = stats["power"]
                    if "might" in stats and c.might is None:
                        c.might = stats["might"]
                if not c.description:
                    dm = re.search(
                        r'whitespace-pre-line"\s*,\s*"children":(\[.+)',
                        value, re.DOTALL,
                    )
                    if dm:
                        c.description = clean_description(dm.group(1))
                if not c.colors or not c.rarity:
                    cols, rar = parse_color_and_rarity(value)
                    if cols and not c.colors:
                        c.colors = sorted(set(cols))
                    if rar and not c.rarity:
                        c.rarity = rar
            infer_card_type(c)

        cards.append(c)

    # Asignar un número de fallback a celdas que aún no tienen para no
    # perderlas (variantes especiales / overnumbered sin metadata visible).
    for c in cards:
        if not c.card_number:
            c.card_number = f"SHOWCASE-{c.external_id[:8]}"
            if not c.set_code:
                c.set_code = "SHOWCASE"
            if not c.variant:
                c.variant = "showcase"

    if verbose:
        with_num = sum(1 for c in cards if c.card_number)
        print(f"    cells={len(cards)} con_numero={with_num}", file=sys.stderr)

    return [c for c in cards if c.card_number]


TYPE_KEYWORDS = {
    "champion", "legend", "unit", "spell", "gear", "battlefield", "rune",
}


def infer_card_type(c: CardData) -> None:
    if c.card_type:
        return
    # Las runas reales son exactamente las 6 elementales. "Rune Prison" y otras
    # cartas que contienen "rune" en el nombre no son del tipo Rune.
    name_lower = (c.name or "").lower()
    rune_names = {"fury rune", "calm rune", "mind rune", "body rune", "chaos rune", "order rune"}
    if name_lower in rune_names:
        c.card_type = "rune"
        return
    for st in c.subtypes:
        low = st.lower()
        if low in TYPE_KEYWORDS:
            c.card_type = low
            return
    if c.energy is not None and c.power is None and c.might is None:
        c.card_type = "spell"
    elif c.power is not None and c.might is not None:
        c.card_type = "unit"
    else:
        c.card_type = "other"


def collect_icons_from_flight(flight: str) -> list[dict]:
    icons: dict = {}
    pattern = re.compile(
        r'https://cdn\.piltoverarchive\.com/(description_keywords|icons|colors|rarities)/'
        r'([^."/]+)\.(svg|webp|png)'
    )
    for m in pattern.finditer(flight):
        folder, code, _ext = m.group(1), m.group(2), m.group(3)
        kind = {
            "description_keywords": "keyword",
            "icons": "stat",
            "colors": "color",
            "rarities": "other",
        }[folder]
        icons[(kind, code)] = {
            "kind": kind, "code": code, "label": code, "image_url": m.group(0),
        }
    return list(icons.values())


def parse_pages(pages: Iterable[int], delay: float = 1.0, verbose: bool = False):
    session = requests.Session()
    all_cards: dict[str, CardData] = {}
    all_icons: dict = {}

    for p in pages:
        # Reintentos por página: si extraemos muy pocas cartas (la página
        # devolvió HTML incompleto o sin chunks RSC) volvemos a intentarlo.
        attempts = 0
        cards: list[CardData] = []
        while attempts < 4:
            attempts += 1
            if verbose:
                tag = f" (intento {attempts})" if attempts > 1 else ""
                print(f"[+] Página {p}...{tag}", file=sys.stderr)
            html = fetch_page(p, session)
            flight = collect_flight_text(html)
            cards = extract_cards(flight, source_url=f"{LIST_URL}?page={p}", verbose=verbose)
            if len(cards) >= 25:
                break
            time.sleep(delay)
        if verbose:
            print(f"    -> {len(cards)} cartas válidas", file=sys.stderr)
        for c in cards:
            # dedup por external_id (UUID) en vez de card_number, así no
            # perdemos variantes que comparten número pero son distintas.
            all_cards.setdefault(c.external_id or c.card_number, c)
        for ic in collect_icons_from_flight(flight):
            all_icons[(ic["kind"], ic["code"])] = ic
        time.sleep(delay)

    return list(all_cards.values()), list(all_icons.values())


def parse_pages_arg(s: str) -> list[int]:
    out: list[int] = []
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(chunk))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="1-21", help="Ej: 1-21 o 1,3,5")
    ap.add_argument("--out", default="riftbound_cards.json")
    ap.add_argument("--icons-out", default="riftbound_icons.json")
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    pages = parse_pages_arg(args.pages)
    cards, icons = parse_pages(pages, delay=args.delay, verbose=args.verbose)

    Path(args.out).write_text(
        json.dumps([asdict(c) for c in cards], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Path(args.icons_out).write_text(
        json.dumps(icons, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    print(f"[OK] {len(cards)} cartas -> {args.out}")
    print(f"[OK] {len(icons)} iconos -> {args.icons_out}")


if __name__ == "__main__":
    main()
