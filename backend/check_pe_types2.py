import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Search for the specific cards visible in the screenshot
names = ['Colgante Imp', 'Ojo del padre', 'Ojo del Padre']
for name in names:
    cur.execute("""
        SELECT c.id, c.name, ct.name, c.custom_image_url, e.title, c.card_type_id
        FROM cards_card c
        JOIN cards_edition e ON c.edition_id = e.id
        LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
        WHERE c.name LIKE ?
    """, (f'%{name}%',))
    results = cur.fetchall()
    for r in results:
        url = r[3][:120] if r[3] else "N/A"
        print(f"id={r[0]} | {r[1]} | tipo={r[2]}(id={r[5]}) | ed={r[4]}")
        print(f"  URL: {url}")

print("\n=== ALL cards where tipo=Aliado but name suggests Oro ===")
cur.execute("""
    SELECT c.id, c.name, ct.name, c.custom_image_url, e.title
    FROM cards_card c
    JOIN cards_edition e ON c.edition_id = e.id
    LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
    WHERE ct.name = 'Aliado'
    AND c.custom_image_url IS NOT NULL
    AND (c.custom_image_url LIKE '%/oros/%' OR c.custom_image_url LIKE '%/oro/%'
         OR c.custom_image_url LIKE '%soporte%')
""")
for r in cur.fetchall():
    url = r[3][:120] if r[3] else "N/A"
    print(f"id={r[0]} | {r[1]} | tipo={r[2]} | ed={r[4]}")
    print(f"  URL: {url}")

# Also check: all Aliado cards in PE editions that have cost=0 and damage=0
# (oros typically have cost=0 and damage=0)
print("\n=== Aliados en PE con cost y damage (para detectar oros) ===")
cur.execute("""
    SELECT c.id, c.name, ct.name, c.cost, c.damage, e.title, c.custom_image_url
    FROM cards_card c
    JOIN cards_edition e ON c.edition_id = e.id
    LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
    WHERE ct.name = 'Aliado'
    AND e.id IN (38, 76, 78, 104, 105, 106, 107, 108)
    AND (c.cost = '0' OR c.cost IS NULL OR c.cost = '')
    AND (c.damage = '0' OR c.damage IS NULL OR c.damage = '')
    ORDER BY c.name
""")
for r in cur.fetchall():
    url = r[6][:100] if r[6] else "N/A"
    print(f"id={r[0]} | {r[1]} | tipo={r[2]} | cost={r[3]} | dmg={r[4]} | ed={r[5]}")
    print(f"  URL: {url}")

# Also search for ALL oros in all editions
print("\n=== Oros marcados como Aliado en TODAS las ediciones ===")
cur.execute("""
    SELECT c.id, c.name, ct.name, c.custom_image_url, e.title
    FROM cards_card c
    JOIN cards_edition e ON c.edition_id = e.id
    LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
    WHERE ct.name = 'Aliado'
    AND c.custom_image_url LIKE '%/oros/%'
""")
for r in cur.fetchall():
    url = r[3][:120] if r[3] else "N/A"
    print(f"id={r[0]} | {r[1]} | tipo={r[2]} | ed={r[4]}")
    print(f"  URL: {url}")

conn.close()
