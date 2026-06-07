import sqlite3
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("SELECT id, slug, title FROM cards_edition WHERE id BETWEEN 100 AND 112 ORDER BY id")
for r in cur.fetchall():
    print(f"  ID={r[0]} | slug={r[1]} | title={r[2]}")
print()
cur.execute("SELECT edition_id, COUNT(*) FROM cards_card WHERE edition_id BETWEEN 100 AND 112 GROUP BY edition_id")
for r in cur.fetchall():
    print(f"  Edition {r[0]}: {r[1]} cards")

# Check not found - sample
import json
with open("pe_abilities_by_name.json","r",encoding="utf-8") as f:
    data = json.load(f)

not_found = []
editions_in_db = {}
cur.execute("SELECT id, slug FROM cards_edition")
for r in cur.fetchall():
    editions_in_db[r[1]] = r[0]

for key in data:
    name, ed_slug = key.split("||",1)
    ed_id = editions_in_db.get(ed_slug)
    if not ed_id:
        not_found.append((name, ed_slug))
        continue
    cur.execute("SELECT id FROM cards_card WHERE name = ? AND edition_id = ?", (name, ed_id))
    if not cur.fetchone():
        cur.execute("SELECT id FROM cards_card WHERE LOWER(name) = LOWER(?) AND edition_id = ?", (name, ed_id))
        if not cur.fetchone():
            not_found.append((name, ed_slug))

print(f"\nNot found total: {len(not_found)}")
print("Edition distribution of not-found:")
from collections import Counter
ed_counts = Counter(nf[1] for nf in not_found)
for ed, cnt in ed_counts.most_common():
    print(f"  {ed}: {cnt}")
print("\nSample not-found:")
for name, ed in not_found[:10]:
    print(f"  '{name}' in {ed}")

conn.close()
