import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Get PE editions
cur.execute("SELECT id, title, slug FROM cards_edition WHERE slug IN ('el-reto','mundo-gotico','la-ira-del-nahual','ragnarok','espiritu-de-dragon','escuelas_elementales','heroes_de_dharma','esc_adicionales') OR slug LIKE 'pe-%'")
editions = cur.fetchall()
print("=== Ediciones Primera Era ===")
for e in editions:
    print(f"  id={e[0]}, title={e[1]}, slug={e[2]}")

pe_ids = [e[0] for e in editions]
if not pe_ids:
    print("No PE editions found")
    exit()

# Get card types
cur.execute("SELECT id, name FROM cards_cardtype")
types = cur.fetchall()
print("\n=== Card Types ===")
for t in types:
    print(f"  id={t[0]}, name={t[1]}")

placeholders = ",".join("?" * len(pe_ids))

# All PE cards
cur.execute(f"""
    SELECT c.id, c.name, ct.name as type_name, c.custom_image_url, e.title as edition_name
    FROM cards_card c
    JOIN cards_edition e ON c.edition_id = e.id
    LEFT JOIN cards_cardtype ct ON c.card_type_id = ct.id
    WHERE e.id IN ({placeholders})
    ORDER BY ct.name, c.name
""", pe_ids)
cards = cur.fetchall()
print(f"\n=== Total PE cards: {len(cards)} ===")

# Oros mal clasificados (URL tiene oros pero tipo != Oro)
print("\n=== Oros mal clasificados (URL tiene 'oros' pero tipo != Oro) ===")
bad = []
for c in cards:
    url = (c[3] or "").lower()
    if "/oros/" in url or "/oro/" in url:
        if c[2] != "Oro":
            print(f"  [{c[2]}] {c[1]} (ed: {c[4]})")
            print(f"    URL: {c[3][:120] if c[3] else 'N/A'}")
            bad.append(c)
if not bad:
    print("  (ninguno)")

# Todas las Oro correctas
print(f"\n=== Cartas correctamente tipo Oro: ===")
for c in cards:
    if c[2] == "Oro":
        print(f"  {c[1]} (ed: {c[4]})")

# Aliados - revisar si alguno debería ser otro tipo
print(f"\n=== Cartas tipo Aliado en PE (revisar URLs) ===")
for c in cards:
    if c[2] == "Aliado":
        url = (c[3] or "").lower()
        flag = ""
        if "/oros/" in url or "/oro/" in url:
            flag = " *** DEBERIA SER ORO ***"
        elif "/armas/" in url or "/arma/" in url:
            flag = " *** DEBERIA SER ARMA ***"
        elif "/talismanes/" in url or "/talisman/" in url:
            flag = " *** DEBERIA SER TALISMAN ***"
        elif "/totems/" in url or "/totem/" in url:
            flag = " *** DEBERIA SER TOTEM ***"
        if flag:
            print(f"  {c[1]} (ed: {c[4]}){flag}")
            print(f"    URL: {c[3][:120] if c[3] else 'N/A'}")

# Check other types for mismatches too
print(f"\n=== Otras inconsistencias tipo vs URL ===")
for c in cards:
    url = (c[3] or "").lower()
    tipo = c[2]
    expected = None
    if "/oros/" in url:
        expected = "Oro"
    elif "/armas/" in url:
        expected = "Arma"
    elif "/talismanes/" in url:
        expected = "Talismán"
    elif "/totems/" in url or "/tótems/" in url:
        expected = "Tótem"
    elif "/razas/" in url:
        expected = "Aliado"

    if expected and tipo != expected:
        # Check alternate names
        if expected == "Talismán" and tipo in ("Talisman", "Talismán"):
            continue
        if expected == "Tótem" and tipo in ("Totem", "Tótem"):
            continue
        print(f"  [{tipo}] {c[1]} -> debería ser [{expected}] (ed: {c[4]})")
        print(f"    URL: {c[3][:120] if c[3] else 'N/A'}")

conn.close()
