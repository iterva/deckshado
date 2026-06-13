"""
Scrape TODAS las cartas del card-explorer de mazosyleyendas.cl (1551 artes)
Detecta cuáles faltan en nuestra DB, las sube a Cloudinary e inserta.

Requiere: pip install playwright cloudinary
          playwright install chromium
"""
import asyncio
import json
import os
import re
import sqlite3
from urllib.parse import unquote

import cloudinary
import cloudinary.uploader

# --- Config ---
cloudinary.config(
    cloud_name=(os.environ.get("CLOUDINARY_CLOUD_NAME") or "drw7y27sm"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)

DB_PATH = "backend/db.sqlite3"
RAW_FILE = "card_explorer_raw.json"
MAPPING_FILE = "card_explorer_mapping.json"

# --- Edition IDs (local DB) ---
EDITION_IDS = {
    "el-reto": 104,
    "mundo-gotico": 105,
    "la-ira-del-nahual": 106,
    "ragnarok": 107,
    "espiritu-de-dragon": 108,
}

# --- Race IDs ---
RACE_IDS = {
    "caballero": 2,
    "dragón": 12,
    "dragon": 12,
    "fairy": 7,
    "faerie": 7,
    "cazador": 22,
    "vampiro": 21,
    "licántropo": 20,
    "licantropo": 20,
    "bestia": 3,
    "chamán": 23,
    "chaman": 23,
    "guerrero": 5,
    "abominación": 25,
    "abominacion": 25,
    "bárbaro": 6,
    "barbaro": 6,
    "dios": 24,
    "kami": 26,
    "xian": 27,
    "criaturas": 28,
    "campeón": 32,
    "campeon": 32,
    "sin raza": 1,
}

# Card type IDs
CARD_TYPES = {
    "aliado": 1,
    "talisman": 2,
    "talismán": 2,
    "arma": 3,
    "totem": 4,
    "tótem": 4,
    "oro": 5,
}

# --- URL path → (edition_slug, race/type) mapping ---
# Maps URL path fragments to (edition_slug, card_type, race_key)
def classify_card(url: str):
    """
    Given a BunnyCDN URL, determine edition, card_type, and race.
    Returns (edition_slug, card_type_id, race_id) or None if can't classify.
    """
    decoded = unquote(url).lower()

    # PE COMP/Razas/N.- Race/ → aliado
    race_patterns = [
        (r"razas/1\.\-?\s*caballero", "el-reto", 1, "caballero"),
        (r"razas/2\.\-?\s*dragon", "el-reto", 1, "dragon"),
        (r"razas/3\.\-?\s*faerie", "el-reto", 1, "fairy"),
        (r"razas/4\.\-?\s*cazador", "mundo-gotico", 1, "cazador"),
        (r"razas/5\.\-?\s*lic", "mundo-gotico", 1, "licántropo"),
        (r"razas/6\.\-?\s*vampiro", "mundo-gotico", 1, "vampiro"),
        (r"razas/7\.\-?\s*bestia", "la-ira-del-nahual", 1, "bestia"),
        (r"razas/8\.\-?\s*cham", "la-ira-del-nahual", 1, "chamán"),
        (r"razas/9\.\-?\s*guerrero", "la-ira-del-nahual", 1, "guerrero"),
        (r"razas/10\.\-?\s*abominaci", "ragnarok", 1, "abominación"),
        (r"razas/11\.\-?\s*b.rbaro", "ragnarok", 1, "bárbaro"),
        (r"razas/12\.\-?\s*dios", "ragnarok", 1, "dios"),
        (r"razas/13\.\-?\s*criaturas", "espiritu-de-dragon", 1, "criaturas"),
        (r"razas/14\.\-?\s*campe", "espiritu-de-dragon", 1, "campeón"),
        (r"razas/15\.\-?\s*kami", "espiritu-de-dragon", 1, "kami"),
        (r"razas/16\.\-?\s*xian", "espiritu-de-dragon", 1, "xian"),
    ]

    # Soporte/N.- Edition/Type/
    support_patterns = [
        (r"soporte/1\.\-?\s*el\s*reto/armas", "el-reto", 3, "sin raza"),
        (r"soporte/1\.\-?\s*el\s*reto/t.tems", "el-reto", 4, "sin raza"),
        (r"soporte/1\.\-?\s*el\s*reto/talismanes", "el-reto", 2, "sin raza"),
        (r"soporte/1\.\-?\s*el\s*reto/oros", "el-reto", 5, "sin raza"),
        (r"soporte/2\.\-?\s*mundo\s*g.tico/armas", "mundo-gotico", 3, "sin raza"),
        (r"soporte/2\.\-?\s*mundo\s*g.tico/t.tems", "mundo-gotico", 4, "sin raza"),
        (r"soporte/2\.\-?\s*mundo\s*g.tico/talismanes", "mundo-gotico", 2, "sin raza"),
        (r"soporte/2\.\-?\s*mundo\s*g.tico/oros", "mundo-gotico", 5, "sin raza"),
        (r"soporte/3\.\-?\s*la\s*ira.*?/armas", "la-ira-del-nahual", 3, "sin raza"),
        (r"soporte/3\.\-?\s*la\s*ira.*?/t.tems", "la-ira-del-nahual", 4, "sin raza"),
        (r"soporte/3\.\-?\s*la\s*ira.*?/talismanes", "la-ira-del-nahual", 2, "sin raza"),
        (r"soporte/3\.\-?\s*la\s*ira.*?/oros", "la-ira-del-nahual", 5, "sin raza"),
        (r"soporte/4\.\-?\s*ragnarok/armas", "ragnarok", 3, "sin raza"),
        (r"soporte/4\.\-?\s*ragnarok/t.tems", "ragnarok", 4, "sin raza"),
        (r"soporte/4\.\-?\s*ragnarok/talismanes", "ragnarok", 2, "sin raza"),
        (r"soporte/4\.\-?\s*ragnarok/oros", "ragnarok", 5, "sin raza"),
        (r"soporte/5\.\-?\s*esp.ritu/armas", "espiritu-de-dragon", 3, "sin raza"),
        (r"soporte/5\.\-?\s*esp.ritu.*?/t.tems", "espiritu-de-dragon", 4, "sin raza"),
        (r"soporte/5\.\-?\s*esp.ritu.*?/talismanes", "espiritu-de-dragon", 2, "sin raza"),
        (r"soporte/5\.\-?\s*esp.ritu.*?/oros", "espiritu-de-dragon", 5, "sin raza"),
    ]

    # Artes Alternativos patterns
    alt_patterns = [
        (r"artes\s*alternativos/el\s*reto/caballero", "el-reto", 1, "caballero"),
        (r"artes\s*alternativos/el\s*reto/dragon", "el-reto", 1, "dragon"),
        (r"artes\s*alternativos/el\s*reto/faerie", "el-reto", 1, "fairy"),
        (r"artes\s*alternativos/el\s*reto/armas", "el-reto", 3, "sin raza"),
        (r"artes\s*alternativos/el\s*reto/totem", "el-reto", 4, "sin raza"),
        (r"artes\s*alternativos/el\s*reto/talim", "el-reto", 2, "sin raza"),
        (r"artes\s*alternativos/el\s*reto/oros", "el-reto", 5, "sin raza"),
        (r"artes\s*alternativos/mundo\s*gotico/cazador", "mundo-gotico", 1, "cazador"),
        (r"artes\s*alternativos/mundo\s*gotico/vampiro", "mundo-gotico", 1, "vampiro"),
        (r"artes\s*alternativos/mundo\s*gotico/licantropo", "mundo-gotico", 1, "licántropo"),
        (r"artes\s*alternativos/mundo\s*gotico/armas", "mundo-gotico", 3, "sin raza"),
        (r"artes\s*alternativos/mundo\s*gotico/talismanes", "mundo-gotico", 2, "sin raza"),
        (r"artes\s*alternativos/mundo\s*gotico/oro", "mundo-gotico", 5, "sin raza"),
        (r"artes\s*alternativos/la\s*ira/bestias", "la-ira-del-nahual", 1, "bestia"),
        (r"artes\s*alternativos/la\s*ira/chaman", "la-ira-del-nahual", 1, "chamán"),
        (r"artes\s*alternativos/la\s*ira/guerrero", "la-ira-del-nahual", 1, "guerrero"),
        (r"artes\s*alternativos/la\s*ira/armas", "la-ira-del-nahual", 3, "sin raza"),
        (r"artes\s*alternativos/la\s*ira/totems", "la-ira-del-nahual", 4, "sin raza"),
        (r"artes\s*alternativos/la\s*ira/talisman", "la-ira-del-nahual", 2, "sin raza"),
        (r"artes\s*alternativos/la\s*ira/oro", "la-ira-del-nahual", 5, "sin raza"),
    ]

    # Expansion patterns
    expansion_patterns = [
        (r"mundos\s*perdidos.*?/tombstone", "mundo-gotico", 1, "cazador"),
        (r"mundos\s*perdidos.*?/nube\s*roja", "la-ira-del-nahual", 1, "guerrero"),
        (r"mundos\s*perdidos.*?/xinnian\s*2026", "espiritu-de-dragon", 1, "campeón"),
    ]

    # Nuevas patterns (edition-specific keywords in page context)
    nuevas_edition_patterns = [
        (r"nuevas\s*4\.0/el\s*reto", "el-reto", 1, "sin raza"),
        (r"nuevas\s*4\.0/gotico", "mundo-gotico", 1, "sin raza"),
        (r"nuevas\s*4\.0/ira", "la-ira-del-nahual", 1, "sin raza"),
        (r"nuevas\s*4\.0/ragnarok", "ragnarok", 1, "sin raza"),
        (r"nuevas\s*4\.0/esperitu", "espiritu-de-dragon", 1, "sin raza"),
        (r"nuevas\s*4\.0/colmillo", "mundo-gotico", 1, "licántropo"),
    ]

    # Oros genéricos
    oros_pattern = r"pe\s*comp/oros/"

    # Cartas Faltantes
    faltantes_patterns = [
        (r"cartas\s*faltantes/reto", "el-reto", 1, "sin raza"),
        (r"cartas\s*faltantes/gotico", "mundo-gotico", 1, "sin raza"),
        (r"cartas\s*faltantes/ira", "la-ira-del-nahual", 1, "sin raza"),
        (r"cartas\s*faltantes/ragnarok", "ragnarok", 1, "sin raza"),
        (r"cartas\s*faltantes/espiritu", "espiritu-de-dragon", 1, "sin raza"),
    ]

    # PE COMP/Cartas Faltantes
    pe_faltantes_patterns = [
        (r"pe\s*comp/cartas\s*faltantes/espiritu", "espiritu-de-dragon", 1, "sin raza"),
    ]

    # Try all pattern groups
    for patterns in [race_patterns, support_patterns, alt_patterns,
                     expansion_patterns, nuevas_edition_patterns,
                     faltantes_patterns, pe_faltantes_patterns]:
        for pattern, edition, card_type, race in patterns:
            if re.search(pattern, decoded):
                race_id = RACE_IDS.get(race, 1)
                # For aliados in races, determine race from the pattern
                if card_type == 1 and race != "sin raza":
                    race_id = RACE_IDS.get(race, 1)
                return (edition, card_type, race_id)

    # Oros genéricos → edición por contexto es difícil, default El Reto
    if re.search(oros_pattern, decoded):
        return ("el-reto", 5, 1)

    # Cofradía
    if "cofradia" in decoded:
        return ("el-reto", 1, 1)  # Default

    # Toolkit 2026 - try to infer from nearby context
    if "toolkit 2026" in decoded:
        if "nuevas" in decoded:
            return ("el-reto", 1, 1)
        if "rework" in decoded:
            return ("el-reto", 1, 1)
        return ("el-reto", 1, 1)

    # lootbox2025
    if "lootbox2025" in decoded:
        return ("el-reto", 1, 1)

    # NuevasCofra
    if "nuevascofra" in decoded:
        return ("el-reto", 2, 1)

    # Nuevas/
    if "/nuevas/" in decoded:
        return ("el-reto", 1, 1)

    # cole racial 2
    if "cole racial 2" in decoded:
        if "reto" in decoded:
            return ("el-reto", 1, 1)
        if "rework" in decoded:
            return ("el-reto", 1, 1)
        if "espiritu" in decoded:
            return ("espiritu-de-dragon", 1, 1)
        return ("el-reto", 1, 1)

    # cartas aniversario
    if "cartas aniversario" in decoded:
        return ("el-reto", 1, 1)

    # Correcioneas (typo in CDN)
    if "correcioneas" in decoded:
        return ("el-reto", 1, 1)

    return None


async def scrape_card_explorer():
    """Scrape all 1551 cards from the card-explorer page."""
    from playwright.async_api import async_playwright

    print("=" * 80)
    print("SCRAPING CARD EXPLORER - TODAS LAS CARTAS PE")
    print("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Abriendo card-explorer...")
        await page.goto("https://mazosyleyendas.cl/card-explorer", wait_until="networkidle", timeout=60000)

        # Wait for cards to load
        await page.wait_for_selector('img[src*="b-cdn.net"]', timeout=30000)
        await asyncio.sleep(3)

        # Scroll to load all lazy-loaded images
        print("Scrolling para cargar todas las imágenes...")
        prev_count = 0
        for i in range(50):
            await page.evaluate("window.scrollBy(0, 2000)")
            await asyncio.sleep(0.5)
            count = await page.evaluate("document.querySelectorAll('img[src*=\"b-cdn.net\"]').length")
            if count == prev_count and count > 1000:
                break
            prev_count = count
            if i % 10 == 0:
                print(f"  ... {count} imágenes cargadas")

        # Extract all cards
        print("Extrayendo datos de cartas...")
        cards = await page.evaluate("""() => {
            const cards = [];
            const containers = document.querySelectorAll('img[src*="b-cdn.net"]');
            containers.forEach(img => {
                const alt = img.alt || '';
                const src = img.src || '';
                if (src && alt) {
                    cards.push({
                        name: alt.trim(),
                        url: src
                    });
                }
            });
            return cards;
        }""")

        print(f"Total cartas extraídas: {len(cards)}")
        await browser.close()

    return cards


def get_existing_urls_from_db():
    """Get all existing card URLs from DB to detect duplicates."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT name, custom_image_url, edition_id
        FROM cards_card
        WHERE edition_id IN (SELECT id FROM cards_edition WHERE format_id=6)
    """)
    existing = {}
    for name, url, ed_id in cur.fetchall():
        key = f"{name}|{ed_id}"
        existing[key] = url
    conn.close()
    return existing


def upload_card_to_cloudinary(source_url, edition_slug, card_name, variant_num=0):
    """Upload card image to Cloudinary from URL."""
    safe_name = card_name.replace(" ", "_").replace("(", "").replace(")", "")
    safe_name = safe_name.replace("'", "").replace('"', "").replace("/", "_")
    safe_name = re.sub(r'[^\w\-]', '_', safe_name)
    if variant_num > 0:
        safe_name = f"{safe_name}_v{variant_num}"

    public_id = f"primera_era/{edition_slug}/{safe_name}"

    try:
        # Use the full URL (not -small)
        full_url = source_url.replace("-small.webp", ".webp")
        result = cloudinary.uploader.upload(
            full_url,
            public_id=public_id,
            overwrite=False,
            resource_type="image",
        )
        return result["secure_url"]
    except Exception as e:
        # Try with small URL if full fails
        try:
            result = cloudinary.uploader.upload(
                source_url,
                public_id=public_id,
                overwrite=False,
                resource_type="image",
            )
            return result["secure_url"]
        except Exception as e2:
            print(f"    ERROR upload {card_name}: {e2}")
            return None


def main():
    # Step 1: Scrape or load raw data
    if os.path.exists(RAW_FILE):
        print(f"Cargando datos cacheados de {RAW_FILE}...")
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            all_cards = json.load(f)
        print(f"  → {len(all_cards)} cartas cargadas")
    else:
        all_cards = asyncio.run(scrape_card_explorer())
        with open(RAW_FILE, "w", encoding="utf-8") as f:
            json.dump(all_cards, f, ensure_ascii=False, indent=2)
        print(f"Datos guardados en {RAW_FILE}")

    # Step 2: Get existing data
    print("\nCargando cartas existentes de la DB...")
    existing = get_existing_urls_from_db()
    print(f"  → {len(existing)} cartas existentes en DB")

    # Also load existing mapping to check by URL
    existing_source_urls = set()
    if os.path.exists("primera_era_mapping.json"):
        with open("primera_era_mapping.json", "r", encoding="utf-8") as f:
            old_mapping = json.load(f)
        for ed, races in old_mapping.items():
            for race, cards in races.items():
                for name, data in cards.items():
                    if isinstance(data, dict):
                        if "source_url" in data:
                            existing_source_urls.add(data["source_url"])
                        if "small_url" in data:
                            existing_source_urls.add(data["small_url"])
                    elif isinstance(data, str):
                        existing_source_urls.add(data)

    # Step 3: Classify and find missing cards
    print("\nClasificando cartas y buscando faltantes...")
    new_cards = []
    unclassified = []

    for card in all_cards:
        url = card["url"]
        name = card["name"]

        # Check if this exact URL is already in our mapping
        if url in existing_source_urls:
            continue

        # Classify the card
        classification = classify_card(url)
        if classification is None:
            unclassified.append(card)
            continue

        edition_slug, card_type_id, race_id = classification
        edition_id = EDITION_IDS[edition_slug]

        # Check if this name+edition already exists in DB
        key = f"{name}|{edition_id}"
        if key in existing:
            # Same name exists - this is a variant, need unique name
            variant = 2
            while f"{name} (v{variant})|{edition_id}" in existing:
                variant += 1
            card_entry = {
                "name": f"{name} (v{variant})",
                "url": url,
                "edition_slug": edition_slug,
                "edition_id": edition_id,
                "card_type_id": card_type_id,
                "race_id": race_id,
                "variant": variant,
            }
        else:
            card_entry = {
                "name": name,
                "url": url,
                "edition_slug": edition_slug,
                "edition_id": edition_id,
                "card_type_id": card_type_id,
                "race_id": race_id,
                "variant": 0,
            }

        new_cards.append(card_entry)
        # Track to handle multiple variants of same card in this batch
        existing[f"{card_entry['name']}|{edition_id}"] = url

    print(f"  → {len(new_cards)} cartas NUEVAS a agregar")
    print(f"  → {len(unclassified)} cartas sin clasificar")

    if unclassified:
        print("\n  Cartas sin clasificar (primeras 10):")
        for c in unclassified[:10]:
            print(f"    - {c['name']}: {c['url']}")

    if not new_cards:
        print("\n¡No hay cartas nuevas que agregar!")
        return

    # Step 4: Upload to Cloudinary and insert to DB
    print(f"\n{'='*80}")
    print(f"SUBIENDO {len(new_cards)} CARTAS A CLOUDINARY E INSERTANDO EN DB")
    print(f"{'='*80}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    mapping = {}  # New mapping for these cards
    uploaded = 0
    errors = 0

    for i, card in enumerate(new_cards, 1):
        name = card["name"]
        url = card["url"]
        edition_slug = card["edition_slug"]
        edition_id = card["edition_id"]
        card_type_id = card["card_type_id"]
        race_id = card["race_id"]
        variant = card["variant"]

        # Upload to Cloudinary
        cloudinary_url = upload_card_to_cloudinary(url, edition_slug, name, 0)

        if cloudinary_url:
            uploaded += 1
            # Insert into DB
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            try:
                cur.execute("""
                    INSERT INTO cards_card (name, slug, custom_image_url, card_type_id, edition_id, race_id, cost, damage, ability, flavour, myl_id, edid, rarity_id)
                    VALUES (?, ?, ?, ?, ?, ?, '', '', '', '', 0, 0, NULL)
                """, (name, slug, cloudinary_url, card_type_id, edition_id, race_id))
            except sqlite3.IntegrityError:
                pass  # Skip if somehow duplicate

            # Track in mapping
            if edition_slug not in mapping:
                mapping[edition_slug] = {}
            mapping[edition_slug][name] = {
                "source_url": url,
                "cloudinary_url": cloudinary_url,
            }
        else:
            errors += 1

        if i % 25 == 0 or i == len(new_cards):
            conn.commit()
            print(f"  [{i}/{len(new_cards)}] Subidas: {uploaded}, Errores: {errors}")

    conn.commit()
    conn.close()

    # Save mapping
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"RESULTADO: {uploaded} subidas, {errors} errores")
    print(f"Mapping guardado en {MAPPING_FILE}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
