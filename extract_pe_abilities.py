"""
Extract ability text from Primera Era card images using EasyOCR.
Updates the ability field in the database for PE cards (editions 104-108).

Usage:
    python extract_pe_abilities.py              # Process all PE cards
    python extract_pe_abilities.py --edition 104  # Process specific edition
    python extract_pe_abilities.py --limit 10     # Process only first N cards
    python extract_pe_abilities.py --dry-run      # Don't save to DB
"""
import io
import os
import sys
import re
import time
import argparse
import sqlite3

import requests
import numpy as np
import cv2
from PIL import Image
import easyocr

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "db.sqlite3")
PE_EDITION_IDS = [104, 105, 106, 107, 108]

# Initialize EasyOCR reader
print("Initializing EasyOCR...")
reader = easyocr.Reader(['es'], gpu=False, verbose=False)
print("EasyOCR ready.")


def clean_ocr_text(text):
    """Post-process OCR text to fix common errors."""
    if not text:
        return ""
    
    # Remove common leading noise patterns (decorative elements read as text)
    # Pattern: sequences with digits+uppercase+symbols before actual card text
    text = re.sub(r'^[\[\](){}<>|/\\]+\s*', '', text)
    
    # Remove leading noise: short sequences with mixed digits/symbols before real text
    # Look for first Spanish keyword that likely starts the ability
    keywords = (
        r'Única|Cuando|Puede[s]?|Un[ao]?\s|El\s|Los\s|Las\s|'
        r'Jugar|Mira|Para\s|Envía|Sube|Solo\s|'
        r'Destruye|Anula|Busca|Roba|Bota|Pon|'
        r'Si\s|Este|Esta|No\s|Todos|Al\s|'
        r'Mientras|Cada|Tu[s]?\s|En\s|Dos\s'
    )
    match = re.search(keywords, text)
    if match and match.start() > 0:
        prefix = text[:match.start()]
        # Only remove prefix if it looks like noise (contains digits or symbols)
        has_digits = any(c.isdigit() for c in prefix)
        has_symbols = any(c in '<>[]{}/\\|@#$%&' for c in prefix)
        if has_digits or has_symbols:
            text = text[match.start():]
    
    # Fix "0" confused with "o" in common patterns
    # "20 más" or "20 menos" -> "2 o más/menos"
    text = re.sub(r'(\d)0\s+(m[aá]s|menos)', r'\1 o \2', text)
    # "X 0 más/menos" 
    text = re.sub(r'(\d)\s+0\s+(m[aá]s|menos)', r'\1 o \2', text)
    # "X 0 Y" where followed by a word (not a digit) - likely "o" connector
    text = re.sub(r'([a-záéíóúñ,.])\s+0\s+([a-záéíóúñA-ZÁÉÍÓÚÑ])', r'\1 o \2', text)
    # Common patterns: "atacante 0 bloqueador", "Aliado 0 Arma"
    text = re.sub(r'(atacante|bloqueador|Aliado|Arma|Tótem|Talismán|Oro)\s+0\s+', r'\1 o ', text)
    # "Coste X 0 menos/más" patterns  
    text = re.sub(r'(Coste\s+\d)\s+0\s+', r'\1 o ', text)
    # "nO" -> "no" (common EasyOCR artifact)
    text = re.sub(r'\bnO\b', 'no', text)
    
    # Fix semicolons that should be commas (common EasyOCR confusion)
    text = re.sub(r';\s+([a-záéíóúñ])', r', \1', text)
    
    # Fix common word-level errors
    text = text.replace('Mauo', 'Mano')
    text = text.replace('mauo', 'mano')
    text = text.replace('alacar', 'atacar')
    text = text.replace('Tollsmanes', 'Talismanes')
    text = text.replace('tollsmanes', 'talismanes')
    
    # Fix "1carta" -> "1 carta" (missing space after number)
    text = re.sub(r'(\d)([a-záéíóúñA-Z])', r'\1 \2', text)
    
    # Remove trailing noise (dashes, brackets etc.)
    text = re.sub(r'[\-—–]+\s*$', '', text)
    text = re.sub(r'[\[\]<>]+\s*$', '', text)
    text = re.sub(r'\s+[YyXx]\s*$', '', text)  # trailing single char
    
    # Clean multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Fix "Unica" -> "Única" (missing accent, very common card keyword)
    text = re.sub(r'^Unica\.', 'Única.', text)
    text = re.sub(r'^Unica,', 'Única,', text)
    
    # Remove trailing period only if the sentence doesn't end properly
    # Keep periods that are part of the text
    
    return text


def extract_ability_from_image(img_bytes):
    """Extract ability text from a card image using EasyOCR."""
    img = Image.open(io.BytesIO(img_bytes))
    w, h = img.size
    
    # Crop ability text area (bottom portion of card)
    top_crop = int(h * 0.77)
    bottom_crop = int(h * 0.93)
    left_crop = int(w * 0.08)
    right_crop = int(w * 0.85)
    ability_area = img.crop((left_crop, top_crop, right_crop, bottom_crop))
    
    # Convert to numpy array and scale up 2x for better OCR
    img_np = np.array(ability_area)
    img_np = cv2.resize(img_np, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # Run EasyOCR
    results = reader.readtext(img_np, detail=0, paragraph=True)
    raw_text = " ".join(results)
    
    # Clean the text
    cleaned = clean_ocr_text(raw_text)
    return cleaned


def get_pe_cards(conn, edition_ids=None, limit=None):
    """Get PE cards from database that need ability extraction."""
    edition_ids = edition_ids or PE_EDITION_IDS
    placeholders = ",".join("?" * len(edition_ids))
    
    query = f"""
        SELECT id, name, custom_image_url, edition_id
        FROM cards_card
        WHERE edition_id IN ({placeholders})
          AND custom_image_url IS NOT NULL
          AND custom_image_url != ''
          AND (ability IS NULL OR ability = '')
        ORDER BY edition_id, id
    """
    params = edition_ids
    
    if limit:
        query += " LIMIT ?"
        params = list(edition_ids) + [limit]
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor.fetchall()


def update_card_ability(conn, card_id, ability_text):
    """Update a card's ability field in the database."""
    conn.execute(
        "UPDATE cards_card SET ability = ? WHERE id = ?",
        (ability_text, card_id)
    )


def main():
    parser = argparse.ArgumentParser(description="Extract PE card abilities via OCR")
    parser.add_argument("--edition", type=int, help="Process specific edition ID")
    parser.add_argument("--limit", type=int, help="Limit number of cards to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database")
    parser.add_argument("--verbose", action="store_true", help="Print each extracted ability")
    args = parser.parse_args()
    
    edition_ids = [args.edition] if args.edition else PE_EDITION_IDS
    
    conn = sqlite3.connect(DB_PATH)
    cards = get_pe_cards(conn, edition_ids, args.limit)
    
    print(f"\nFound {len(cards)} PE cards to process.")
    if not cards:
        print("No cards need processing (all already have abilities or no image URL).")
        return
    
    success = 0
    failed = 0
    empty = 0
    
    for i, (card_id, name, url, ed_id) in enumerate(cards):
        print(f"  [{i+1}/{len(cards)}] {name} (ed={ed_id})...", end=" ", flush=True)
        
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"DOWNLOAD FAILED ({resp.status_code})")
                failed += 1
                continue
            
            ability = extract_ability_from_image(resp.content)
            
            if not ability or len(ability) < 5:
                print("EMPTY (no text detected)")
                empty += 1
                continue
            
            if args.verbose:
                print(f"\n    -> {ability}")
            else:
                print(f"OK ({len(ability)} chars)")
            
            if not args.dry_run:
                update_card_ability(conn, card_id, ability)
            
            success += 1
            
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
        
        # Small delay to avoid hammering Cloudinary
        if i > 0 and i % 50 == 0:
            if not args.dry_run:
                conn.commit()
            time.sleep(1)
    
    if not args.dry_run:
        conn.commit()
    conn.close()
    
    print(f"\n{'='*40}")
    print(f"Results: {success} extracted, {empty} empty, {failed} failed")
    print(f"Total processed: {success + empty + failed}/{len(cards)}")
    if args.dry_run:
        print("(DRY RUN - no changes saved to database)")


if __name__ == "__main__":
    main()
