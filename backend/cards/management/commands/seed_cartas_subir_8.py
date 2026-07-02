"""
Seed batch 8 cards:
  - 4 new Chile Oscuro 2 cards (CHI-05, CHI-08, CHI-14, CHI-16)
  - 2 new Toolkit 26 Imperio cards (edid 15, 18)
  - Update image for CHI-15 (Túneles Secretos)

Images are uploaded to Cloudinary first, then cards are created/updated
with the Cloudinary URLs.
"""
import os
import json

import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity

# Cloudinary config
cloudinary.config(
    cloud_name=(os.environ.get("CLOUDINARY_CLOUD_NAME") or "daobfx9yb"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)

CLOUDINARY_FOLDER = "deckshado/extra_cards"

# Source images folder
SOURCE_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "cartas por subir 8",
)

# Map: source filename → cloudinary public_id (without extension)
IMAGE_MAP = {
    "C-O-2-164_005_exorcismo_de_carmen_marin.webp": "c-o-2_05",
    "C-O-2-164_008_estacion_fantasma.webp": "c-o-2_08",
    "C-O-2-164_014_machete_del_abuelo.webp": "c-o-2_14",
    "C-O-2-164_015_tuneles_secretos.webp": "c-o-2_15-v2",
    "C-O-2-164_016_hospital_san_jose.webp": "c-o-2_16",
    "tk-26-163_015_celebrar_la_muerte.webp": "tk26_15",
    "tk-26-163_018_calaveras_azucar.webp": "tk26_18",
}

CHILE_OSCURO_2_CARDS = [
    {
        "myl_id": "custom_co2_05",
        "edid": "CHI-05",
        "slug": "exorcismo-de-carmen-marin-co2",
        "name": "Exorcismo de Carmen Marín",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Elige un efecto. Puedes Botar dos cartas o Descartar una carta "
            "para elegir ambos:\n"
            "- Destierra un Cementerio. Las cartas en los Destierros pierden "
            "su habilidad durante este y los siguientes tres turnos.\n"
            "- Una carta pierde su habilidad y no puede atacar ni bloquear "
            "por el resto del juego."
        ),
        "flavour": (
            '"La endemoniada", fue el primer caso documentado de exorcismo '
            "en latinoamérica, enfrentando la visión de la iglesia y la ciencia."
        ),
        "cloudinary_id": "c-o-2_05",
    },
    {
        "myl_id": "custom_co2_08",
        "edid": "CHI-08",
        "slug": "estacion-fantasma-co2",
        "name": "Estación Fantasma",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Una vez por turno, puedes nombrar una carta que no sea Oro. "
            "Tu oponente Baraja las cartas que controle con ese nombre.\n"
            "Cuando ataques, elige hasta dos Aliados con Furia que controles "
            "para que no hagan daño este turno y tu oponente Destierre tantas "
            "cartas del fondo de su Castillo como su Fuerza."
        ),
        "flavour": (
            "Construcciones interrumpidas, destinos inconclusos. Ocultan "
            "secretos y misterios imposibles, sólo los más incautos se "
            "atreven a descubrirlos."
        ),
        "cloudinary_id": "c-o-2_08",
    },
    {
        "myl_id": "custom_co2_14",
        "edid": "CHI-14",
        "slug": "machete-del-abuelo-co2",
        "name": "Machete del Abuelo",
        "type_slug": "arma",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Una vez en tu turno, un Aliado gana Furia, 2 de Fuerza "
            "permanentemente y puedes Robar hasta tantas cartas como coste "
            "tenga más una.\n"
            "Una vez por turno, una carta que no sea Oro pierde su habilidad "
            "y es Desterrada. Esta habilidad no puede ser prevenida ni cancelada."
        ),
        "flavour": (
            "Símbolo de poder y conexión con la tierra. Protagonista de "
            "incontables relatos de una lucha contra el mal encarnado: "
            "El Diablo mismo."
        ),
        "cloudinary_id": "c-o-2_14",
    },
    {
        "myl_id": "custom_co2_16",
        "edid": "CHI-16",
        "slug": "hospital-san-jose-co2",
        "name": "Hospital San José",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Cuando entra en juego, puedes Desterrar el Cementerio de tu oponente.\n"
            "Una vez por turno, puedes Barajar hasta seis cartas de los "
            "Cementerios y Robar tantas cartas como Tótem de distinto coste controles.\n"
            "En la Fase Final oponente o cuando salga del juego, tu oponente "
            "Bota cinco cartas."
        ),
        "flavour": (
            "Utilizado para aislar a enfermos de epidemias, cientos de almas "
            "habitan aun entre sus derrumbadas habitaciones y fríos pasillos."
        ),
        "cloudinary_id": "c-o-2_16",
    },
]

TOOLKIT_26_CARDS = [
    {
        "myl_id": "custom_tk26_15",
        "edid": "15",
        "slug": "celebrar-la-muerte-tk26",
        "name": "Celebrar la Muerte",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Destierra una carta de coste 3 o menos. No se pueden jugar "
            "cartas con el mismo nombre hasta tu próximo turno. Cuando se "
            "resuelva, Baraja este Talismán en tu Castillo.\n"
            "Cuando Botes esta carta por daño oponente, puedes Desterrarlo "
            "para Barajar hasta cinco cartas de los Cementerios."
        ),
        "flavour": (
            "Carrozas y flores atraviesan calles soleadas; risas y cantos "
            "acompañan la procesión que honra a los que partieron."
        ),
        "cloudinary_id": "tk26_15",
    },
    {
        "myl_id": "custom_tk26_18",
        "edid": "18",
        "slug": "calaveras-de-azucar-tk26",
        "name": "Calaveras de Azúcar",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, muestra cartas del tope de tu Castillo "
            "hasta mostrar dos Oros de distinto nombre, ponlos en tu mano y "
            "Baraja el resto.\n"
            "En el turno oponente, puedes subirlo a tu mano para prevenir un "
            "efecto que Anule, cancele o prevenga."
        ),
        "flavour": (
            "Sonrisas dulces y colores vivos; las calaveras guardan recuerdos "
            "y alegrías de los que ya partieron."
        ),
        "cloudinary_id": "tk26_18",
    },
]


class Command(BaseCommand):
    help = "Seed batch 8 cards (Chile Oscuro 2 + Toolkit 26) with Cloudinary upload"

    def handle(self, *args, **options):
        source = os.path.normpath(SOURCE_FOLDER)
        if not os.path.isdir(source):
            self.stderr.write(f"Source folder not found: {source}")
            return

        # --- Step 1: Upload images to Cloudinary ---
        self.stdout.write(self.style.MIGRATE_HEADING("Uploading images to Cloudinary..."))
        cloudinary_urls = {}

        for filename, public_id in IMAGE_MAP.items():
            filepath = os.path.join(source, filename)
            if not os.path.isfile(filepath):
                self.stderr.write(f"  File not found: {filepath}")
                continue

            full_public_id = f"{CLOUDINARY_FOLDER}/{public_id}"
            self.stdout.write(f"  Uploading {filename}...", ending=" ")
            try:
                result = cloudinary.uploader.upload(
                    filepath,
                    public_id=full_public_id,
                    overwrite=True,
                    resource_type="image",
                )
                url = result["secure_url"]
                cloudinary_urls[public_id] = url
                self.stdout.write(self.style.SUCCESS(f"OK → {url}"))
            except Exception as e:
                self.stderr.write(f"ERROR: {e}")

        if not cloudinary_urls:
            self.stderr.write("No images uploaded! Aborting.")
            return

        # --- Step 2: Create/update cards ---
        imp_format = Format.objects.filter(code="imp").first()
        promo_rarity = Rarity.objects.filter(slug="promo").first()

        # Chile Oscuro 2
        co2_edition = Edition.objects.get(myl_id="custom_chile_oscuro_2")
        self.stdout.write(self.style.MIGRATE_HEADING(f"\nChile Oscuro 2 ({co2_edition.title})"))

        for card_data in CHILE_OSCURO_2_CARDS:
            card_type = CardType.objects.filter(slug=card_data["type_slug"]).first()
            race = None
            if card_data["race_slug"]:
                race = Race.objects.filter(slug=card_data["race_slug"]).first()

            image_url = cloudinary_urls.get(card_data["cloudinary_id"], "")
            if not image_url:
                self.stderr.write(f"  No Cloudinary URL for {card_data['name']}, skipping")
                continue

            card, created = Card.objects.update_or_create(
                myl_id=card_data["myl_id"],
                defaults={
                    "edid": card_data["edid"],
                    "slug": card_data["slug"],
                    "name": card_data["name"],
                    "edition": co2_edition,
                    "rarity": promo_rarity,
                    "race": race,
                    "card_type": card_type,
                    "cost": card_data["cost"],
                    "damage": card_data["damage"],
                    "ability": card_data["ability"],
                    "flavour": card_data["flavour"],
                    "custom_image_url": image_url,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {card.name} ({card.edid}) → {image_url}")

        # Update CHI-15 image
        chi15_url = cloudinary_urls.get("c-o-2_15-v2", "")
        if chi15_url:
            updated = Card.objects.filter(myl_id="custom_co2_15").update(
                custom_image_url=chi15_url
            )
            if updated:
                self.stdout.write(f"  Updated image: Túneles Secretos (CHI-15) → {chi15_url}")

        # Toolkit 26 Imperio
        tk26_edition = Edition.objects.get(myl_id="custom_toolkit_26_imp")
        self.stdout.write(self.style.MIGRATE_HEADING(f"\nToolkit 26 ({tk26_edition.title})"))

        for card_data in TOOLKIT_26_CARDS:
            card_type = CardType.objects.filter(slug=card_data["type_slug"]).first()
            race = None
            if card_data["race_slug"]:
                race = Race.objects.filter(slug=card_data["race_slug"]).first()

            image_url = cloudinary_urls.get(card_data["cloudinary_id"], "")
            if not image_url:
                self.stderr.write(f"  No Cloudinary URL for {card_data['name']}, skipping")
                continue

            card, created = Card.objects.update_or_create(
                myl_id=card_data["myl_id"],
                defaults={
                    "edid": card_data["edid"],
                    "slug": card_data["slug"],
                    "name": card_data["name"],
                    "edition": tk26_edition,
                    "rarity": promo_rarity,
                    "race": race,
                    "card_type": card_type,
                    "cost": card_data["cost"],
                    "damage": card_data["damage"],
                    "ability": card_data["ability"],
                    "flavour": card_data["flavour"],
                    "custom_image_url": image_url,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {card.name} ({card.edid}) → {image_url}")

        total = len(CHILE_OSCURO_2_CARDS) + len(TOOLKIT_26_CARDS)
        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {total} new cards + 1 image update (batch 8)."
        ))

        # --- Step 3: Update cloudinary_mapping.json ---
        mapping_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "cloudinary_mapping.json",
        )
        mapping_file = os.path.normpath(mapping_file)
        if os.path.isfile(mapping_file):
            with open(mapping_file, "r") as f:
                mapping = json.load(f)
            for pid, url in cloudinary_urls.items():
                ext = url.rsplit(".", 1)[-1]
                mapping.setdefault("extra_cards", {})[f"{pid}.{ext}"] = url
            with open(mapping_file, "w") as f:
                json.dump(mapping, f, indent=2)
            self.stdout.write(f"Updated {mapping_file}")
