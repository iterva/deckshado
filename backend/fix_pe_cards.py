"""
Fix PE card races and types.
Combines all fixes:
1. Revert any wrong changes from old fix (Fenrir)
2. Fix Colgante Impio / Ojo del Padre → Oro
3. Assign correct race to 306 aliados that had 'Sin Raza'
4. Fix cards misclassified as Aliado that should be Arma/Talismán/Tótem

Run from backend/: python fix_pe_races.py
"""
import json
import os
import re
import sqlite3
import unicodedata

RAW_FILE = os.path.join(os.path.dirname(__file__), "..", "primera_era_raw.json")
DB_PATH = os.path.join(os.path.dirname(__file__), "db.sqlite3")

RACE_SLUGS = {
    "Caballero": "caballero", "Dragón": "dragon", "Fairy": "faerie",
    "Cazador": "cazador", "Vampiro": "vampiro", "Licántropo": "licantropo",
    "Bestia": "bestia", "Chaman": "chaman", "Guerrero": "guerrero",
    "Abominación": "abominacion", "Bárbaro": "barbaro", "Dios": "dios",
    "Campeón": "campeon", "Criaturas": "criaturas", "Kami": "kami", "Xian": "xian",
}

EDITION_SLUGS = {
    "El Reto": "el-reto", "Mundo Gótico": "mundo-gotico",
    "La Ira del Nahual": "la-ira-del-nahual", "Ragnarok": "ragnarok",
    "Espíritu de Dragón": "espiritu-de-dragon",
}

PE_SLUGS = tuple(EDITION_SLUGS.values())

# Manual race assignments by card name (normalized) -> race_slug
# For cards that can't be auto-matched from raw JSON
MANUAL_RACE = {
    ("el-reto", "isthar"): "faerie",
    ("el-reto", "terence el escudero"): "caballero",
    ("el-reto", "mounstro del lago"): "dragon",
    ("el-reto", "tentevilu"): "faerie",
    ("el-reto", "yddraig wen"): "dragon",
    ("el-reto", "dragon esmeralda"): "dragon",
    ("el-reto", "las musas"): "faerie",
    ("el-reto", "caballero verde"): "caballero",
    ("el-reto", "bruja carabusse"): "faerie",
    ("el-reto", "nido de dragon"): "dragon",
    ("el-reto", "espino blanco"): "faerie",
    ("el-reto", "peter stumpp"): "faerie",
    ("el-reto", "pantera mishipeshu"): "dragon",
    ("el-reto", "guerrero abenaki"): "guerrero",
    ("el-reto", "witte wiwer"): "faerie",
    ("el-reto", "genesis troll"): "faerie",
    ("el-reto", "li shuwen"): "campeon",
    ("el-reto", "yagyu jubei"): "kami",
    ("el-reto", "tarhunna"): "faerie",
    ("el-reto", "perun"): "faerie",
    ("mundo-gotico", "alabarda de la sangre"): "cazador",
    ("la-ira-del-nahual", "basilisco"): "bestia",
    ("la-ira-del-nahual", "cipatonal y oxmoco"): "chaman",
    ("la-ira-del-nahual", "mama ocllo"): "chaman",
    ("la-ira-del-nahual", "wayra tata"): "chaman",
    ("la-ira-del-nahual", "sinchi roca"): "guerrero",
    ("la-ira-del-nahual", "ah puch"): "chaman",
    ("la-ira-del-nahual", "forma de oso"): "bestia",
    ("la-ira-del-nahual", "k' ak' na"): "chaman",
    ("la-ira-del-nahual", "tzolkin"): "chaman",
    ("la-ira-del-nahual", "pintura naskapi"): "chaman",
    ("ragnarok", "fenrisulfr"): "abominacion",
    ("ragnarok", "nidhogg"): "abominacion",
    ("ragnarok", "hararld halfdansson"): "barbaro",
    ("ragnarok", "lagertha"): "barbaro",
    ("espiritu-de-dragon", "susano wa"): "kami",
    ("espiritu-de-dragon", "yingyanggong"): "xian",
    ("espiritu-de-dragon", "calabaza del inmortal"): "xian",
}

# Cards wrongly classified as Aliado → correct type_id
# type_id: 2=Talismán, 3=Arma, 4=Tótem
MANUAL_TYPE_FIX = {
    ("el-reto", "mandoble purificador"): 3,
    ("el-reto", "flamberge suiza"): 3,
    ("el-reto", "arco delaware"): 3,
    ("el-reto", "baculo del trueno"): 3,
    ("el-reto", "duelo en el monte"): 2,
    ("el-reto", "amuleto de caribu"): 2,
    ("el-reto", "aniquilar"): 2,
    ("el-reto", "iluminar"): 2,
    ("la-ira-del-nahual", "lanza wayki"): 3,
    ("la-ira-del-nahual", "totem de uktena"): 4,
    ("ragnarok", "amor de valkyria"): 2,
}


def normalize(name):
    """Remove accents, lowercase, strip special chars."""
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_only = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', ascii_only.lower().replace('_', ' ').replace('-', ' ')).strip()


def strip_variant(name):
    """Remove (v2), (v3), (Arte Alternativo) suffixes."""
    return re.sub(r'\s*\((v\d+|Arte Alternativo)\)\s*$', '', name).strip()


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- Step 0: Revert any wrong changes from old ID-based script ---
    cur.execute("UPDATE cards_card SET card_type_id = 1 WHERE name = 'Fenrir' AND card_type_id = 5")
    if cur.rowcount:
        print(f"Reverted Fenrir to Aliado")

    # --- Step 1: Fix Colgante Impio / Ojo del Padre → Oro ---
    cur.execute("SELECT id FROM cards_edition WHERE slug = 'mundo-gotico'")
    mg_row = cur.fetchone()
    if mg_row:
        mg_id = mg_row[0]
        oro_names = ['Colgante Impio', 'Colgante Impio (v2)', 'Ojo del Padre', 'Ojo del padre']
        for name in oro_names:
            cur.execute(
                "UPDATE cards_card SET card_type_id = 5 WHERE name = ? AND edition_id = ? AND card_type_id = 1",
                (name, mg_id)
            )
        print(f"Oro fixes applied (Colgante Impio / Ojo del Padre)")

    # --- Step 2: Build race map from raw JSON ---
    raw_race_map = {}  # {(edition_slug, normalized_name): race_slug}
    if os.path.exists(RAW_FILE):
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        for edition_name, races in raw_data.items():
            ed_slug = EDITION_SLUGS.get(edition_name)
            if not ed_slug:
                continue
            for race_name, cards in races.items():
                race_slug = RACE_SLUGS.get(race_name)
                if not race_slug:
                    continue
                for card in cards:
                    name = card.get("name", "").strip()
                    url = card.get("fullUrl", "").lower()
                    if any(x in url for x in ["/oros/", "/talismanes/", "/armas/", "/totems/", "/tótems/"]):
                        continue
                    raw_race_map[(ed_slug, normalize(name))] = race_slug
                    raw_race_map[(ed_slug, name.lower())] = race_slug

    # Get race IDs
    cur.execute("SELECT id, slug FROM cards_race")
    race_ids = {slug: rid for rid, slug in cur.fetchall()}
    sin_raza_id = 1

    # --- Step 3: Fix races for Sin Raza aliados ---
    cur.execute(f"""
        SELECT c.id, c.name, c.edition_id, e.slug
        FROM cards_card c
        JOIN cards_edition e ON c.edition_id = e.id
        JOIN cards_cardtype ct ON c.card_type_id = ct.id
        WHERE ct.name = 'Aliado' AND c.race_id = ?
        AND e.slug IN {PE_SLUGS}
    """, (sin_raza_id,))
    sin_raza_cards = cur.fetchall()
    print(f"\nSin Raza aliados found: {len(sin_raza_cards)}")

    fixed_race = 0
    for card_id, card_name, edition_id, ed_slug in sin_raza_cards:
        base = strip_variant(card_name)
        norm_name = normalize(card_name)
        norm_base = normalize(base)
        new_race = None

        # Try 1: raw JSON match (normalized)
        new_race = raw_race_map.get((ed_slug, norm_name)) or raw_race_map.get((ed_slug, norm_base))

        # Try 2: cross-edition raw match
        if not new_race:
            for es in PE_SLUGS:
                new_race = raw_race_map.get((es, norm_name)) or raw_race_map.get((es, norm_base))
                if new_race:
                    break

        # Try 3: base card in same edition with race
        if not new_race and base != card_name:
            cur.execute("""
                SELECT r.slug FROM cards_card c
                JOIN cards_race r ON c.race_id = r.id
                WHERE c.name = ? AND c.edition_id = ? AND c.race_id != ?
            """, (base, edition_id, sin_raza_id))
            row = cur.fetchone()
            if row:
                new_race = row[0]

        # Try 4: case-insensitive match in DB
        if not new_race:
            cur.execute(f"""
                SELECT r.slug FROM cards_card c
                JOIN cards_race r ON c.race_id = r.id
                JOIN cards_edition e ON c.edition_id = e.id
                WHERE LOWER(c.name) = LOWER(?) AND e.slug IN {PE_SLUGS} AND c.race_id != ?
                LIMIT 1
            """, (base, sin_raza_id))
            row = cur.fetchone()
            if row:
                new_race = row[0]

        # Try 5: manual mapping
        if not new_race:
            new_race = MANUAL_RACE.get((ed_slug, norm_base)) or MANUAL_RACE.get((ed_slug, norm_name))

        if new_race and new_race in race_ids:
            cur.execute("UPDATE cards_card SET race_id = ? WHERE id = ?", (race_ids[new_race], card_id))
            fixed_race += 1

    print(f"Race fixes: {fixed_race}")

    # --- Step 4: Fix misclassified types ---
    cur.execute(f"""
        SELECT c.id, c.name, e.slug
        FROM cards_card c
        JOIN cards_edition e ON c.edition_id = e.id
        JOIN cards_cardtype ct ON c.card_type_id = ct.id
        WHERE ct.name = 'Aliado' AND c.race_id = ?
        AND e.slug IN {PE_SLUGS}
    """, (sin_raza_id,))
    still_sin_raza = cur.fetchall()

    type_fixed = 0
    for card_id, card_name, ed_slug in still_sin_raza:
        norm = normalize(card_name)
        new_type = MANUAL_TYPE_FIX.get((ed_slug, norm))
        if new_type:
            cur.execute("UPDATE cards_card SET card_type_id = ? WHERE id = ?", (new_type, card_id))
            type_fixed += 1

    print(f"Type fixes: {type_fixed}")

    conn.commit()

    # --- Summary ---
    cur.execute(f"""
        SELECT c.id, c.name, e.slug
        FROM cards_card c
        JOIN cards_edition e ON c.edition_id = e.id
        JOIN cards_cardtype ct ON c.card_type_id = ct.id
        WHERE ct.name = 'Aliado' AND c.race_id = ?
        AND e.slug IN {PE_SLUGS}
    """, (sin_raza_id,))
    remaining = cur.fetchall()
    if remaining:
        print(f"\nRemaining Sin Raza aliados: {len(remaining)}")
        for r in remaining:
            print(f"  {r[1]} ({r[2]})")
    else:
        print("\nAll PE aliados have proper races!")

    conn.close()
    print("Done!")


if __name__ == "__main__":
    main()
