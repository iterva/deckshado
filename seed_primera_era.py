"""
Seed la base de datos con las cartas de Primera Era.
Lee primera_era_raw.json (URLs de BunnyCDN) y primera_era_mapping.json (Cloudinary).
Crea ediciones PE y cartas con sus imágenes.

Uso: python seed_primera_era.py
"""
import json
import os
import sqlite3
from urllib.parse import unquote

DB_PATH = os.path.join("backend", "db.sqlite3")
RAW_FILE = "primera_era_raw.json"
MAPPING_FILE = "primera_era_mapping.json"

PE_FORMAT_ID = 6  # 'pe' format in cards_format

# Mapeo de edición → slug para la tabla cards_edition
EDITION_CONFIG = {
    "El Reto": {"slug": "el-reto", "myl_id": "pe_01"},
    "Mundo Gótico": {"slug": "mundo-gotico", "myl_id": "pe_02"},
    "La Ira del Nahual": {"slug": "la-ira-del-nahual", "myl_id": "pe_03"},
    "Ragnarok": {"slug": "ragnarok-pe", "myl_id": "pe_04"},
    "Espíritu de Dragón": {"slug": "espiritu-de-dragon", "myl_id": "pe_05"},
}

# Mapeo de raza → slug en la BD
RACE_SLUGS = {
    "Caballero": "caballero",
    "Dragón": "dragon",
    "Fairy": "faerie",
    "Cazador": "cazador",
    "Vampiro": "vampiro",
    "Licántropo": "licantropo",
    "Bestia": "bestia",
    "Chaman": "chaman",
    "Guerrero": "guerrero",
    "Abominación": "abominacion",
    "Bárbaro": "barbaro",
    "Dios": "dios",
    "Campeón": "campeon",
    "Criaturas": "criaturas",
    "Kami": "kami",
    "Xian": "xian",
}


def infer_card_type_from_url(url: str) -> str:
    """Infiere el tipo de carta desde la ruta de la imagen."""
    decoded = unquote(url).lower()
    if "/talismanes/" in decoded or "/talisman/" in decoded:
        return "talisman"
    if "/armas/" in decoded:
        return "arma"
    if "/tótems/" in decoded or "/totems/" in decoded:
        return "totem"
    if "/oros/" in decoded:
        return "oro"
    if "/razas/" in decoded:
        return "aliado"
    # Si no se puede inferir, asumimos aliado (las cartas nuevas suelen ser aliados)
    return "aliado"


def infer_race_from_url(url: str, page_race: str) -> str:
    """Infiere la raza desde la URL. Si es soporte, es 'noraza'."""
    decoded = unquote(url).lower()
    if "/soporte/" in decoded:
        return "noraza"
    if "/razas/" in decoded:
        # La raza es la que indica la URL
        return RACE_SLUGS.get(page_race, "noraza")
    # Para cartas de otras carpetas (Nuevas, Toolkit, etc), asumimos que son de la raza de la página
    # si son aliados, o noraza si son soporte
    card_type = infer_card_type_from_url(url)
    if card_type == "aliado":
        return RACE_SLUGS.get(page_race, "noraza")
    return "noraza"


def main():
    print("=" * 80)
    print("SEED PRIMERA ERA - Base de Datos")
    print("=" * 80)

    # Cargar datos
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Cargar mapping de Cloudinary si existe
    cloudinary_mapping = {}
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            cloudinary_mapping = json.load(f)
        print(f"Cloudinary mapping cargado")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Crear ediciones PE si no existen
    print("\n--- Creando ediciones PE ---")
    edition_ids = {}
    for ed_name, config in EDITION_CONFIG.items():
        cur.execute("SELECT id FROM cards_edition WHERE slug = ?", (config["slug"],))
        row = cur.fetchone()
        if row:
            edition_ids[ed_name] = row[0]
            print(f"  {ed_name} ya existe (id={row[0]})")
        else:
            cur.execute(
                "INSERT INTO cards_edition (myl_id, title, slug, format_id, active, image, date_release, date_empire_valid) VALUES (?, ?, ?, ?, 1, '', NULL, NULL)",
                (config["myl_id"], f"PE - {ed_name}", config["slug"], PE_FORMAT_ID),
            )
            edition_ids[ed_name] = cur.lastrowid
            print(f"  {ed_name} creada (id={cur.lastrowid})")

    conn.commit()

    # 2. Obtener IDs de razas y tipos
    races_db = {}
    cur.execute("SELECT id, slug FROM cards_race")
    for row in cur.fetchall():
        races_db[row[1]] = row[0]

    types_db = {}
    cur.execute("SELECT id, slug FROM cards_cardtype")
    for row in cur.fetchall():
        types_db[row[1]] = row[0]

    # Rarity: usamos "Vasallo" (id=7) como default para PE
    default_rarity_id = 7

    # 3. Insertar cartas
    print("\n--- Insertando cartas ---")
    inserted = 0
    skipped = 0
    seen_cards = set()  # (name_lower, edition) para evitar duplicados

    for edition_name, races in raw_data.items():
        edition_id = edition_ids[edition_name]
        for race_name, cards in races.items():
            for card in cards:
                card_name = card["name"]
                source_url = card["smallUrl"]

                # Deduplicar por nombre + edición
                key = (card_name.lower(), edition_name)
                if key in seen_cards:
                    skipped += 1
                    continue
                seen_cards.add(key)

                # Verificar si ya existe en la BD
                cur.execute(
                    "SELECT id FROM cards_card WHERE name = ? AND edition_id = ?",
                    (card_name, edition_id),
                )
                if cur.fetchone():
                    skipped += 1
                    continue

                # Inferir tipo y raza
                card_type_slug = infer_card_type_from_url(source_url)
                race_slug = infer_race_from_url(source_url, race_name)

                card_type_id = types_db.get(card_type_slug, types_db["aliado"])
                race_id = races_db.get(race_slug, races_db["noraza"])

                # Obtener URL de Cloudinary si está disponible
                image_url = ""
                if edition_name in cloudinary_mapping:
                    if race_name in cloudinary_mapping[edition_name]:
                        card_mapping = cloudinary_mapping[edition_name][race_name].get(card_name, {})
                        if isinstance(card_mapping, dict):
                            image_url = card_mapping.get("cloudinary_url", "")
                        elif isinstance(card_mapping, str):
                            image_url = card_mapping

                # Si no hay URL de Cloudinary, usar la URL original
                if not image_url:
                    image_url = card["fullUrl"]

                # Generar slug y myl_id
                slug = f"pe-{card_name.lower().replace(' ', '-').replace('(', '').replace(')', '')}"
                myl_id = f"pe_{inserted + 1:04d}"

                cur.execute(
                    """INSERT INTO cards_card 
                       (myl_id, edid, slug, name, cost, damage, ability, flavour, 
                        card_type_id, edition_id, race_id, rarity_id, custom_image_url)
                       VALUES (?, '', ?, ?, 0, 0, '', '', ?, ?, ?, ?, ?)""",
                    (myl_id, slug, card_name, card_type_id, edition_id, race_id, default_rarity_id, image_url),
                )
                inserted += 1

                if inserted % 100 == 0:
                    print(f"  {inserted} cartas insertadas...")
                    conn.commit()

    conn.commit()
    conn.close()

    print(f"\n{'='*80}")
    print(f"RESULTADO: {inserted} insertadas, {skipped} saltadas (duplicados)")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
