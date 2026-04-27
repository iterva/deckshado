"""
Sube imágenes de backend/media/extra_cards/ a Cloudinary
y genera un JSON con el mapeo filename → cloudinary_url.
Luego actualiza la DB local (custom_image_url).
"""
import os
import sqlite3
import json
import cloudinary
import cloudinary.uploader

# Configuración
cloudinary.config(
    cloud_name="dmvu6tuee",
    api_key="618467334728855",
    api_secret="egB_Ypv0wdVVBL2oRhUaoHr8bY8",
    secure=True,
)

MEDIA_DIR = os.path.join("backend", "media", "extra_cards")
DB_PATH = os.path.join("backend", "db.sqlite3")
MAPPING_FILE = "cloudinary_mapping.json"

# También team_logos
TEAM_LOGOS_DIR = os.path.join("backend", "media", "team_logos")


def upload_folder(folder, cloudinary_folder):
    """Sube todos los archivos de una carpeta local a Cloudinary."""
    mapping = {}
    if not os.path.isdir(folder):
        print(f"  Carpeta {folder} no existe, saltando.")
        return mapping

    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    print(f"  {len(files)} archivos en {folder}")

    for i, fname in enumerate(sorted(files), 1):
        filepath = os.path.join(folder, fname)
        public_id = f"{cloudinary_folder}/{os.path.splitext(fname)[0]}"
        print(f"  [{i}/{len(files)}] Subiendo {fname}...", end=" ", flush=True)
        try:
            result = cloudinary.uploader.upload(
                filepath,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
            )
            url = result["secure_url"]
            mapping[fname] = url
            print(f"OK → {url}")
        except Exception as e:
            print(f"ERROR: {e}")
    return mapping


def update_database(extra_mapping, logo_mapping):
    """Actualiza custom_image_url en la BD para las 83 cartas."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Cartas con custom_image_url apuntando a PA
    rows = cur.execute(
        "SELECT id, custom_image_url FROM cards_card WHERE custom_image_url LIKE '%/media/extra_cards/%'"
    ).fetchall()
    print(f"\n{len(rows)} cartas a actualizar en DB")

    updated = 0
    for card_id, old_url in rows:
        # Extraer filename del URL viejo
        fname = old_url.rsplit("/", 1)[-1]
        new_url = extra_mapping.get(fname)
        if new_url:
            cur.execute("UPDATE cards_card SET custom_image_url = ? WHERE id = ?", (new_url, card_id))
            updated += 1
            print(f"  Card {card_id}: {fname} → {new_url}")
        else:
            print(f"  Card {card_id}: {fname} NO ENCONTRADO en mapping!")

    conn.commit()
    conn.close()
    print(f"\n{updated}/{len(rows)} cartas actualizadas.")


def main():
    print("=== Subiendo extra_cards a Cloudinary ===")
    extra_mapping = upload_folder(MEDIA_DIR, "deckshado/extra_cards")

    print("\n=== Subiendo team_logos a Cloudinary ===")
    logo_mapping = upload_folder(TEAM_LOGOS_DIR, "deckshado/team_logos")

    # Guardar mapping
    all_mapping = {"extra_cards": extra_mapping, "team_logos": logo_mapping}
    with open(MAPPING_FILE, "w") as f:
        json.dump(all_mapping, f, indent=2)
    print(f"\nMapping guardado en {MAPPING_FILE}")

    print("\n=== Actualizando DB local ===")
    update_database(extra_mapping, logo_mapping)

    print("\nListo! Ahora sube la DB actualizada a PythonAnywhere.")


if __name__ == "__main__":
    main()
