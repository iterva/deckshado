"""
Export PE abilities from local DB keyed by (card_name, edition_slug).
Then apply to any DB (local or production) by name lookup.

This solves the ID mismatch between local and production databases.

Usage:
    python sync_pe_abilities.py --export       # Export from local to JSON
    python sync_pe_abilities.py --apply        # Apply JSON to current DB (by name)
    python sync_pe_abilities.py --dry-run      # Show what would change (default)

On PythonAnywhere:
    cd /home/iterva/deckshado/Proyecto-deckshado/backend
    git pull
    python sync_pe_abilities.py --apply
"""
import os
import json
import sqlite3
import argparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.sqlite3")
EXPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pe_abilities_by_name.json")

# Edition ID to slug mapping
EDITION_SLUGS = {
    104: "el-reto",
    105: "mundo-gotico",
    106: "la-ira-del-nahual",
    107: "ragnarok-pe",
    108: "espiritu-de-dragon",
}


def export_abilities():
    """Export abilities from local DB keyed by (name, edition_slug)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT c.name, e.slug, c.ability
        FROM cards_card c
        JOIN cards_edition e ON e.id = c.edition_id
        WHERE c.edition_id IN (104, 105, 106, 107, 108)
          AND c.ability IS NOT NULL AND c.ability != ''
        ORDER BY c.edition_id, c.id
    """)

    data = {}
    for name, ed_slug, ability in cur.fetchall():
        key = f"{name}||{ed_slug}"
        data[key] = ability

    conn.close()

    with open(EXPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(data)} abilities to {EXPORT_FILE}")
    return data


def apply_abilities(dry_run=True):
    """Apply abilities from JSON to DB by name + edition lookup."""
    if not os.path.exists(EXPORT_FILE):
        print(f"ERROR: {EXPORT_FILE} not found. Run with --export first.")
        return

    with open(EXPORT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} abilities from export file.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get all PE edition slugs and their IDs in THIS database
    # Dynamically find PE editions from the export keys
    needed_slugs = set(k.split("||")[1] for k in data.keys())
    placeholders = ",".join("?" * len(needed_slugs))
    cur.execute(f"SELECT id, slug FROM cards_edition WHERE slug IN ({placeholders})", list(needed_slugs))
    edition_map = {slug: eid for eid, slug in cur.fetchall()}
    print(f"Found editions: {edition_map}")

    updated = 0
    skipped = 0
    not_found = 0
    already_correct = 0

    for key, ability in data.items():
        name, ed_slug = key.split("||", 1)
        ed_id = edition_map.get(ed_slug)
        if not ed_id:
            not_found += 1
            continue

        # Find card by name + edition
        cur.execute(
            "SELECT id, ability FROM cards_card WHERE name = ? AND edition_id = ?",
            (name, ed_id)
        )
        row = cur.fetchone()
        if not row:
            # Try case-insensitive match
            cur.execute(
                "SELECT id, ability FROM cards_card WHERE LOWER(name) = LOWER(?) AND edition_id = ?",
                (name, ed_id)
            )
            row = cur.fetchone()

        if not row:
            not_found += 1
            if not_found <= 5:
                print(f"  NOT FOUND: '{name}' in {ed_slug}")
            continue

        card_id, current_ability = row
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

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'=' * 50}")
    print(f"Results:")
    print(f"  Updated:         {updated}")
    print(f"  Already correct: {already_correct}")
    print(f"  Not found:       {not_found}")
    print(f"  Skipped:         {skipped}")
    if dry_run:
        print(f"\n  (DRY RUN - use --apply to save changes)")
    else:
        print(f"\n  Changes committed to database!")


def main():
    parser = argparse.ArgumentParser(description="Sync PE abilities by name across databases")
    parser.add_argument("--export", action="store_true", help="Export abilities from local DB")
    parser.add_argument("--apply", action="store_true", help="Apply abilities to current DB")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change (default)")
    args = parser.parse_args()

    if args.export:
        export_abilities()
    elif args.apply:
        apply_abilities(dry_run=False)
    else:
        # Default: dry-run
        if not os.path.exists(EXPORT_FILE):
            print("No export file found. Exporting first...")
            export_abilities()
        apply_abilities(dry_run=True)


if __name__ == "__main__":
    main()
