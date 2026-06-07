"""Check PE abilities in the database."""
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Check Abramelin cards
print("=== ABRAMELIN ===")
cur.execute("SELECT id, name, ability, edition_id FROM cards_card WHERE name LIKE '%Abramelin%' ORDER BY id")
for r in cur.fetchall():
    print(f"ID={r[0]} | {r[1]} | ed={r[3]}")
    print(f"  Ability: {(r[2] or 'EMPTY')[:200]}")
    print()

# Count PE cards with/without abilities
print("\n=== STATS ===")
cur.execute("SELECT COUNT(*) FROM cards_card WHERE edition_id BETWEEN 104 AND 108 AND ability != '' AND ability IS NOT NULL")
print(f"PE cards WITH ability: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM cards_card WHERE edition_id BETWEEN 104 AND 108 AND (ability = '' OR ability IS NULL)")
print(f"PE cards WITHOUT ability: {cur.fetchone()[0]}")

# Show first 20 PE cards with abilities to check pattern
print("\n=== FIRST 20 PE CARDS WITH ABILITIES ===")
cur.execute("""
    SELECT id, name, ability, edition_id 
    FROM cards_card 
    WHERE edition_id BETWEEN 104 AND 108 AND ability != '' AND ability IS NOT NULL
    ORDER BY id
    LIMIT 20
""")
for r in cur.fetchall():
    print(f"ID={r[0]} | {r[1]} | ed={r[3]}")
    print(f"  {(r[2])[:150]}")
    print()

conn.close()
