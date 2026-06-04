"""
Sube imágenes de cartas del blog de Vigilantes a Cloudinary.
Genera aydv_blog_vigilantes_mapping.json con el mapeo cloudinary_id → url.
"""
import os
import json
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name="dmvu6tuee",
    api_key="618467334728855",
    api_secret="egB_Ypv0wdVVBL2oRhUaoHr8bY8",
    secure=True,
)

SOURCE_DIR = "cartas-blog-vigilantes"
CLOUDINARY_FOLDER = "deckshado/myl_cards/aydv_blog_vigilantes"
MAPPING_FILE = "aydv_blog_vigilantes_mapping.json"

# Mapeo: filename → cloudinary_id
FILE_TO_ID = {
    # Kit Batalla (promos)
    "AYDV_175-1.png": "aydv_175",
    "AYDV_176-1.png": "aydv_176",
    "AYDV_179-1.png": "aydv_179",
    "AYDV_180-1.png": "aydv_180",
    "AYDV_181-1.png": "aydv_181",
    "AYDV_182-1.png": "aydv_182",
    "AYDV_183-1.png": "aydv_183",
    "AYDV_184-1.png": "aydv_184",
    "AYDV_186-1.png": "aydv_186",
    # Torneo Lanzamiento
    "AYDV_190.png": "aydv_190",
    "AYDV_191.png": "aydv_191",
    # Profecías
    "AYDV_192.png": "aydv_192",
    "AYDV_194.png": "aydv_194",
    "AYDV_195.png": "aydv_195",
    "AYDV_199.png": "aydv_199",
    # Buy-a-Box (Jinetes)
    "AYDV_213-1.png": "aydv_213",
    "AYDV_214-1.png": "aydv_214",
    "AYDV_215-1.png": "aydv_215",
    "AYDV_216-1.png": "aydv_216",
    # Secretas
    "01_Secretas_01_0-2.png": "aydv_160_s",
    "01_Secretas_01_02-1.png": "aydv_161_s",
    "01_Secretas_02-0-1.png": "aydv_167_s",
    # Ultra Secretas (Enoquiano)
    "01_Secretas_3_0-2-1.png": "aydv_us_gabriel",
    "01_Secretas_3_02-1-1.png": "aydv_us_semyazza",
    "01_Secretas_3_03-1-1.png": "aydv_us_lucifer",
    # Showcase (base set rarity examples)
    "03_ultrareales_02-2.png": "aydv_002_u",
    "04_megareales_0-1.png": "aydv_021_m",
    "07_vasallo_03-1.png": "aydv_123_v",
}


def main():
    mapping = {}
    total = len(FILE_TO_ID)

    print(f"Subiendo {total} cartas a Cloudinary ({CLOUDINARY_FOLDER})...\n")

    for i, (filename, cloud_id) in enumerate(sorted(FILE_TO_ID.items()), 1):
        filepath = os.path.join(SOURCE_DIR, filename)
        if not os.path.isfile(filepath):
            print(f"  [{i}/{total}] SKIP (no existe): {filename}")
            continue

        public_id = f"{CLOUDINARY_FOLDER}/{cloud_id}"
        print(f"  [{i}/{total}] {filename} → {cloud_id}...", end=" ", flush=True)

        try:
            result = cloudinary.uploader.upload(
                filepath,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
            )
            url = result["secure_url"]
            mapping[cloud_id] = url
            print(f"OK")
        except Exception as e:
            print(f"ERROR: {e}")

    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(mapping)} imágenes subidas. Mapeo guardado en {MAPPING_FILE}")


if __name__ == "__main__":
    main()
