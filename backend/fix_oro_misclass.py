"""
Fix misclassified oro cards in PE - Mundo Gótico.
Cards 'Colgante Impio' and 'Ojo del Padre' (and their v2 variants)
are marked as Aliado (id=1) but should be Oro (id=5).

Uses NAME-based lookup (not IDs) to work across different DB instances.
"""
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Step 1: Revert any wrong changes from previous run (Fenrir)
cur.execute("""
    UPDATE cards_card SET card_type_id = 1
    WHERE name = 'Fenrir' AND card_type_id = 5
""")
if cur.rowcount:
    print(f"Reverted Fenrir back to Aliado ({cur.rowcount} rows)")

# Step 2: Fix by NAME - find Colgante Impio and Ojo del Padre in PE editions
card_names = ['Colgante Impio', 'Colgante Impio (v2)', 'Ojo del Padre', 'Ojo del padre']

# Get PE - Mundo Gótico edition id
cur.execute("SELECT id FROM cards_edition WHERE slug = 'mundo-gotico'")
row = cur.fetchone()
if not row:
    print("ERROR: edition 'mundo-gotico' not found")
    conn.close()
    exit(1)
mg_id = row[0]

print("=== Before fix ===")
for name in card_names:
    cur.execute("""
        SELECT c.id, c.name, ct.name, c.card_type_id
        FROM cards_card c
        LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
        WHERE c.name = ? AND c.edition_id = ?
    """, (name, mg_id))
    r = cur.fetchone()
    if r:
        print(f"  id={r[0]} | {r[1]} | tipo={r[2]} (type_id={r[3]})")
    else:
        print(f"  '{name}' not found in Mundo Gótico")

# Fix: change card_type_id from 1 (Aliado) to 5 (Oro) by name
cur.execute("""
    UPDATE cards_card
    SET card_type_id = 5
    WHERE name IN (?, ?, ?, ?)
    AND edition_id = ?
    AND card_type_id = 1
""", card_names + [mg_id])

print(f"\nUpdated {cur.rowcount} cards")

# Verify after fix
print("\n=== After fix ===")
for name in card_names:
    cur.execute("""
        SELECT c.id, c.name, ct.name, c.card_type_id
        FROM cards_card c
        LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
        WHERE c.name = ? AND c.edition_id = ?
    """, (name, mg_id))
    r = cur.fetchone()
    if r:
        print(f"  id={r[0]} | {r[1]} | tipo={r[2]} (type_id={r[3]})")

conn.commit()
conn.close()
print("\nDone!")
