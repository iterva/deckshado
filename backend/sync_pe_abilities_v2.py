"""
Enhanced PE ability sync - handles name mismatches between local and production.
Uses normalized name matching (case-insensitive, accent-stripped, variant aliasing).

Usage on PA:
    python sync_pe_abilities_v2.py --apply
    python sync_pe_abilities_v2.py              # dry-run (default)
"""
import os
import json
import sqlite3
import unicodedata
import re
import argparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.sqlite3")
EXPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pe_abilities_by_name.json")


def normalize(name):
    """Normalize name for fuzzy matching: lowercase, strip accents, remove special chars."""
    # Strip accents
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase
    ascii_name = ascii_name.lower().strip()
    # Remove parenthetical variant markers
    ascii_name = re.sub(r'\s*\(v\d+\)\s*', '', ascii_name)
    ascii_name = re.sub(r'\s*\(arte alternativo\)\s*', '', ascii_name)
    ascii_name = re.sub(r'\s*\(alt\)\s*', '', ascii_name)
    # Remove special characters but keep spaces
    ascii_name = re.sub(r'[^a-z0-9\s]', '', ascii_name)
    # Collapse spaces
    ascii_name = re.sub(r'\s+', ' ', ascii_name).strip()
    return ascii_name


def is_junk_name(name):
    """Detect artifact/junk card names from file names."""
    # Patterns like '226_qcrp4d', '05-Flamberge-Suiza-JO', etc.
    if re.match(r'^\d+[-_]', name):
        return True
    if re.match(r'^[a-z0-9_]+$', name) and '_' in name:
        return True
    return False


def apply_abilities(dry_run=True):
    """Apply abilities with fuzzy name matching."""
    if not os.path.exists(EXPORT_FILE):
        print(f"ERROR: {EXPORT_FILE} not found.")
        return

    with open(EXPORT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} abilities from export file.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get PE edition slugs
    needed_slugs = set(k.split("||")[1] for k in data.keys())
    placeholders = ",".join("?" * len(needed_slugs))
    cur.execute(f"SELECT id, slug FROM cards_edition WHERE slug IN ({placeholders})", list(needed_slugs))
    edition_map = {slug: eid for eid, slug in cur.fetchall()}
    print(f"Found editions: {edition_map}")

    # Build a lookup of ALL cards in PE editions: normalized_name -> [(id, name, edition_id)]
    all_pe_edition_ids = list(edition_map.values())
    if not all_pe_edition_ids:
        print("No PE editions found in DB!")
        return
    
    ph = ",".join("?" * len(all_pe_edition_ids))
    cur.execute(f"SELECT id, name, edition_id, ability FROM cards_card WHERE edition_id IN ({ph})", all_pe_edition_ids)
    db_cards = cur.fetchall()
    print(f"Total PE cards in DB: {len(db_cards)}")

    # Index by edition_id -> normalized_name -> list of (id, original_name, ability)
    db_index = {}  # {edition_id: {normalized_name: [(card_id, original_name, ability)]}}
    for card_id, name, ed_id, ability in db_cards:
        if ed_id not in db_index:
            db_index[ed_id] = {}
        norm = normalize(name)
        if norm not in db_index[ed_id]:
            db_index[ed_id][norm] = []
        db_index[ed_id][norm].append((card_id, name, ability))

    # Also index by exact name (case-insensitive) for fallback
    db_exact = {}  # {edition_id: {name_lower: [(card_id, ability)]}}
    for card_id, name, ed_id, ability in db_cards:
        if ed_id not in db_exact:
            db_exact[ed_id] = {}
        key = name.lower().strip()
        if key not in db_exact[ed_id]:
            db_exact[ed_id][key] = []
        db_exact[ed_id][key].append((card_id, ability))

    updated = 0
    already_correct = 0
    not_found = 0
    junk_skipped = 0
    not_found_list = []

    for key, ability in data.items():
        name, ed_slug = key.split("||", 1)
        ed_id = edition_map.get(ed_slug)
        if not ed_id:
            not_found += 1
            continue

        # Skip junk names
        if is_junk_name(name):
            junk_skipped += 1
            continue

        # Strategy 1: Exact name match (case-insensitive)
        found = None
        name_lower = name.lower().strip()
        if ed_id in db_exact and name_lower in db_exact[ed_id]:
            candidates = db_exact[ed_id][name_lower]
            found = candidates[0]  # (card_id, current_ability)

        # Strategy 2: Normalized match (strips accents, variant markers)
        if not found:
            norm = normalize(name)
            if ed_id in db_index and norm in db_index[ed_id]:
                candidates = db_index[ed_id][norm]
                # If export name has variant marker, try to match base card
                # Otherwise take first match
                found = (candidates[0][0], candidates[0][2])

        if not found:
            not_found += 1
            if not_found <= 20:
                not_found_list.append((name, ed_slug))
            continue

        card_id, current_ability = found
        if current_ability == ability:
            already_correct += 1
            continue

        if not dry_run:
            cur.execute("UPDATE cards_card SET ability = ? WHERE id = ?", (ability, card_id))
        updated += 1

        if updated <= 10:
            old_preview = (current_ability or "(empty)")[:60]
            new_preview = ability[:60]
            print(f"  [{card_id}] {name} ({ed_slug})")
            print(f"    OLD: {old_preview}")
            print(f"    NEW: {new_preview}")
            print()

    if not dry_run and updated > 0:
        conn.commit()

    conn.close()

    print(f"\n{'=' * 50}")
    print(f"Results:")
    print(f"  Updated:         {updated}")
    print(f"  Already correct: {already_correct}")
    print(f"  Not found:       {not_found}")
    print(f"  Junk skipped:    {junk_skipped}")
    if not_found_list:
        print(f"\n  Sample not-found (first 20):")
        for name, ed in not_found_list:
            print(f"    '{name}' in {ed}")
    if dry_run:
        print(f"\n  (DRY RUN - use --apply to save changes)")
    else:
        print(f"\n  Changes committed to database!")


def main():
    parser = argparse.ArgumentParser(description="Sync PE abilities with fuzzy name matching")
    parser.add_argument("--apply", action="store_true", help="Actually save changes")
    args = parser.parse_args()
    apply_abilities(dry_run=not args.apply)


if __name__ == "__main__":
    main()
