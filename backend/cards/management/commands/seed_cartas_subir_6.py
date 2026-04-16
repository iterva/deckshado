"""
Seed batch 6 cards:
  - 2 Chile Oscuro 2 cards (CHI-09, CHI-15)
  - 5 Toolkit 26 Imperio cards (TK2025-12, 24, 30, 31, 35)
"""
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity

MEDIA_BASE = "https://iterva.pythonanywhere.com/media/extra_cards"

CHILE_OSCURO_2_CARDS = [
    {
        "myl_id": "custom_co2_09",
        "edid": "CHI-09",
        "slug": "amarre-de-bruja-co2",
        "name": "Amarre de Bruja",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Elige un Aliado que controles de coste 2 o más y un Aliado que "
            "controle tu oponente de igual o menor Fuerza. Gana el control "
            "del Aliado oponente, mientras tu Aliado esté en juego."
        ),
        "flavour": (
            "Cuerdas y velas enlazan destinos. El amarre ata corazones y deseos "
            "con el poder antiguo y silencioso de la brujería."
        ),
        "image_file": "c-o-2_09.png",
    },
    {
        "myl_id": "custom_co2_15",
        "edid": "CHI-15",
        "slug": "tuneles-secretos-co2",
        "name": "Túneles Secretos",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Cuando entra en juego, juega una carta de tu mano o Cementerio "
            "reduciendo su coste en un Oro, hasta un mínimo de 0.\n"
            "Una vez por turno, cuando uno de tus Aliados salga del juego, "
            "puedes subirlo a tu mano.\n"
            "En tu Fase Final, Baraja y/o Destierra hasta cinco cartas de "
            "los Cementerios y Roba una carta."
        ),
        "flavour": (
            "Construidos por los jesuitas para esconder tesoros y huir de la "
            "expulsión. Una red que conecta puntos claves y secretos de la "
            "ciudad de Santiago."
        ),
        "image_file": "c-o-2_15.png",
    },
]

TOOLKIT_26_IMP_CARDS = [
    {
        "myl_id": "custom_tk26i_12",
        "edid": "12",
        "slug": "pan-de-muerto-tk26i",
        "name": "Pan de Muerto",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "En tu Vigilia, una vez por turno, puedes pagarlo para buscar un "
            "Talismán o Tótem de coste 2 o más en tu Castillo y jugarlo "
            "reduciendo su coste en un Oro.\n"
            "Sólo se puede Botar y/o Desterrar hasta quince cartas de cada "
            "Castillo por turno y tus Aliados son Indestructibles mientras bloquean."
        ),
        "flavour": (
            "Con su forma redonda y decoración de azúcar, el pan de muerto guarda "
            "en su dulzura el recuerdo de quienes siguen vivos en el corazón."
        ),
        "image_file": "tk26i_12.png",
    },
    {
        "myl_id": "custom_tk26i_24",
        "edid": "24",
        "slug": "grisgris-tk26i",
        "name": "Grisgrís",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "Durante la Vigilia de su oponente, los jugadores sólo pueden jugar "
            "hasta dos Talismanes y/o utilizar hasta dos habilidades.\n"
            "Al comienzo de la Vigilia oponente, puedes Desterrar hasta una carta "
            "de un Cementerio por cada Aliado que haya atacado en tu turno."
        ),
        "flavour": (
            "Pequeños amuletos cuelgan al viento; en sus símbolos y hechizos, "
            "se esconde poder antiguo y protección silenciosa."
        ),
        "image_file": "tk26i_24.png",
    },
    {
        "myl_id": "custom_tk26i_30",
        "edid": "30",
        "slug": "bayou-st-john-tk26i",
        "name": "Bayou St. John",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando entra en juego, Roba dos cartas.\n"
            "Una vez por turno, Descarta o Destruye una carta que controles "
            "para que hasta dos Aliados de coste 2 o menos ganen 1 de Fuerza "
            "y Furia.\n"
            "En tu Vigilia o Fase Final, Destierra hasta tres cartas del "
            "Cementerio oponente."
        ),
        "flavour": (
            "La bruma envuelve los cipreses; aguas lentas guardan secretos "
            "antiguos y ecos de rituales olvidados."
        ),
        "image_file": "tk26i_30.png",
    },
    {
        "myl_id": "custom_tk26i_31",
        "edid": "31",
        "slug": "amuleto-de-serpiente-tk26i",
        "name": "Amuleto de Serpiente",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego y al comienzo de tu Vigilia, puedes mostrar "
            "las tres primeras cartas de tu Castillo y poner un Aliado de coste "
            "1 o menos o con Furia, o un Arma de ahí en tu mano. Si lo haces, "
            "hasta tu próximo turno jugar Talismanes cuesta un Oro adicional si "
            "ese jugador ha jugado Talismanes en el turno."
        ),
        "flavour": (
            "Escamas brillan al sol; el amuleto protege y atrae astucia, poder "
            "y misterios silenciosos."
        ),
        "image_file": "tk26i_31.png",
    },
    {
        "myl_id": "custom_tk26i_35",
        "edid": "35",
        "slug": "culto-a-la-muerte-tk26i",
        "name": "Culto a la Muerte",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Elige un efecto:\n"
            "- Anula una carta de coste 2 o menos que no sea Aliado y "
            "Destierra esa carta.\n"
            "- Cancela la habilidad de una carta y tu oponente no puede "
            "utilizar más habilidades de cartas con ese nombre este turno."
        ),
        "flavour": (
            "Velas y ofrendas iluminan la fe; el culto honra a los que "
            "partieron y protege a los vivos."
        ),
        "image_file": "tk26i_35.png",
    },
]


class Command(BaseCommand):
    help = "Seed batch 6 cards (Chile Oscuro 2 + Toolkit 26 Imperio)"

    def handle(self, *args, **options):
        imp_format = Format.objects.filter(code="imp").first()
        promo_rarity = Rarity.objects.filter(slug="promo").first()

        # --- Chile Oscuro 2 ---
        co2_edition = Edition.objects.filter(myl_id="custom_chile_oscuro_2").first()
        if not co2_edition:
            co2_edition, _ = Edition.objects.get_or_create(
                myl_id="custom_chile_oscuro_2",
                defaults={
                    "slug": "chile_oscuro_2",
                    "title": "IMP - Chile Oscuro 2",
                    "format": imp_format,
                    "active": True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Created edition: {co2_edition.title}"))
        else:
            self.stdout.write(f"Edition exists: {co2_edition.title}")

        for card_data in CHILE_OSCURO_2_CARDS:
            card_type = CardType.objects.filter(slug=card_data["type_slug"]).first()
            race = None
            if card_data["race_slug"]:
                race = Race.objects.filter(slug=card_data["race_slug"]).first()

            image_url = f"{MEDIA_BASE}/{card_data['image_file']}"

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
            self.stdout.write(f"  {action}: {card.name} ({card.edid})")

        # --- Toolkit 26 Imperio ---
        tk26i_edition = Edition.objects.filter(myl_id="custom_toolkit_26_imp").first()
        if not tk26i_edition:
            tk26i_edition, _ = Edition.objects.get_or_create(
                myl_id="custom_toolkit_26_imp",
                defaults={
                    "slug": "toolkit_26_imperio",
                    "title": "IMP - Toolkit 26 Imperio",
                    "format": imp_format,
                    "active": True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Created edition: {tk26i_edition.title}"))
        else:
            self.stdout.write(f"Edition exists: {tk26i_edition.title}")

        for card_data in TOOLKIT_26_IMP_CARDS:
            card_type = CardType.objects.filter(slug=card_data["type_slug"]).first()
            race = None
            if card_data["race_slug"]:
                race = Race.objects.filter(slug=card_data["race_slug"]).first()

            image_url = f"{MEDIA_BASE}/{card_data['image_file']}"

            card, created = Card.objects.update_or_create(
                myl_id=card_data["myl_id"],
                defaults={
                    "edid": card_data["edid"],
                    "slug": card_data["slug"],
                    "name": card_data["name"],
                    "edition": tk26i_edition,
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
            self.stdout.write(f"  {action}: {card.name} ({card.edid})")

        total = len(CHILE_OSCURO_2_CARDS) + len(TOOLKIT_26_IMP_CARDS)
        self.stdout.write(self.style.SUCCESS(f"\nDone! {total} cards seeded (batch 6)."))
