import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Buscar Colgante Impio y Ojo del Padre
cur.execute("""
    SELECT c.id, c.name, ct.name, c.custom_image_url, e.title, c.card_type_id, c.cost, c.damage
    FROM cards_card c
    JOIN cards_edition e ON c.edition_id = e.id
    LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
    WHERE c.name LIKE '%Colgante%' OR c.name LIKE '%Ojo del%'
""")
for r in cur.fetchall():
    url = r[3][:150] if r[3] else "N/A"
    print(f"id={r[0]} | {r[1]} | tipo={r[2]}(id={r[5]}) | cost={r[6]} | dmg={r[7]} | ed={r[4]}")
    print(f"  URL: {url}")
    print()

# Check: all cards in PE editions that have 'soporte' in URL but tipo=Aliado
print("=== Cards con 'soporte' en URL pero tipo=Aliado ===")
cur.execute("""
    SELECT c.id, c.name, ct.name, c.custom_image_url, e.title
    FROM cards_card c
    JOIN cards_edition e ON c.edition_id = e.id
    LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
    WHERE ct.name = 'Aliado'
    AND e.id IN (38, 76, 78, 104, 105, 106, 107, 108)
    AND c.custom_image_url LIKE '%soporte%'
    ORDER BY c.name
""")
results = cur.fetchall()
print(f"Total: {len(results)}")
for r in results:
    url = r[3][:150] if r[3] else "N/A"
    print(f"  id={r[0]} | {r[1]} | tipo={r[2]} | ed={r[4]}")
    print(f"    URL: {url}")

# Check: all cards in PE editions that have 'Soporte' in URL  
print("\n=== Cards con 'Soporte' (capitalizado) en URL ===")
cur.execute("""
    SELECT c.id, c.name, ct.name, c.custom_image_url, e.title
    FROM cards_card c
    JOIN cards_edition e ON c.edition_id = e.id
    LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
    WHERE e.id IN (38, 76, 78, 104, 105, 106, 107, 108)
    AND (c.custom_image_url LIKE '%Soporte%' OR c.custom_image_url LIKE '%soporte%')
    AND ct.name != 'Oro'
    ORDER BY c.name
""")
results = cur.fetchall()
print(f"Total: {len(results)}")
for r in results:
    url = r[3][:150] if r[3] else "N/A"
    print(f"  id={r[0]} | {r[1]} | tipo={r[2]} | ed={r[4]}")
    print(f"    URL: {url}")

conn.close()
