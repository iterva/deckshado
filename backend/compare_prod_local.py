"""Compare production vs local DB for PE cards."""
import requests
import sqlite3
import json

API_BASE = "https://iterva.pythonanywhere.com/api/cards/"
DB_PATH = "db.sqlite3"

def check_production():
    # Get some PE cards from production
    resp = requests.get(API_BASE, params={"search": "Abramelin el Mago", "format": "pe"}, timeout=15)
    data = resp.json()
    # Handle paginated or list response
    if isinstance(data, dict):
        results = data.get("results", [])
        count = data.get("count", len(results))
    else:
        results = data
        count = len(data)
    print(f"=== PRODUCTION: Abramelin search ({count} results) ===")
    for card in results:
        print(f"  ID={card['id']} | {card['name']} | {card.get('edition_name','')}")
        print(f"    Ability: {(card.get('ability','') or 'EMPTY')[:200]}")
        print()

    # Compare with local
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print("=== LOCAL DB: Abramelin PE ===")
    cur.execute("SELECT id, name, ability, edition_id FROM cards_card WHERE name LIKE '%Abramelin%' AND edition_id BETWEEN 104 AND 108 ORDER BY id")
    for r in cur.fetchall():
        print(f"  ID={r[0]} | {r[1]} | ed={r[3]}")
        print(f"    Ability: {(r[2] or 'EMPTY')[:200]}")
        print()

    # Check a broader sample - get random PE cards from production and compare
    print("\n=== RANDOM PE COMPARISON (El Reto, first 10) ===")
    resp2 = requests.get(API_BASE, params={"edition": "el-reto", "page_size": "10"}, timeout=15)
    data2 = resp2.json()
    results2 = data2.get("results", data2) if isinstance(data2, dict) else data2
    for card in results2:
        cur.execute("SELECT ability FROM cards_card WHERE id = ?", (card["id"],))
        local = cur.fetchone()
        local_ability = (local[0] if local else "NOT FOUND")[:80]
        prod_ability = (card.get("ability","") or "EMPTY")[:80]
        match = "OK" if local_ability == prod_ability else "MISMATCH!"
        if match == "MISMATCH!":
            print(f"  [{match}] ID={card['id']} | {card['name']}")
            print(f"    PROD:  {prod_ability}")
            print(f"    LOCAL: {local_ability}")
            print()

    # Broader check: compare 50 cards across editions
    print("\n=== BROADER MISMATCH CHECK (50 cards per edition) ===")
    editions = ["el-reto", "mundo-gotico", "la-ira-del-nahual", "ragnarok-pe", "espiritu-de-dragon"]
    total_checked = 0
    mismatches = 0
    for ed_slug in editions:
        resp3 = requests.get(API_BASE, params={"edition": ed_slug, "page_size": "50"}, timeout=15)
        data3 = resp3.json()
        results3 = data3.get("results", data3) if isinstance(data3, dict) else data3
        ed_mismatches = 0
        for card in results3:
            cur.execute("SELECT ability FROM cards_card WHERE id = ?", (card["id"],))
            local = cur.fetchone()
            local_ab = (local[0] if local else None)
            prod_ab = card.get("ability","") or ""
            if local_ab != prod_ab:
                ed_mismatches += 1
                if ed_mismatches <= 3:
                    print(f"  [{ed_slug}] ID={card['id']} {card['name']}")
                    print(f"    PROD:  {prod_ab[:100]}")
                    print(f"    LOCAL: {(local_ab or '')[:100]}")
                    print()
            total_checked += 1
        mismatches += ed_mismatches
        print(f"  {ed_slug}: {ed_mismatches}/{len(results3)} mismatches")
    
    print(f"\n  TOTAL: {mismatches}/{total_checked} mismatches")
    conn.close()

if __name__ == "__main__":
    check_production()
