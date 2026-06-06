"""
Fix misclassified oro cards in PE - Mundo Gótico.
Cards 'Colgante Impio' and 'Ojo del Padre' (and their v2 variants)
are marked as Aliado (id=1) but should be Oro (id=5).
"""
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# IDs confirmed from check:
# 14969 - Colgante Impio
# 15041 - Ojo del Padre
# 16657 - Colgante Impio (v2)
# 16658 - Ojo del padre

card_ids = [14969, 15041, 16657, 16658]

# Verify current state
print("=== Before fix ===")
for cid in card_ids:
    cur.execute("""
        SELECT c.id, c.name, ct.name, c.card_type_id
        FROM cards_card c
        LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
        WHERE c.id = ?
    """, (cid,))
    r = cur.fetchone()
    if r:
        print(f"  id={r[0]} | {r[1]} | tipo={r[2]} (type_id={r[3]})")

# Fix: change card_type_id from 1 (Aliado) to 5 (Oro)
cur.execute("""
    UPDATE cards_card
    SET card_type_id = 5
    WHERE id IN (?, ?, ?, ?)
    AND card_type_id = 1
""", card_ids)

print(f"\nUpdated {cur.rowcount} cards")

# Verify after fix
print("\n=== After fix ===")
for cid in card_ids:
    cur.execute("""
        SELECT c.id, c.name, ct.name, c.card_type_id
        FROM cards_card c
        LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
        WHERE c.id = ?
    """, (cid,))
    r = cur.fetchone()
    if r:
        print(f"  id={r[0]} | {r[1]} | tipo={r[2]} (type_id={r[3]})")

conn.commit()
conn.close()
print("\nDone!")
