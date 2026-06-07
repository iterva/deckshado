"""
Fix PE ability texts in batches.

Batch 1: Clean common OCR errors in all PE card abilities.
Batch 2: Sync variant card abilities with their base card (variants are alternate art).
Batch 3: Fix known specific mismatches (manual corrections).

Usage:
    python fix_pe_abilities.py                 # Run all batches (dry-run)
    python fix_pe_abilities.py --apply         # Actually save changes to DB
    python fix_pe_abilities.py --batch 1       # Run only batch 1
    python fix_pe_abilities.py --batch 2       # Run only batch 2

Can be run on PythonAnywhere:
    cd /home/iterva/deckshado/Proyecto-deckshado/backend
    python fix_pe_abilities.py --apply
"""
import os
import re
import sqlite3
import argparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.sqlite3")
PE_EDITION_IDS = (104, 105, 106, 107, 108)


# ──────────────────────────────────────────────
# BATCH 1: Clean OCR errors
# ──────────────────────────────────────────────

OCR_REPLACEMENTS = [
    # Common letter confusions
    (r'\bv iugarlo\b', 'jugarlo'),
    (r'\bVA Aliado\b', 'un Aliado'),
    (r'\bFala fuerza\b', '1 a la fuerza'),
    (r'\bdcaed\s*', ''),
    (r'\bI ala Fuerza\b', '1 a la Fuerza'),
    (r'\bIala Fuerza\b', '1 a la Fuerza'),
    (r'\bIala fuerza\b', '1 a la fuerza'),
    (r'\bala fuerza\b', 'a la fuerza'),
    (r'\bala Fuerza\b', 'a la Fuerza'),
    (r'\b1ala\b', '1 a la'),
    (r'\bUn aliado\b', 'Un Aliado'),  # capitalize
    (r'\bun aliado\b', 'un Aliado'),
    # "]" misread as "1" — the most common OCR error
    (r'\] carta', '1 carta'),
    (r'\] Oro', '1 Oro'),
    (r'\] a la [Ff]uerza', '1 a la Fuerza'),
    (r'\] 0 menos', '1 o menos'),
    (r'e\] ', 'el '),
    # "v" misread as "y" (conjunction)
    (r' v ', ' y '),
    # "tuoponente" -> "tu oponente"
    (r'\btuoponente\b', 'tu oponente'),
    # "Iu" / "lu" -> "tu"
    (r'\bIu\b', 'tu'),
    (r'\blu\b(?!\s*[A-Z])', 'tu'),
    # "IO" -> "no" (in context "IO puede" -> "no puede")
    (r'\bIO\b', 'no'),
    # "pponente" -> "oponente"
    (r'\bpponente\b', 'oponente'),
    # "yno" -> "y no"
    (r'\byno\b', 'y no'),
    # "vava aser" -> "vaya a ser"
    (r'\bvava aser\b', 'vaya a ser'),
    (r'\bvava a ser\b', 'vaya a ser'),
    # "bloauoado" -> "bloqueado"
    (r'\bbloauoado\b', 'bloqueado'),
    # "Wn" -> "un"
    (r'\bWn\b', 'un'),
    # "@" as "a" in context
    (r'movido@', 'movido a'),
    (r' @ ', '. '),
    # "Cadà" -> "Cada"
    (r'\bCadà\b', 'Cada'),
    # "ólo" at start -> "Sólo"
    (r'^ólo\b', 'Sólo'),
    # Trailing noise: quotes, braces
    (r'[\s]*["{}\[\]]+\s*$', ''),
    # "havan" -> "hayan"
    (r'\bhavan\b', 'hayan'),
    # "Fina" at end -> "Final"
    (r'\bFina$', 'Final'),
    (r'\bFil$', 'Final'),
    # "Maze" -> "Mazo"
    (r'\bMaze\b', 'Mazo'),
    # "Mare" -> "Mano" at end
    (r'\bMare$', 'Mano'),
    # "SU '" -> "su"
    (r"\bSU '", 'su '),
    # Common OCR digit/letter swaps
    (r'\bCoste O\b', 'Coste 0'),
    (r'\b(\d)\s*0\s*(m[aá]s|menos)', r'\1 o \2'),  # "2 0 más" -> "2 o más"
    # Missing spaces after punctuation
    (r'(\.)([A-ZÁÉÍÓÚÑ])', r'\1 \2'),
    (r'(:)([A-ZÁÉÍÓÚÑa-záéíóúñ])', r'\1 \2'),
    # "Aliados-" with trailing hyphen
    (r'Aliados-\s*([A-Z])', r'Aliados \1'),
    (r'Aliados-\s*$', 'Aliados'),
    # "Mauo" -> "Mano"
    (r'\bMauo\b', 'Mano'),
    (r'\bmauo\b', 'mano'),
    # "alacar" -> "atacar"
    (r'\balacar\b', 'atacar'),
    # "Tollsmanes" -> "Talismanes"
    (r'\bTollsmanes\b', 'Talismanes'),
    # Common noise at start
    (r'^[\[\](){}<>|/\\]+\s*', ''),
    # Trailing noise
    (r'[\-—–]+\s*$', ''),
    (r'[\[\]<>]+\s*$', ''),
    # Multiple spaces
    (r'\s{2,}', ' '),
    # "Lu Mazo" -> "tu Mazo"
    (r'\bLu Mazo\b', 'tu Mazo'),
    (r'\blu Mazo\b', 'tu Mazo'),
    # "Unica" -> "Única"
    (r'^Unica\.', 'Única.'),
    (r'^Unica,', 'Única,'),
    (r'^Unica\b', 'Única'),
    # "oponenie" -> "oponente"
    (r'\boponenie\b', 'oponente'),
    # "iuego" -> "juego"
    (r'\biuego\b', 'juego'),
    (r'\bIuego\b', 'juego'),
    # "iugar" -> "jugar"
    (r'\biugar\b', 'jugar'),
    # "buscar" that should be "jugar" near "Coste X o menos ... Cementerio sin pagar"
    # This is a specific pattern for the Abramelin-type cards
    (r'buscar un Aliado de Coste (\d+) o menos en tu Cementerio v iugarlo sin pagar su Coste',
     r'jugar un Aliado de Coste \1 o menos de tu Cementerio sin pagar su Coste'),
    (r'buscar un Aliado de Coste (\d+) o menos en tu Cementerio y jugarlo sin pagar su Coste',
     r'jugar un Aliado de Coste \1 o menos de tu Cementerio sin pagar su Coste'),
]


def clean_ability_text(text: str) -> str:
    """Apply OCR fixes to ability text."""
    if not text:
        return text
    result = text
    for pattern, replacement in OCR_REPLACEMENTS:
        result = re.sub(pattern, replacement, result)
    return result.strip()


# ──────────────────────────────────────────────
# BATCH 2: Sync variants with base cards
# ──────────────────────────────────────────────

def get_base_name(variant_name: str) -> str:
    """Get the base card name from a variant name."""
    # "Abramelin el Mago (v2)" -> "Abramelin el Mago"
    return re.sub(r'\s*\(v\d+\)\s*$', '', variant_name)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def run_batch1(cur, apply=False):
    """Clean OCR errors in all PE abilities."""
    print("\n" + "=" * 60)
    print("BATCH 1: Cleaning OCR errors in PE abilities")
    print("=" * 60)

    cur.execute("""
        SELECT id, name, ability FROM cards_card
        WHERE edition_id IN (104,105,106,107,108)
          AND ability IS NOT NULL AND ability != ''
        ORDER BY id
    """)
    cards = cur.fetchall()
    print(f"  Total PE cards with abilities: {len(cards)}")

    changes = []
    for card_id, name, ability in cards:
        cleaned = clean_ability_text(ability)
        if cleaned != ability:
            changes.append((card_id, name, ability, cleaned))

    print(f"  Cards that would be updated: {len(changes)}")

    if changes:
        print(f"\n  Sample changes (first 15):")
        for card_id, name, old, new in changes[:15]:
            print(f"    [{card_id}] {name}")
            # Show diff
            if len(old) > 80:
                old_show = old[:80] + "..."
            else:
                old_show = old
            if len(new) > 80:
                new_show = new[:80] + "..."
            else:
                new_show = new
            print(f"      OLD: {old_show}")
            print(f"      NEW: {new_show}")
            print()

    if apply and changes:
        for card_id, name, old, new in changes:
            cur.execute("UPDATE cards_card SET ability = ? WHERE id = ?", (new, card_id))
        print(f"  >>> Applied {len(changes)} updates!")
    elif changes:
        print(f"  (dry-run, use --apply to save)")

    return len(changes)


def run_batch2(cur, apply=False):
    """Sync variant abilities with their base card."""
    print("\n" + "=" * 60)
    print("BATCH 2: Syncing variant abilities with base cards")
    print("=" * 60)

    # Get all variant PE cards
    cur.execute("""
        SELECT id, name, ability, edition_id FROM cards_card
        WHERE edition_id IN (104,105,106,107,108)
          AND (name LIKE '%(v2)%' OR name LIKE '%(v3)%' OR name LIKE '%(v4)%')
        ORDER BY id
    """)
    variants = cur.fetchall()
    print(f"  Total variant PE cards: {len(variants)}")

    changes = []
    no_base = []

    for var_id, var_name, var_ability, edition_id in variants:
        base_name = get_base_name(var_name)

        # Find base card in same edition
        cur.execute("""
            SELECT id, ability FROM cards_card
            WHERE name = ? AND edition_id = ?
        """, (base_name, edition_id))
        base = cur.fetchone()

        if not base:
            no_base.append((var_id, var_name))
            continue

        base_id, base_ability = base
        if not base_ability:
            continue

        # If variant has different ability than base, mark for update
        if var_ability != base_ability:
            changes.append((var_id, var_name, var_ability, base_ability, base_name))

    print(f"  Variants that need syncing: {len(changes)}")
    if no_base:
        print(f"  Variants with no matching base card: {len(no_base)}")
        for vid, vname in no_base[:5]:
            print(f"    [{vid}] {vname}")

    if changes:
        print(f"\n  Sample changes (first 10):")
        for var_id, var_name, old, new, base_name in changes[:10]:
            print(f"    [{var_id}] {var_name} <- {base_name}")
            old_show = (old or "(empty)")[:70]
            new_show = new[:70]
            print(f"      WAS: {old_show}")
            print(f"      NOW: {new_show}")
            print()

    if apply and changes:
        for var_id, var_name, old, new, base_name in changes:
            cur.execute("UPDATE cards_card SET ability = ? WHERE id = ?", (new, var_id))
        print(f"  >>> Applied {len(changes)} updates!")
    elif changes:
        print(f"  (dry-run, use --apply to save)")

    return len(changes)


def main():
    parser = argparse.ArgumentParser(description="Fix PE ability texts in batches")
    parser.add_argument("--apply", action="store_true", help="Actually save changes")
    parser.add_argument("--batch", type=int, choices=[1, 2], help="Run specific batch only")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    total_changes = 0

    if args.batch is None or args.batch == 1:
        total_changes += run_batch1(cur, apply=args.apply)

    if args.batch is None or args.batch == 2:
        total_changes += run_batch2(cur, apply=args.apply)

    if args.apply and total_changes > 0:
        conn.commit()
        print(f"\n{'=' * 60}")
        print(f"TOTAL: {total_changes} cards updated and committed!")
    else:
        print(f"\n{'=' * 60}")
        print(f"TOTAL: {total_changes} cards would be updated (dry-run)")

    conn.close()


if __name__ == "__main__":
    main()
