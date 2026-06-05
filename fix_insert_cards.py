"""
Fix: Insert the 1511 cards into DB with proper myl_id values.
The original script uploaded to Cloudinary successfully but failed DB inserts
because myl_id=0 was used for all (UNIQUE constraint).

This script:
1. Removes the erroneous myl_id='0' entry
2. Re-classifies cards from card_explorer_raw.json
3. Looks up Cloudinary URLs from card_explorer_mapping.json
4. Inserts with sequential myl_ids (pe_1309, pe_1310, ...)
"""
import json
import re
import sqlite3
from urllib.parse import unquote

DB_PATH = "backend/db.sqlite3"
RAW_FILE = "card_explorer_raw.json"
MAPPING_FILE = "card_explorer_mapping.json"

# Import classification logic
EDITION_IDS = {
    "el-reto": 104,
    "mundo-gotico": 105,
    "la-ira-del-nahual": 106,
    "ragnarok": 107,
    "espiritu-de-dragon": 108,
}

RACE_IDS = {
    "caballero": 2, "dragón": 12, "dragon": 12, "fairy": 7, "faerie": 7,
    "cazador": 22, "vampiro": 21, "licántropo": 20, "licantropo": 20,
    "bestia": 3, "chamán": 23, "chaman": 23, "guerrero": 5,
    "abominación": 25, "abominacion": 25, "bárbaro": 6, "barbaro": 6,
    "dios": 24, "kami": 26, "xian": 27, "criaturas": 28,
    "campeón": 32, "campeon": 32, "sin raza": 1,
}


def classify_card(url: str):
    decoded = unquote(url).lower()

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

    expansion_patterns = [
        (r"mundos\s*perdidos.*?/tombstone", "mundo-gotico", 1, "cazador"),
        (r"mundos\s*perdidos.*?/nube\s*roja", "la-ira-del-nahual", 1, "guerrero"),
        (r"mundos\s*perdidos.*?/xinnian\s*2026", "espiritu-de-dragon", 1, "campeón"),
    ]

    nuevas_edition_patterns = [
        (r"nuevas\s*4\.0/el\s*reto", "el-reto", 1, "sin raza"),
        (r"nuevas\s*4\.0/gotico", "mundo-gotico", 1, "sin raza"),
        (r"nuevas\s*4\.0/ira", "la-ira-del-nahual", 1, "sin raza"),
        (r"nuevas\s*4\.0/ragnarok", "ragnarok", 1, "sin raza"),
        (r"nuevas\s*4\.0/esperitu", "espiritu-de-dragon", 1, "sin raza"),
        (r"nuevas\s*4\.0/colmillo", "mundo-gotico", 1, "licántropo"),
    ]

    faltantes_patterns = [
        (r"cartas\s*faltantes/reto", "el-reto", 1, "sin raza"),
        (r"cartas\s*faltantes/gotico", "mundo-gotico", 1, "sin raza"),
        (r"cartas\s*faltantes/ira", "la-ira-del-nahual", 1, "sin raza"),
        (r"cartas\s*faltantes/ragnarok", "ragnarok", 1, "sin raza"),
        (r"cartas\s*faltantes/espiritu", "espiritu-de-dragon", 1, "sin raza"),
    ]

    pe_faltantes_patterns = [
        (r"pe\s*comp/cartas\s*faltantes/espiritu", "espiritu-de-dragon", 1, "sin raza"),
    ]

    for patterns in [race_patterns, support_patterns, alt_patterns,
                     expansion_patterns, nuevas_edition_patterns,
                     faltantes_patterns, pe_faltantes_patterns]:
        for pattern, edition, card_type, race in patterns:
            if re.search(pattern, decoded):
                race_id = RACE_IDS.get(race, 1)
                return (edition, card_type, race_id)

    if re.search(r"pe\s*comp/oros/", decoded):
        return ("el-reto", 5, 1)
    if "cofradia" in decoded:
        return ("el-reto", 1, 1)
    if "toolkit 2026" in decoded:
        return ("el-reto", 1, 1)
    if "lootbox2025" in decoded:
        return ("el-reto", 1, 1)
    if "nuevascofra" in decoded:
        return ("el-reto", 2, 1)
    if "/nuevas/" in decoded:
        return ("el-reto", 1, 1)
    if "cole racial 2" in decoded:
        if "espiritu" in decoded:
            return ("espiritu-de-dragon", 1, 1)
        return ("el-reto", 1, 1)
    if "cartas aniversario" in decoded:
        return ("el-reto", 1, 1)
    if "correcioneas" in decoded:
        return ("el-reto", 1, 1)

    return None


def main():
    # Load raw cards and mapping
    raw_cards = json.load(open(RAW_FILE, "r", encoding="utf-8"))
    mapping = json.load(open(MAPPING_FILE, "r", encoding="utf-8"))

    # Build reverse lookup: source_url → cloudinary_url
    url_to_cloudinary = {}
    for edition_slug, cards in mapping.items():
        for card_name, data in cards.items():
            url_to_cloudinary[data["source_url"]] = data["cloudinary_url"]

    print(f"Cartas raw: {len(raw_cards)}")
    print(f"URLs en mapping (Cloudinary): {len(url_to_cloudinary)}")

    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Remove erroneous myl_id='0' entry
    cur.execute("DELETE FROM cards_card WHERE myl_id = '0'")
    deleted = cur.rowcount
    print(f"Eliminadas {deleted} cartas con myl_id='0'")
    conn.commit()

    # Get existing card URLs in DB to avoid re-inserting
    cur.execute("SELECT custom_image_url FROM cards_card WHERE edition_id IN (104,105,106,107,108)")
    existing_urls = set(r[0] for r in cur.fetchall() if r[0])

    # Get next myl_id number
    cur.execute("SELECT myl_id FROM cards_card WHERE myl_id LIKE 'pe_%' ORDER BY CAST(SUBSTR(myl_id, 4) AS INTEGER) DESC LIMIT 1")
    last = cur.fetchone()
    next_id = int(last[0].split("_")[1]) + 1 if last else 1309
    print(f"Siguiente myl_id: pe_{next_id:04d}")

    # Classify and build insert list
    # Track name occurrences per edition to assign variants
    name_counts = {}  # (name, edition_slug) → count
    cur.execute("SELECT name, edition_id FROM cards_card WHERE edition_id IN (104,105,106,107,108)")
    for row in cur.fetchall():
        key = (row[0], row[1])
        name_counts[key] = name_counts.get(key, 0) + 1

    to_insert = []
    unclassified = []

    for card in raw_cards:
        name = card["name"]
        url = card["url"]

        # Skip if this exact cloudinary URL is already in DB
        cloudinary_url = url_to_cloudinary.get(url)
        if not cloudinary_url:
            continue  # Not in mapping (wasn't uploaded)
        if cloudinary_url in existing_urls:
            continue  # Already in DB

        # Classify
        result = classify_card(url)
        if not result:
            unclassified.append(card)
            continue

        edition_slug, card_type_id, race_id = result
        edition_id = EDITION_IDS[edition_slug]

        # Determine variant name
        key = (name, edition_id)
        count = name_counts.get(key, 0)
        if count > 0:
            display_name = f"{name} (v{count + 1})"
        else:
            display_name = name
        name_counts[key] = count + 1

        to_insert.append({
            "name": display_name,
            "cloudinary_url": cloudinary_url,
            "card_type_id": card_type_id,
            "edition_id": edition_id,
            "race_id": race_id,
        })

    print(f"\nCartas a insertar: {len(to_insert)}")
    print(f"Sin clasificar: {len(unclassified)}")
    if unclassified:
        print("  Primeras sin clasificar:")
        for c in unclassified[:5]:
            print(f"    - {c['name']}: {c['url']}")

    # Insert
    inserted = 0
    for card in to_insert:
        myl_id = f"pe_{next_id:04d}"
        slug = re.sub(r'[^a-z0-9]+', '-', card["name"].lower()).strip('-')
        try:
            cur.execute("""
                INSERT INTO cards_card (name, slug, custom_image_url, card_type_id, edition_id, race_id, cost, damage, ability, flavour, myl_id, edid, rarity_id)
                VALUES (?, ?, ?, ?, ?, ?, '', '', '', '', ?, 0, NULL)
            """, (card["name"], slug, card["cloudinary_url"], card["card_type_id"],
                  card["edition_id"], card["race_id"], myl_id))
            inserted += 1
            next_id += 1
        except sqlite3.IntegrityError as e:
            print(f"  ERROR inserting {card['name']}: {e}")

        if inserted % 100 == 0:
            conn.commit()

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"INSERTADAS: {inserted} cartas (pe_{next_id - inserted:04d} a pe_{next_id - 1:04d})")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
