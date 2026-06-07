import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Find shadow ban oros
cur.execute("SELECT id, name, edition_id, card_type_id, cost, race_id, ability, custom_image_url FROM cards_card WHERE LOWER(name) LIKE '%shadow%ban%'")
rows = cur.fetchall()
print(f"Found {len(rows)} shadow ban cards:")
for r in rows:
    print(f"  ID={r[0]} | name={r[1]} | ed={r[2]} | type={r[3]} | cost={r[4]} | race={r[5]}")
    print(f"    img: {r[7][:100] if r[7] else 'none'}")

# Find Espiritu Samurai edition
print("\nEspiritu Samurai edition:")
cur.execute("SELECT id, slug, title, format_id FROM cards_edition WHERE title LIKE '%Samur%' OR slug LIKE '%samur%'")
for r in cur.fetchall():
    print(f"  ID={r[0]} | slug={r[1]} | title={r[2]} | format={r[3]}")

# AyDV edition
print("\nAyDV editions:")
cur.execute("SELECT id, slug, title, format_id FROM cards_edition WHERE slug LIKE '%angel%' OR title LIKE '%ngeles%Demonios%'")
for r in cur.fetchall():
    print(f"  ID={r[0]} | slug={r[1]} | title={r[2]} | format={r[3]}")

# PE editions
print("\nPE editions:")
cur.execute("SELECT id, slug, title FROM cards_edition WHERE id BETWEEN 104 AND 108 ORDER BY id")
for r in cur.fetchall():
    print(f"  ID={r[0]} | slug={r[1]} | title={r[2]}")

# noraza race
print("\nnoraza:")
cur.execute("SELECT id, slug, name FROM cards_race WHERE slug = 'noraza'")
for r in cur.fetchall():
    print(f"  ID={r[0]} | slug={r[1]} | name={r[2]}")

conn.close()
