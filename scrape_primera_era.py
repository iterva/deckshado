"""
Scrape todas las cartas de Primera Era desde mazosyleyendas.cl/deck-builder/racial-edicion
y las sube a Cloudinary.

Requiere: pip install playwright cloudinary requests
          playwright install chromium
"""
import asyncio
import json
import os
import time
import requests
import cloudinary
import cloudinary.uploader
from urllib.parse import unquote

# --- Configuración Cloudinary ---
cloudinary.config(
    cloud_name=(os.environ.get("CLOUDINARY_CLOUD_NAME") or "drw7y27sm"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)

BASE_URL = "https://mazosyleyendas.cl/deck-builder/racial-edicion"

EDITIONS = {
    "El Reto": ["Caballero", "Dragón", "Fairy"],
    "Mundo Gótico": ["Cazador", "Vampiro", "Licántropo"],
    "La Ira del Nahual": ["Bestia", "Chaman", "Guerrero"],
    "Ragnarok": ["Abominación", "Bárbaro", "Dios"],
    "Espíritu de Dragón": ["Campeón", "Criaturas", "Kami", "Xian"],
}

MAPPING_FILE = "primera_era_mapping.json"
DOWNLOAD_DIR = "primera_era_cards"


async def scrape_all_cards():
    """Usa Playwright para navegar todas las ediciones/razas y extraer URLs de cartas."""
    from playwright.async_api import async_playwright

    all_cards = {}  # {edition: {race: [{name, smallUrl, fullUrl}]}}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for edition, races in EDITIONS.items():
            all_cards[edition] = {}
            for race in races:
                url = f"{BASE_URL}/{edition}/{race}"
                print(f"\n{'='*60}")
                print(f"Scraping: {edition} / {race}")
                print(f"URL: {url}")

                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    # Esperar a que las imágenes de cartas carguen
                    await page.wait_for_selector('img[src*="b-cdn.net"]', timeout=15000)
                    # Esperar un poco más para que todas carguen
                    await asyncio.sleep(2)

                    # Extraer todas las URLs de imágenes de cartas
                    cards = await page.evaluate("""() => {
                        const imgs = Array.from(document.querySelectorAll('img[src*="b-cdn.net"]'));
                        return imgs.map(img => {
                            const src = img.src;
                            const decoded = decodeURIComponent(src);
                            const filename = decoded.split('/').pop().replace('-small.webp', '');
                            return {
                                name: filename,
                                smallUrl: src,
                                fullUrl: src.replace('-small.webp', '.webp')
                            };
                        });
                    }""")

                    all_cards[edition][race] = cards
                    print(f"  → {len(cards)} cartas encontradas")

                except Exception as e:
                    print(f"  ERROR: {e}")
                    all_cards[edition][race] = []

        await browser.close()

    return all_cards


def download_image(url, filepath):
    """Descarga una imagen desde una URL."""
    try:
        resp = requests.get(url, timeout=30, stream=True)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return True
        else:
            print(f"    HTTP {resp.status_code} para {url}")
            return False
    except Exception as e:
        print(f"    Error descargando: {e}")
        return False


def upload_to_cloudinary(filepath, public_id):
    """Sube una imagen a Cloudinary y retorna la URL."""
    try:
        result = cloudinary.uploader.upload(
            filepath,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            folder="primera_era",
        )
        return result["secure_url"]
    except Exception as e:
        print(f"    Error subiendo a Cloudinary: {e}")
        return None


def upload_from_url(image_url, public_id):
    """Sube una imagen a Cloudinary directamente desde URL (sin descargar)."""
    try:
        result = cloudinary.uploader.upload(
            image_url,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
        return result["secure_url"]
    except Exception as e:
        print(f"    Error subiendo a Cloudinary: {e}")
        return None


def sanitize_public_id(edition, race, card_name):
    """Genera un public_id seguro para Cloudinary."""
    # Normalizar: quitar caracteres problemáticos
    safe_name = card_name.replace(" ", "_").replace("(", "").replace(")", "")
    safe_name = safe_name.replace("'", "").replace('"', "").replace("/", "_")
    safe_edition = edition.replace(" ", "_")
    safe_race = race.replace(" ", "_")
    return f"primera_era/{safe_edition}/{safe_race}/{safe_name}"


def main():
    # Paso 1: Scrape
    print("=" * 80)
    print("SCRAPING CARTAS DE PRIMERA ERA")
    print("=" * 80)

    # Cargar mapping existente si hay
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        print(f"Mapping existente cargado: {sum(len(races) for ed in mapping.values() for races in ed.values())} cartas")
    else:
        mapping = {}

    # Scrape
    all_cards = asyncio.run(scrape_all_cards())

    # Guardar datos crudos
    with open("primera_era_raw.json", "w", encoding="utf-8") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)
    print(f"\nDatos crudos guardados en primera_era_raw.json")

    # Paso 2: Subir a Cloudinary directamente desde URL
    print("\n" + "=" * 80)
    print("SUBIENDO A CLOUDINARY")
    print("=" * 80)

    total = sum(len(cards) for ed in all_cards.values() for cards in ed.values())
    uploaded = 0
    errors = 0

    for edition, races in all_cards.items():
        if edition not in mapping:
            mapping[edition] = {}

        for race, cards in races.items():
            if race not in mapping[edition]:
                mapping[edition][race] = {}

            for card in cards:
                name = card["name"]

                # Si ya está en el mapping, saltar
                if name in mapping[edition][race]:
                    uploaded += 1
                    continue

                public_id = sanitize_public_id(edition, race, name)
                # Subir directamente desde la URL del CDN (más eficiente)
                image_url = card["fullUrl"]

                print(f"  [{uploaded+errors+1}/{total}] {edition}/{race}/{name}...", end=" ", flush=True)
                cloudinary_url = upload_from_url(image_url, public_id)

                if cloudinary_url:
                    mapping[edition][race][name] = {
                        "cloudinary_url": cloudinary_url,
                        "source_url": image_url,
                    }
                    uploaded += 1
                    print(f"OK")
                else:
                    # Intentar con la URL small si la full falla
                    cloudinary_url = upload_from_url(card["smallUrl"], public_id)
                    if cloudinary_url:
                        mapping[edition][race][name] = {
                            "cloudinary_url": cloudinary_url,
                            "source_url": card["smallUrl"],
                        }
                        uploaded += 1
                        print(f"OK (small)")
                    else:
                        errors += 1
                        print(f"FAILED")

                # Guardar mapping cada 20 cartas
                if (uploaded + errors) % 20 == 0:
                    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
                        json.dump(mapping, f, ensure_ascii=False, indent=2)

                # Rate limiting
                time.sleep(0.3)

    # Guardar mapping final
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"RESULTADO: {uploaded} subidas, {errors} errores")
    print(f"Mapping guardado en {MAPPING_FILE}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
