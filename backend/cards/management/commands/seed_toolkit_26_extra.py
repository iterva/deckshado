"""
Seed Toolkit 26 extra cards (TK2025 edition, edids 01,13,14,16,17,19,20,21,22,23).
Card data extracted manually from card images.
"""
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity

MEDIA_BASE = "https://iterva.pythonanywhere.com/media/extra_cards"

TOOLKIT_26_EXTRA_CARDS = [
    {
        "myl_id": "custom_tk26_01",
        "edid": "01",
        "slug": "dracula-tk26",
        "name": "Drácula",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Las habilidades de este Oro no pueden ser canceladas.\n"
            "Cuando entra en juego, Roba dos cartas.\n"
            "Puedes convertirlo en un Oro sin habilidad para "
            "prevenir que una habilidad sea cancelada o "
            "un Aliado de coste 1 sea Anulado.\n"
            "Puedes Desterrarlo de tu mano o Cementerio "
            "para cancelar el ataque de hasta dos Aliados."
        ),
        "flavour": (
            "Drácula es una danza entre lo oscuro y lo sublime. "
            "El conde, vampiro eterno, acecha con sed insaciable. "
            "Castillos sombríos, barcos malditos, y Londres vulnerable son "
            "el escenario del terror inmortal."
        ),
        "image_file": "tk26_01.png",
    },
    {
        "myl_id": "custom_tk26_13",
        "edid": "13",
        "slug": "la-catrina-tk26",
        "name": "La Catrina",
        "type_slug": "aliado",
        "race_slug": None,
        "cost": "3",
        "damage": "2",
        "ability": (
            "Exhumar.\n"
            "Cuando entra en juego, Baraja las cartas oponentes que no sean "
            "Oro y por cada Oro que controle tu oponente, el Destierra la "
            "primera carta del tope de su Castillo.\n"
            "Las cartas en el Cementerio y Destierro oponente pierden su habilidad."
        ),
        "flavour": (
            "Con vestido majestuoso y mirada hueca, simboliza la unión "
            "entre lo terrenal y lo eterno en la celebración de la vida."
        ),
        "image_file": "tk26_13.png",
    },
    {
        "myl_id": "custom_tk26_14",
        "edid": "14",
        "slug": "ofrenda-a-los-abuelos-tk26",
        "name": "Ofrenda a los Abuelos",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "En respuesta a que tu oponente fuera a buscar cartas en tu "
            "Castillo o por segunda vez en su Castillo este turno, "
            "juégalo sin pagar su coste.\n"
            "Busca hasta dos cartas con distinto nombre "
            "en un Castillo y Destiérralas o prevén que tu "
            "oponente busque cartas en tu Castillo."
        ),
        "flavour": (
            "Velas titilan, aromas de pan y recuerdos; los ancestros susurran, "
            "guiando pasos con cariño eterno."
        ),
        "image_file": "tk26_14.png",
    },
    {
        "myl_id": "custom_tk26_16",
        "edid": "16",
        "slug": "guadana-de-santa-muerte-tk26",
        "name": "Guadaña de Santa Muerte",
        "type_slug": "arma",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "No puede portarse en Aliados de Fuerza 2 o 3.\n"
            "El portador gana 2 de Fuerza e Indestructible.\n"
            "Cuando entra en juego, puedes Destruir un Aliado.\n"
            "En tu Fase Final, si no controlas Aliados con "
            "Furia o Imbloqueable, agrupa un Oro y "
            "muestra cartas del tope de tu Castillo hasta "
            "mostrar un Talismán y ponlo en tu mano."
        ),
        "flavour": (
            "Entre humo de copal y pétalos, su guadaña guía a quienes "
            "veneran la Santa Muerte con fe profunda."
        ),
        "image_file": "tk26_16.png",
    },
    {
        "myl_id": "custom_tk26_17",
        "edid": "17",
        "slug": "altar-de-muertos-tk26",
        "name": "Altar de Muertos",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Cuando entra en juego, Baraja la mitad de los "
            "Aliados de cada jugador redondeado hacia "
            "arriba o una carta de coste 3 o menos.\n"
            "Una vez en tu turno, elige que tu oponente "
            "Bote dos o Destierra una carta del tope "
            "de su Castillo, por cada Tótem que controles. "
            "Si controlas dos Tótem o menos, Roba una carta."
        ),
        "flavour": (
            "Flores, velas y recuerdos se entrelazan; el altar susurra "
            "historias de aquellos que viven en memoria."
        ),
        "image_file": "tk26_17.png",
    },
    {
        "myl_id": "custom_tk26_19",
        "edid": "19",
        "slug": "red-de-plata-tk26",
        "name": "Red de Plata",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Anula o cancela la habilidad de un Aliado. "
            "Si tenía coste 2 o menos, Destierra ese Aliado.\n"
            "Puedes Desterrarlo de tu Cementerio para "
            "que un Aliado pierda su habilidad por el turno."
        ),
        "flavour": (
            "La red de la diosa lunar atrapa los sueños y promesas "
            "de un futuro impredecible."
        ),
        "image_file": "tk26_19.png",
    },
    {
        "myl_id": "custom_tk26_20",
        "edid": "20",
        "slug": "espada-vikinga-tk26",
        "name": "Espada Vikinga",
        "type_slug": "arma",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "El portador gana 2 de Fuerza.\n"
            "Cuando entra en juego, Roba dos cartas y "
            "Baraja una carta oponente de coste igual o "
            "menor a la cantidad de Aliados que controles.\n"
            "Puedes pagar un Oro y Desterrar esta carta "
            "de tu mano para Anular una carta de coste 1."
        ),
        "flavour": (
            "Su hoja lleva la furia del norte y runas grabadas "
            "en su alma de metal. Un arma fiel que canta con cada golpe, "
            "símbolo de honor y destino."
        ),
        "image_file": "tk26_20.png",
    },
    {
        "myl_id": "custom_tk26_21",
        "edid": "21",
        "slug": "carcosa-tk26",
        "name": "Carcosa",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Cuando entra en juego y al comienzo del "
            "turno oponente, Destierra una carta que no "
            "sea Oro o mira la mano de tu oponente y "
            "Destierra un Talismán de ahí. Roba una carta.\n"
            "Al comienzo de tu turno y cuando salga del "
            "juego, tu oponente Bota cuatro cartas."
        ),
        "flavour": (
            "En Carcosa, los vivos no viven, y los muertos nunca se van, "
            "la locura y el miedo conviven, en un baile eterno sin final."
        ),
        "image_file": "tk26_21.png",
    },
    {
        "myl_id": "custom_tk26_22",
        "edid": "22",
        "slug": "ritual-vudu-tk26",
        "name": "Ritual Vudú",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "En tu Vigilia, reduce su coste en un Oro por "
            "cada carta que jugó tu oponente este turno "
            "hasta un mínimo de 0 y no puedes jugar más "
            "Ritual Vudú este turno.\n"
            "Roba una carta, sube hasta un Aliado de tu "
            "Cementerio a tu mano y al comienzo de tu "
            "próximo turno genera un Oro y Roba dos cartas."
        ),
        "flavour": (
            "Tambores resuenan, humo se eleva; espíritus obedecen "
            "al ritual que une lo humano y lo invisible."
        ),
        "image_file": "tk26_22.png",
    },
    {
        "myl_id": "custom_tk26_23",
        "edid": "23",
        "slug": "rito-de-pontchartrain-tk26",
        "name": "Rito de Pontchartrain",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Elige un efecto. Si tu oponente tiene menos de "
            "veinte cartas en su Castillo, elige ambos.\n"
            "- Convierte una carta oponente en una del "
            "mismo tipo sin habilidad y Roba una carta.\n"
            "- Si tu oponente no ha recibido daño este turno, "
            "Bota cinco cartas de su Castillo y cuando se "
            "resuelva, sube esta carta a tu mano."
        ),
        "flavour": (
            "La bruma cubre el lago al amanecer; antiguos secretos "
            "despiertan mientras la ceremonia invoca fuerzas ocultas "
            "y murmullos olvidados."
        ),
        "image_file": "tk26_23.png",
    },
]


class Command(BaseCommand):
    help = "Seed Toolkit 26 extra cards (edids 01,13,14,16,17,19,20,21,22,23)"

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

        for card_data in TOOLKIT_26_EXTRA_CARDS:
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
            f"\nDone! {len(TOOLKIT_26_EXTRA_CARDS)} Toolkit 26 extra cards seeded."
        ))
