"""
Seed Toolkit 26 Imperio cards (TK2025 edition, not in MYL API).
Card data extracted manually from card images.
"""
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity

MEDIA_BASE = "https://iterva.pythonanywhere.com/media/extra_cards"

TOOLKIT_26_IMP_CARDS = [
    {
        "myl_id": "custom_tk26i_25",
        "edid": "25",
        "slug": "muneco-vudu-tk26i",
        "name": "Muñeco Vudú",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "En tu Vigilia, si controlas Aliados con Furia, puedes pagarlo "
            "para mirar la mano de tu oponente. Elige un Talismán o Tótem de "
            "ahí y Barájalo. Esta habilidad no puede ser cancelada ni prevenida.\n"
            "En tu Vigilia, una vez por turno, un Aliado gana "
            "2 de Fuerza permanentemente."
        ),
        "flavour": (
            "Hilos y alfileres marcan su destino; el muñeco refleja deseos, "
            "penas y fuerzas ocultas del corazón."
        ),
        "image_file": "tk26i_25.png",
    },
    {
        "myl_id": "custom_tk26i_26",
        "edid": "26",
        "slug": "papa-legba-tk26i",
        "name": "Papa Legba",
        "type_slug": "aliado",
        "race_slug": None,
        "cost": "1",
        "damage": "4",
        "ability": (
            "Cuando entra en juego o ataque, puedes mostrar cartas del tope de "
            "tu Castillo hasta mostrar un Aliado con Furia y un Arma, pon una en "
            "tu mano y la otra en tu Cementerio. Si mostraste ambos, busca en un "
            "Castillo dos cartas con distinto nombre y Destiérralas."
        ),
        "flavour": (
            "En la encrucijada espera; abre caminos y susurra secretos antiguos, "
            "conectando el mundo terrenal con lo invisible."
        ),
        "image_file": "tk26i_26.png",
    },
    {
        "myl_id": "custom_tk26i_27",
        "edid": "27",
        "slug": "contactar-ancestros-tk26i",
        "name": "Contactar Ancestros",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Prevén que un Aliado sea Anulado, Destruido, Desterrado o cambie "
            "de controlador.\n"
            "En tu Vigilia, si no has puesto Oros en juego este turno, puedes "
            "convertir este Talismán de tu mano en un Oro sin habilidad, ponlo "
            "en tu Reserva y Roba una carta."
        ),
        "flavour": (
            "Susurros cruzan el tiempo; rituales y ofrendas conectan vivos y "
            "muertos en un hilo místico eterno."
        ),
        "image_file": "tk26i_27.png",
    },
    {
        "myl_id": "custom_tk26i_28",
        "edid": "28",
        "slug": "maldicion-vudu-tk26i",
        "name": "Maldición Vudú",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "0",
        "damage": None,
        "ability": (
            "Sólo puedes jugarlo durante tu turno.\n"
            "Cancela una habilidad o una carta en juego pierde su habilidad "
            "por el turno. En tu Fase Final mueve tus Oros a tu Oro Pagado.\n"
            "Puedes Desterrarlo de tu Cementerio para Barajar o Desterrar "
            "una carta de un Cementerio."
        ),
        "flavour": (
            "Sombras y símbolos se entrelazan; la maldición se cierne, guiando "
            "el destino con fuerza oscura y siniestra."
        ),
        "image_file": "tk26i_28.png",
    },
    {
        "myl_id": "custom_tk26i_32",
        "edid": "32",
        "slug": "medalla-de-santa-muerte-tk26i",
        "name": "Medalla de Santa Muerte",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Al comienzo del turno, puedes Descartar una carta para nombrar una "
            "carta que no sea Oro. Las cartas con ese nombre no tienen habilidad "
            "por el turno.\n"
            "Los jugadores sólo pueden jugar y/o utilizar hasta tres habilidades "
            "de Oros, cartas de coste 0 y/o de cartas fuera del juego por turno."
        ),
        "flavour": (
            "Superstición y oración se entrelazan; la medalla ofrece protección "
            "y guía bajo la mirada de la Santa Muerte."
        ),
        "image_file": "tk26i_32.png",
    },
    {
        "myl_id": "custom_tk26i_33",
        "edid": "33",
        "slug": "medalla-de-papa-legba-tk26i",
        "name": "Medalla de Papa Legba",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, puedes Robar una carta.\n"
            "En tu Vigilia, una vez por turno, si tu oponente jugó cartas y/o "
            "utilizó habilidades más de dos veces este turno y controlas Aliados "
            "con Furia, puedes poner la primera carta de su Castillo en tu Oro "
            "Pagado como un Oro sin habilidad."
        ),
        "flavour": (
            "Magia y símbolos antiguos se unen; la medalla abre caminos y "
            "conecta con fuerzas invisibles que guían destinos."
        ),
        "image_file": "tk26i_33.png",
    },
    {
        "myl_id": "custom_tk26i_34",
        "edid": "34",
        "slug": "dragon-dorado-tk26i",
        "name": "Dragón Dorado",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "0",
        "damage": None,
        "ability": (
            "Única.\n"
            "Cuando juegues este Talismán, Destiérralo.\n"
            "Anula una carta. Luego, Baraja tantas cartas de tu mano como "
            "coste tenga esa carta."
        ),
        "flavour": (
            "Su brillo es luz sagrada, guardián de sabidurías antiguas. Sus "
            "escamas resplandecen como el sol naciente, y su aliento purifica "
            "o destruye. Majestuoso y eterno, es la esperanza y el juicio para "
            "quienes se atreven a buscarlo."
        ),
        "image_file": "tk26i_34.png",
    },
    {
        "myl_id": "custom_tk26i_36",
        "edid": "36",
        "slug": "levantar-zombi-tk26i",
        "name": "Levantar Zombi",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Hasta tu próximo turno, cada vez que recibas daño oponente, "
            "tu oponente Bota esa misma cantidad y tú pones en juego un "
            "Aliado de un Cementerio como un Aliado sin habilidad.\n"
            "Puedes Desterrarlo de tu Cementerio para Barajar hasta tres "
            "cartas de los Cementerios."
        ),
        "flavour": (
            "Manos se alzan entre tierra y sombras; antiguos rituales devuelven "
            "la vida a cuerpos olvidados."
        ),
        "image_file": "tk26i_36.png",
    },
]


class Command(BaseCommand):
    help = "Seed Toolkit 26 Imperio extra cards"

    def handle(self, *args, **options):
        imp_format = Format.objects.filter(code="imp").first()
        edition, created = Edition.objects.get_or_create(
            myl_id="custom_toolkit_26_imp",
            defaults={
                "slug": "toolkit_26_imperio",
                "title": "IMP - Toolkit 26 Imperio",
                "format": imp_format,
                "active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created edition: {edition.title}"))
        else:
            self.stdout.write(f"Edition already exists: {edition.title}")

        promo_rarity = Rarity.objects.filter(slug="promo").first()

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
                    "edition": edition,
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

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {len(TOOLKIT_26_IMP_CARDS)} Toolkit 26 Imperio cards seeded."
        ))
