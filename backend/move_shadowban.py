"""
Move Shadow Ban oros to Ángeles y Demonios edition and duplicate into all PE editions.

Usage:
    python move_shadowban.py           # dry-run
    python move_shadowban.py --apply   # actually save
"""
import os
import sqlite3
import argparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.sqlite3")

# Target editions
AYDV_EDITION_ID = 40  # Ángeles y Demonios (formato Imperio Rotado)
PE_EDITION_IDS = [104, 105, 106, 107, 108]

# Card type and race
ORO_TYPE_ID = 5
NORAZA_RACE_ID = 1
DEFAULT_RARITY_ID = 7  # Vasallo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find shadow ban cards
    cur.execute("SELECT id, name, cost, ability, custom_image_url, slug, myl_id FROM cards_card WHERE LOWER(name) LIKE '%shadow%ban%' AND card_type_id = 5")
    shadow_bans = cur.fetchall()
    print(f"Found {len(shadow_bans)} Shadow Ban oros:")
    for sb in shadow_bans:
        print(f"  ID={sb[0]} | {sb[1]} | cost={sb[2]} | img={sb[4][:60] if sb[4] else 'none'}")

    if not shadow_bans:
        print("No shadow ban cards found!")
        return

    # Step 1: Move existing cards to AyDV edition
    print(f"\n--- Step 1: Move to Ángeles y Demonios (ed={AYDV_EDITION_ID}) ---")
    for sb in shadow_bans:
        card_id = sb[0]
        print(f"  Moving ID={card_id} '{sb[1]}' from current edition to ed={AYDV_EDITION_ID}")
        if args.apply:
            cur.execute("UPDATE cards_card SET edition_id = ?, race_id = ? WHERE id = ?",
                        (AYDV_EDITION_ID, NORAZA_RACE_ID, card_id))

    # Step 2: Create copies in each PE edition
    print(f"\n--- Step 2: Create copies in PE editions ---")
    created = 0
    for pe_ed_id in PE_EDITION_IDS:
        for sb in shadow_bans:
            orig_id, name, cost, ability, img_url, slug, myl_id = sb
            
            # Check if already exists in this edition
            cur.execute("SELECT id FROM cards_card WHERE LOWER(name) = LOWER(?) AND edition_id = ?",
                        (name, pe_ed_id))
            if cur.fetchone():
                print(f"  Already exists: '{name}' in ed={pe_ed_id}, skipping")
                continue

            # Create new slug and myl_id for the copy
            new_slug = f"pe-shadow-ban-{pe_ed_id}-{orig_id}"
            new_myl_id = f"shwbn_pe_{pe_ed_id}_{created + 1}"

            print(f"  Creating '{name}' in ed={pe_ed_id} (img: {img_url[:50] if img_url else 'none'})")
            if args.apply:
                cur.execute("""
                    INSERT INTO cards_card 
                    (myl_id, edid, slug, name, cost, damage, ability, flavour,
                     card_type_id, edition_id, race_id, rarity_id, custom_image_url)
                    VALUES (?, '', ?, ?, ?, 0, ?, '', ?, ?, ?, ?, ?)
                """, (new_myl_id, new_slug, name, cost, ability or '',
                      ORO_TYPE_ID, pe_ed_id, NORAZA_RACE_ID, DEFAULT_RARITY_ID, img_url or ''))
            created += 1

    if args.apply:
        conn.commit()
        print(f"\n=== Applied: moved {len(shadow_bans)} cards, created {created} copies ===")
    else:
        print(f"\n=== DRY RUN: would move {len(shadow_bans)} cards, create {created} copies ===")
        print("  Use --apply to save changes")

    conn.close()


if __name__ == "__main__":
    main()
