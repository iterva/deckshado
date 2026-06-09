"""
Fix OCR/scraping artifacts in PE ability texts.

Issues fixed:
1. Stray keyword-icon prefixes (P, A, TA, AT, e, T, s, D, etc.)
2. OCR errors (Siataca -> Si ataca, Icarta -> 1 carta, etc.)
3. Missing spaces (elresto -> el resto, deun -> de un)
4. Zero-for-O substitutions (man0 -> mano)

Usage:
    python fix_ability_typos.py              # dry-run (default)
    python fix_ability_typos.py --apply      # apply to JSON + DB
"""
import os
import json
import re
import sqlite3
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE, "pe_abilities_by_name.json")
DB_PATH = os.path.join(BASE, "db.sqlite3")

# ─── Known keyword-icon prefixes to strip ───────────────────────────────────
# These are OCR artifacts from card keyword icons (speed, unblockable, etc.)
# Only match short codes (1-3 chars) that are NOT real Spanish words.

# All Spanish words that could legitimately start an ability (lowercase)
SPANISH_WORDS = {
    'un', 'una', 'uno', 'el', 'en', 'si', 'su', 'no', 'la', 'lo', 'se',
    'al', 'de', 'los', 'las', 'tu', 'tus', 'dos', 'tres', 'por', 'del',
    'mis', 'sus', 'cada', 'este', 'esta', 'todo', 'toda', 'todos', 'todas',
    'roba', 'mira', 'pon', 'elige', 'jugar', 'puedes', 'puede', 'cuando',
    'mientras', 'genera', 'destruye', 'destierra', 'baraja', 'bota',
    'descarta', 'anula', 'busca', 'sube', 'envía', 'gana', 'pierde',
    'intercambia', 'nombra', 'solo', 'sólo', 'única', 'imbloqueable',
    'para', 'hasta', 'luego', 'también', 'paga', 'pagar', 'ver',
    'da', 'dan', 'son', 'hay', 'va', 'ven', 'sal', 'pon', 'da',
    'ya', 'así', 'y', 'o', 'a', 'con', 'sin', 'ni', 'que',
    'ese', 'esa', 'eso', 'esta', 'esto', 'aquel', 'aquella',
}


def is_prefix_junk(text):
    """
    Determine if the text starts with junk prefix tokens (icon artifacts).
    Only strips tokens that are clearly NOT Spanish words (1-4 char codes like
    P, TA, AT, s, D, Ksa, Rg, S6, s0, etc.)
    """
    words = text.split()
    if not words:
        return None

    # Collect consecutive non-Spanish short tokens from the start
    junk_tokens = []
    for w in words:
        w_lower = w.lower().rstrip('.,;:')
        # If it's a real Spanish word or longer than 4 chars, stop
        if w_lower in SPANISH_WORDS or len(w) > 4:
            break
        # If it looks like a number (pure digits), it could be either
        if w.isdigit() and int(w) <= 9:
            junk_tokens.append(w)
            continue
        # If it's 1-4 chars and NOT a Spanish word, it's likely junk
        if len(w) <= 4 and w_lower not in SPANISH_WORDS:
            junk_tokens.append(w)
        else:
            break

    if not junk_tokens:
        return None

    # The prefix we'd strip
    prefix = ' '.join(junk_tokens)

    # After stripping, the remainder must start with a capital letter or known word
    remainder = text[len(prefix):].lstrip()
    if not remainder:
        return None

    first_remaining = remainder.split()[0].lower().rstrip('.,;:')
    # Only strip if what follows looks like legitimate ability text
    if remainder[0].isupper() or first_remaining in SPANISH_WORDS:
        return prefix

    return None


# ─── OCR error corrections ───────────────────────────────────────────────────
OCR_FIXES = [
    # Missing spaces
    (r'\bSiataca\b', 'Si ataca'),
    (r'\bdeun\b', 'de un'),
    (r'\belresto\b', 'el resto'),
    (r'\bdeljuego\b', 'del juego'),
    (r'\bnosea\b', 'no sea'),
    (r'^Enlu\b', 'En tu'),
    (r'\bdetu\b', 'de tu'),
    # Truncated/garbled first word (lost initial letter)
    (r'^ugar\b', 'Jugar'),
    (r'^JEn\b', 'En'),
    (r'^Vo puede\b', 'No puede'),
    # Extra/wrong characters
    (r'\bpermanentementer\b', 'permanentemente'),
    (r'\bStsale\b', 'Si sale'),
    # I/l/1 confusion (OCR)
    (r'\bIcarta\b', '1 carta'),
    (r'\bIa la\b', '1 a la'),
    (r'(?<=\s)Ia(?=\s)', '1a'),
    # 0/o confusion
    (r'\bman0\b', 'mano'),
    (r'\bman0s\b', 'manos'),
    (r'\bturnO\b', 'turno'),
    # "ada" at start (lost the C from "Cada")
    (r'^ada jugador', 'Cada jugador'),
    (r'^ada vez', 'Cada vez'),
    # "UI" that should be "1" (OCR artifact)
    (r'\bmostrar UI\b', 'mostrar 1'),
    # Clean up stray quotes before words
    (r"(?<= )'(?=jugar|elegir|primeras)", ''),
]


def clean_ability(text):
    """Apply all fixes to an ability text. Returns (cleaned_text, list_of_changes)."""
    if not text or not text.strip():
        return text, []

    original = text
    changes = []

    # Step 1: Apply OCR fixes FIRST (so "Enlu" -> "En tu" prevents bad prefix strip)
    for pattern, replacement in OCR_FIXES:
        new_text = re.sub(pattern, replacement, text)
        if new_text != text:
            changes.append(f"{pattern} → {replacement}")
            text = new_text

    # Step 2: Strip junk prefixes
    prefix = is_prefix_junk(text)
    if prefix:
        text = text[len(prefix):].lstrip()
        changes.append(f"Stripped prefix [{prefix}]")

    # Step 3: Capitalize first letter if needed
    if text and text[0].islower() and changes:
        text = text[0].upper() + text[1:]
        changes.append("Capitalized first letter")

    return text, changes


def main():
    parser = argparse.ArgumentParser(description="Fix OCR typos in PE abilities")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    args = parser.parse_args()

    # Load JSON
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} abilities from {JSON_PATH}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}\n")

    fixed_count = 0
    fixed_data = {}

    for key, ability in data.items():
        cleaned, changes = clean_ability(ability)
        fixed_data[key] = cleaned

        if changes:
            fixed_count += 1
            name = key.split("||")[0]
            print(f"  [{name}]")
            print(f"    ANTES: {ability[:100]}")
            print(f"    DESP:  {cleaned[:100]}")
            for c in changes:
                print(f"      • {c}")
            print()

    print(f"\n{'='*60}")
    print(f"Total corregidas: {fixed_count} / {len(data)}")

    if args.apply and fixed_count > 0:
        # Update JSON file
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(fixed_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ JSON actualizado: {JSON_PATH}")

        # Update database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Get PE edition IDs
        cur.execute("""
            SELECT id, slug FROM cards_edition 
            WHERE slug IN ('el-reto','mundo-gotico','la-ira-del-nahual','ragnarok-pe','espiritu-de-dragon')
        """)
        edition_map = {slug: eid for eid, slug in cur.fetchall()}

        db_updated = 0
        for key, ability in fixed_data.items():
            original = data[key]
            if ability == original:
                continue

            name, ed_slug = key.split("||", 1)
            ed_id = edition_map.get(ed_slug)
            if not ed_id:
                continue

            # Update all cards with this name in this edition
            cur.execute(
                "UPDATE cards_card SET ability = ? WHERE name = ? AND edition_id = ?",
                (ability, name, ed_id)
            )
            # Also try without variant suffix
            base_name = re.sub(r'\s*\(v\d+\)$', '', name)
            if base_name != name:
                cur.execute(
                    "UPDATE cards_card SET ability = ? WHERE name = ? AND edition_id = ?",
                    (ability, base_name, ed_id)
                )
            db_updated += cur.rowcount

        conn.commit()
        conn.close()
        print(f"✓ DB actualizada: {db_updated} filas afectadas")
    elif not args.apply and fixed_count > 0:
        print("\n(Usar --apply para aplicar los cambios)")


if __name__ == "__main__":
    main()
