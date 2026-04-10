"""
Seed Toolkit 26 cards (TK2025 edition, edids 02-11, not in MYL API).
Card data extracted manually from card images.
"""
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity

MEDIA_BASE = "https://iterva.pythonanywhere.com/media/extra_cards"

TOOLKIT_26_CARDS = [
    {
        "myl_id": "custom_tk26_02",
        "edid": "02",
        "slug": "signo-amarillo-tk26",
        "name": "Signo Amarillo",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Indesterrable.\n"
            "Cuando entra en juego, mira cuatro cartas del tope de tu Castillo. "
            "Pon una de ahí en tu mano, otra en tu Cementerio y ordena el resto.\n"
            "Puedes convertir este Oro en un Oro sin habilidad para cancelar la habilidad "
            "de una carta fuera del juego o un Oro."
        ),
        "flavour": (
            "Las máscaras caen, revelando el miedo, en Carcosa, donde la realidad se tuerce, "
            "bajo el Signo Amarillo, todo es un juego, y la cordura, en sombras, se disuelve."
        ),
        "image_file": "tk26_02.png",
    },
    {
        "myl_id": "custom_tk26_03",
        "edid": "03",
        "slug": "escarapela-nacional-tk26",
        "name": "Escarapela Nacional",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Al comienzo de la Vigilia oponente, si no controlas más Oros que él "
            "puedes ponerlo en juego como si fuera tu Vigilia y no puedes poner "
            "Oros en juego en tu próximo turno.\n"
            "Cuando entra en juego, Roba dos cartas o busca un Aliado u Oro en tu "
            "Castillo y ponlo en tu mano."
        ),
        "flavour": (
            "Escarapela verde, blanco y rojo: latido de la patria. Águila sobre nopal, "
            "cielo y sangre. Maíz y jade, plata y volcán. Honor, memoria y coraje: "
            "México se alza, libre, eterno."
        ),
        "image_file": "tk26_03.png",
    },
    {
        "myl_id": "custom_tk26_04",
        "edid": "04",
        "slug": "el-caleuche-tk26",
        "name": "El Caleuche",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "No puede ser Anulado. Elige un efecto:\n"
            "- En respuesta a que se juegue una carta sin pagar su coste o que no pueda "
            "ser Anulada, esa carta entra en juego sin habilidad por el turno. Si es "
            "Talismán, se resuelve sin efecto.\n"
            "- Baraja una carta de coste 2 o menos y Roba dos cartas."
        ),
        "flavour": (
            "Los que lo ven escuchan risas de ultratumba y gritos atrapados. Sus tripulantes, "
            "almas perdidas, te invitan a subir. Solo un brujo poderoso podría sobrevivir "
            "a esa convocatoria."
        ),
        "image_file": "tk26_04.png",
    },
    {
        "myl_id": "custom_tk26_05",
        "edid": "05",
        "slug": "tempilcahue-tk26",
        "name": "Tempilcahue",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "0",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo. Elige un efecto:\n"
            "- Busca una carta en tu Castillo, ponla en tu mano y Roba una carta. "
            "No puedes jugar más cartas este turno.\n"
            "- Paga dos Oros para Barajar cartas cuyos costes sumen hasta 4 y "
            "Robar dos cartas."
        ),
        "flavour": (
            "Guía mi alma por los mares del oeste, abuela, cuéntame de aquella tierra "
            "más allá del mar, el Ngill chenmaywe."
        ),
        "image_file": "tk26_05.png",
    },
    {
        "myl_id": "custom_tk26_06",
        "edid": "06",
        "slug": "cuervo-nocturno-tk26",
        "name": "Cuervo Nocturno",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "No puede ser Anulado. Si atacaste en tu turno anterior, tiene "
            "Exhumar en tu Cementerio.\n"
            "Puedes poner esta y otra carta de tu mano en el fondo de tu Castillo "
            "y Robar dos cartas. Sólo puedes utilizar esta habilidad de Cuervo "
            "Nocturno una vez por turno.\n"
            "Destierra seis cartas del tope del Castillo oponente."
        ),
        "flavour": (
            "\"¡Dime cuál es tu nombre en la ribera de la Noche Plutónica!\" "
            "Y el Cuervo dijo: \"Nunca más.\" - E.A. Poe."
        ),
        "image_file": "tk26_06.png",
    },
    {
        "myl_id": "custom_tk26_07",
        "edid": "07",
        "slug": "espada-de-ohiggins-tk26",
        "name": "Espada de O'Higgins",
        "type_slug": "arma",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "El portador gana 2 de Fuerza e Indesterrable.\n"
            "En tu Vigilia, una vez por turno, puedes Barajar una carta que no sea "
            "Oro o buscar un Oro en tu Castillo y ponerlo en tu mano.\n"
            "En tu Fase Final, Destierra hasta tres cartas de los Cementerios "
            "y Roba dos cartas."
        ),
        "flavour": (
            "En Rancagua, O'Higgins enfrentó lo imposible. Rodeado, sin más aliados "
            "que su coraje, luchó por la libertad. Su determinación encendió la llama "
            "de la patria, resistiendo hasta el final."
        ),
        "image_file": "tk26_07.png",
    },
    {
        "myl_id": "custom_tk26_08",
        "edid": "08",
        "slug": "templo-de-hatshepsut-tk26",
        "name": "Templo de Hatshepsut",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Cuando entra en juego, Baraja o Destierra una carta oponente de coste "
            "3 o menos.\n"
            "En tu Vigilia o al comienzo de tu Fase Final, una vez por turno, puedes "
            "Desterrar o Barajar hasta tres cartas de los Cementerios."
        ),
        "flavour": (
            "Para reinar tuvo que reinventarse y adaptarse, manteniendo a la vez su "
            "identidad y personalidad. Los señores que desempeñaron cargos bajo su mandato "
            "se sintieron orgullosos de servirla y honrarla."
        ),
        "image_file": "tk26_08.png",
    },
    {
        "myl_id": "custom_tk26_09",
        "edid": "09",
        "slug": "dia-de-los-muertos-tk26",
        "name": "Día de los Muertos",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "7",
        "damage": None,
        "ability": (
            "Reduce su coste en un Oro por cada carta que no sea Oro en juego, "
            "hasta un mínimo de 1.\n"
            "Convierte los Aliados en Aliados de Fuerza 1 con la habilidad "
            "\"No puede portar Armas\".\n"
            "Si está en tu Cementerio, el daño directo y de combate que recibe "
            "tu Castillo se reduce en dos."
        ),
        "flavour": (
            "Las calles se encienden con calaveras danzantes, flores vibrantes "
            "y velas titilantes, donde la vida celebra a la muerte en un eterno abrazo."
        ),
        "image_file": "tk26_09.png",
    },
    {
        "myl_id": "custom_tk26_10",
        "edid": "10",
        "slug": "iluminar-el-camino-tk26",
        "name": "Iluminar el Camino",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Sólo puedes jugarlo en respuesta a que tu oponente juegue su segunda "
            "carta del turno y no puede ser Anulado.\n"
            "Tu oponente sólo puede jugar una carta más de ese mismo tipo este turno "
            "y tú no puedes jugar más cartas este turno."
        ),
        "flavour": (
            "Entre sombras, las velas marcan senderos dorados, guiando a los espíritus "
            "con ternura hacia el calor del recuerdo eterno."
        ),
        "image_file": "tk26_10.png",
    },
    {
        "myl_id": "custom_tk26_11",
        "edid": "11",
        "slug": "tamales-tk26",
        "name": "Tamales",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "No puede ser afectado por Aliados.\n"
            "Tu oponente sólo puede utilizar las habilidades de Oros y cartas de "
            "coste 2 o más si no controla más copias de esa carta.\n"
            "En tu Fase Final, puedes Barajar hasta tres cartas de los Cementerios."
        ),
        "flavour": (
            "Envueltos en maíz y tradición, reposan como ofrenda sagrada, alimento "
            "de memoria para los que ya partieron."
        ),
        "image_file": "tk26_11.png",
    },
]


class Command(BaseCommand):
    help = "Seed Toolkit 26 extra cards (edids 02-11)"

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

        for card_data in TOOLKIT_26_CARDS:
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
            f"\nDone! {len(TOOLKIT_26_CARDS)} Toolkit 26 cards seeded."
        ))
