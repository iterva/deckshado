"""Check PE variant cards for ability mismatches."""
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Count variant cards in PE
cur.execute("""SELECT COUNT(*) FROM cards_card 
    WHERE edition_id BETWEEN 104 AND 108 
    AND (name LIKE '%(v2)%' OR name LIKE '%(v3)%' OR name LIKE '%(v4)%')""")
print(f"Variant PE cards (v2/v3/v4): {cur.fetchone()[0]}")

# Total PE cards
cur.execute("SELECT COUNT(*) FROM cards_card WHERE edition_id BETWEEN 104 AND 108")
print(f"Total PE cards: {cur.fetchone()[0]}")

# Check if variants have same ability as base card
cur.execute("""
    SELECT c1.id, c1.name, c1.ability, c2.id, c2.name, c2.ability
    FROM cards_card c1
    JOIN cards_card c2 ON c2.name = REPLACE(REPLACE(REPLACE(c1.name, ' (v2)', ''), ' (v3)', ''), ' (v4)', '')
        AND c2.edition_id = c1.edition_id
    WHERE c1.edition_id BETWEEN 104 AND 108
        AND (c1.name LIKE '%(v2)%' OR c1.name LIKE '%(v3)%' OR c1.name LIKE '%(v4)%')
        AND c1.ability = c2.ability
        AND c1.ability != ''
""")
same_rows = cur.fetchall()
print(f"\nVariants with SAME ability as their base card: {len(same_rows)}")
for r in same_rows[:10]:
    print(f"  ID {r[0]}: {r[1]}")
    print(f"    = base ID {r[3]}: {r[4]}")
    print(f"    Text: {r[2][:100]}")
    print()

# Also check: variants that have NON-EMPTY but DIFFERENT ability from base
cur.execute("""
    SELECT c1.id, c1.name, c1.ability, c2.id, c2.name, c2.ability
    FROM cards_card c1
    JOIN cards_card c2 ON c2.name = REPLACE(REPLACE(REPLACE(c1.name, ' (v2)', ''), ' (v3)', ''), ' (v4)', '')
        AND c2.edition_id = c1.edition_id
    WHERE c1.edition_id BETWEEN 104 AND 108
        AND (c1.name LIKE '%(v2)%' OR c1.name LIKE '%(v3)%' OR c1.name LIKE '%(v4)%')
        AND c1.ability != c2.ability
        AND c1.ability != ''
        AND c2.ability != ''
""")
diff_rows = cur.fetchall()
print(f"\nVariants with DIFFERENT ability from base: {len(diff_rows)}")
for r in diff_rows[:5]:
    print(f"  ID {r[0]}: {r[1]}")
    print(f"    Variant: {r[2][:80]}")
    print(f"    Base:    {r[5][:80]}")
    print()

conn.close()
