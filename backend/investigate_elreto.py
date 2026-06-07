"""Investigate the El Reto ability mapping issue."""
import sqlite3
import json

DB_PATH = "db.sqlite3"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# What's at IDs 14521-14540 locally?
print("=== LOCAL DB: IDs 14521-14540 ===")
cur.execute("SELECT id, name, edition_id, ability FROM cards_card WHERE id BETWEEN 14521 AND 14540 ORDER BY id")
for r in cur.fetchall():
    print(f"  ID={r[0]} | {r[1]} | ed={r[2]} | ab={( r[3] or 'EMPTY')[:80]}")

print("\n=== LOCAL DB: El Reto (ed=104) first 20 cards ===")
cur.execute("SELECT id, name, ability FROM cards_card WHERE edition_id = 104 ORDER BY id LIMIT 20")
for r in cur.fetchall():
    print(f"  ID={r[0]} | {r[1]} | ab={(r[2] or 'EMPTY')[:80]}")

# Check pe_abilities.json - what IDs does it have for El Reto cards?
print("\n=== pe_abilities.json: first 20 entries ===")
with open("pe_abilities.json", "r", encoding="utf-8") as f:
    abilities = json.load(f)

# Get the ID range
ids = sorted(int(k) for k in abilities.keys())
print(f"  ID range: {ids[0]} - {ids[-1]}")
print(f"  Total entries: {len(ids)}")

# Check first 20 entries and what card name they map to
print("\n=== First 20 pe_abilities entries vs card names ===")
for card_id_str in list(abilities.keys())[:20]:
    card_id = int(card_id_str)
    cur.execute("SELECT name, edition_id FROM cards_card WHERE id = ?", (card_id,))
    row = cur.fetchone()
    name = row[0] if row else "NOT FOUND"
    ed = row[1] if row else "?"
    ab_preview = abilities[card_id_str][:60]
    print(f"  ID={card_id} | {name} (ed={ed}) | ab={ab_preview}")

# Check if the abilities reference card names in text that DON'T match
print("\n=== ABILITY TEXT MENTIONS DIFFERENT CARD NAME (El Reto) ===")
cur.execute("""
    SELECT id, name, ability FROM cards_card 
    WHERE edition_id = 104 AND ability != '' AND ability IS NOT NULL
    ORDER BY id LIMIT 30
""")
mismatches = 0
for card_id, name, ability in cur.fetchall():
    # Check if ability mentions a different card name
    name_lower = name.lower()
    # Look for "Cuando X entra en juego" or "X gana" patterns
    import re
    mentions = re.findall(r'Cuando (\w+(?:\s+\w+)?)\s+(?:entra|porta|sea)', ability)
    for mention in mentions:
        if mention.lower() not in name_lower and mention.lower() not in ["este", "un", "una", "el", "la"]:
            print(f"  ID={card_id} '{name}' -> ability mentions '{mention}'")
            print(f"    {ability[:100]}")
            mismatches += 1
            break

print(f"\n  Found {mismatches} obvious name mismatches in first 30 El Reto cards")

conn.close()
