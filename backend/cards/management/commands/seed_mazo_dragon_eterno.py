"""
Seed Mazo Imperio del Dragón + Mazo Imperio Eterno (AYDV edition).
  - Creates editions for both mazos (format=imp)
  - Uses pre-uploaded Cloudinary images
  - Creates 46 Dragon cards + 46 Eterno cards in the database

Usage:
    python manage.py seed_mazo_dragon_eterno
"""
import os
import json

from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity
from ._mapping_health import validate_mapping_urls


DRAGON_MAPPING_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "mazo_dragon_mapping.json",
)

ETERNO_MAPPING_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "mazo_eterno_mapping.json",
)

# ── Dragon Card data (46 cards) ─────────────────────────────────────
MAZO_DRAGON_CARDS = [
    {
        "myl_id": "custom_mid_01",
        "edid": "MID-01",
        "slug": "azi-raoiota-mid",
        "name": "Azi Raoiota",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "3",
        "damage": "5",
        "ability": (
            "Furia.\n"
            "Si controlas Dragones reduce su coste en un Oro.\n"
            "Una vez por turno, genera un Oro para Aliados y Destruye hasta "
            "una carta de coste 2 o menos.\n"
            "Al comienzo del turno, si está en juego o en tu Cementerio, un "
            "Oro o carta de coste 2 o menos pierde su habilidad por el turno."
        ),
        "image_file": "mazo_dragon_0.png",
        "cloudinary_id": "dragon_0",
    },
    {
        "myl_id": "custom_mid_02",
        "edid": "MID-02",
        "slug": "jormundgander-mid",
        "name": "Jormundgander",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Furia.\n"
            "Cuando entra en juego, Roba una carta.\n"
            "Cuando haga daño, puedes convertirlo en un Oro y moverlo a tu "
            "Oro Pagado.\n"
            "Si esta carta es un Oro, cuando lo pagues para jugar un Aliado, "
            "convierte este Oro en un Aliado y muévelo a tu Línea de Defensa."
        ),
        "image_file": "mazo_dragon_02.png",
        "cloudinary_id": "dragon_02",
    },
    {
        "myl_id": "custom_mid_03",
        "edid": "MID-03",
        "slug": "ofrendas-al-dragon-mid",
        "name": "Ofrendas al Dragón",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Baraja y/o Destierra hasta cuatro cartas de los Cementerios. Si "
            "Barajaste y/o Desterraste cuatro cartas de distinto tipo, genera "
            "un Oro por el turno.\n"
            "Puedes Descartar este Talismán para que un Arma o Tótem pierda "
            "su habilidad por el turno."
        ),
        "image_file": "mazo_dragon_03.png",
        "cloudinary_id": "dragon_03",
    },
    {
        "myl_id": "custom_mid_04",
        "edid": "MID-04",
        "slug": "duelo-de-dragones-mid",
        "name": "Duelo de Dragones",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Puedes jugarlo al comienzo de cualquier Fase. Cuando lo juegues, "
            "Destiérralo.\n"
            "Mira la mano de tu oponente y Destierra una carta de coste 2 o "
            "menos de ahí. Busca una carta en un Castillo y hasta dos cartas "
            "de un Cementerio y Destiérralas. Si Destierras dos o menos cartas "
            "de esta forma, Roba dos cartas."
        ),
        "image_file": "mazo_dragon_04.png",
        "cloudinary_id": "dragon_04",
    },
    {
        "myl_id": "custom_mid_05",
        "edid": "MID-05",
        "slug": "danza-de-dragones-mid",
        "name": "Danza de Dragones",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Sólo puedes jugar esta carta si controlas y/o muestras de tu "
            "mano al menos cinco Oros.\n"
            "Prevén un efecto y puedes subir hasta un Aliado u Oro de tu "
            "Cementerio a tu mano."
        ),
        "image_file": "mazo_dragon_05.png",
        "cloudinary_id": "dragon_05",
    },
    {
        "myl_id": "custom_mid_06",
        "edid": "MID-06",
        "slug": "garras-de-dragon-mid",
        "name": "Garras de Dragón",
        "type_slug": "arma",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "El portador gana Fuerza igual a su coste y no puede ser "
            "Barajado.\n"
            "Cuando entra en juego, cada jugador Bota tantas cartas como "
            "Oros controle su oponente.\n"
            "Si se Botaron Oros de esta forma, pon un Oro de un Cementerio "
            "en tu Oro Pagado."
        ),
        "image_file": "mazo_dragon_06.png",
        "cloudinary_id": "dragon_06",
    },
    {
        "myl_id": "custom_mid_07",
        "edid": "MID-07",
        "slug": "totem-del-dragon-ancestral-mid",
        "name": "Tótem del Dragón Ancestral",
        "type_slug": "totem",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Cuando entra en juego, Baraja y/o Destierra hasta tres cartas "
            "de los Cementerios y elige entre Destruir una carta de coste 2 "
            "o menos o Robar dos cartas.\n"
            "En tu turno, puedes Barajarlo para Anular un Aliado o cancelar "
            "una habilidad."
        ),
        "image_file": "mazo_dragon_07.png",
        "cloudinary_id": "dragon_07",
    },
    {
        "myl_id": "custom_mid_08",
        "edid": "MID-08",
        "slug": "escamas-de-dragon-mid",
        "name": "Escamas de Dragón",
        "type_slug": "totem",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando entra en juego, cada jugador Bota tres cartas y tú "
            "Robas una carta.\n"
            "En tu Vigilia, una vez por turno, puedes Descartar una carta "
            "para buscar una carta en tu Castillo y ponerla en tu Cementerio."
        ),
        "image_file": "mazo_dragon_08.png",
        "cloudinary_id": "dragon_08",
    },
    {
        "myl_id": "custom_mid_09",
        "edid": "MID-09",
        "slug": "corazon-de-dragon-mid",
        "name": "Corazón de Dragón",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Entra en juego como una copia de un Oro que controle tu "
            "oponente.\n"
            "En tu Vigilia, si no has puesto Oros en juego este turno, "
            "puedes ponerlo desde tu mano o Cementerio en tu Reserva."
        ),
        "image_file": "mazo_dragon_09.png",
        "cloudinary_id": "dragon_09",
    },
    {
        "myl_id": "custom_mid_10",
        "edid": "MID-10",
        "slug": "diente-de-dragon-mid",
        "name": "Diente de Dragón",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "En tu Fase Final, puedes Barajar una carta de tu mano para "
            "mostrar cartas del tope de tu Castillo hasta mostrar una carta "
            "de coste 3 o más y ponerla en tu mano.\n"
            "Cada jugador sólo puede generar Oros y jugar cartas sin pagar "
            "su coste una vez por turno."
        ),
        "image_file": "mazo_dragon_010.png",
        "cloudinary_id": "dragon_010",
    },
    {
        "myl_id": "custom_mid_11",
        "edid": "MID-11",
        "slug": "padre-dagon-mid",
        "name": "Padre Dagón",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "4",
        "damage": "6",
        "ability": (
            "No se puede Anular ni cancelar su habilidad.\n"
            "Una vez por turno, las cartas oponentes que no sean Oro pierden "
            "su habilidad y son Destruidas o prevén que uno o más Aliados "
            "sean afectados por un efecto oponente.\n"
            "Tu oponente sólo puede poner en juego hasta tres cartas por "
            "turno que no sean Oro."
        ),
        "image_file": "mazo_dragon_011.png",
        "cloudinary_id": "dragon_011",
    },
    {
        "myl_id": "custom_mid_12",
        "edid": "MID-12",
        "slug": "mecha-daikaiju-mid",
        "name": "Mecha-Daikaiju",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "3",
        "damage": "5",
        "ability": (
            "Indestructible. Indesterrable.\n"
            "Cuando entra en juego, Roba hasta tres cartas.\n"
            "Una vez en tu turno, busca en tu Castillo un Oro, ponlo en tu "
            "Oro Pagado y hasta tu próximo turno tu oponente no puede "
            "utilizar habilidades disparadas a menos que pague un Oro.\n"
            "Tus Aliados ganan 1 de Fuerza y Furia."
        ),
        "image_file": "mazo_dragon_012.png",
        "cloudinary_id": "dragon_012",
    },
    {
        "myl_id": "custom_mid_13",
        "edid": "MID-13",
        "slug": "azi-sruvara-mid",
        "name": "Azi Sruvara",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "1",
        "damage": "3",
        "ability": (
            "Cuando entra en juego, busca en tu Castillo un Aliado Azi, "
            "ponlo en tu mano y convierte una carta de coste 1 o menos en "
            "un Oro con la habilidad \"Cancelar la habilidad de tus Aliados "
            "de coste 4 o más cuesta un Oro adicional\" y muévelo a tu Oro "
            "Pagado."
        ),
        "image_file": "mazo_dragon_013.png",
        "cloudinary_id": "dragon_013",
    },
    {
        "myl_id": "custom_mid_14",
        "edid": "MID-14",
        "slug": "jabberwocky-mid",
        "name": "Jabberwocky",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "2",
        "damage": "3",
        "ability": (
            "Si no controlas Aliados de coste 1 o menos, reduce su coste en "
            "un Oro. No se puede Anular, ni cancelar su habilidad.\n"
            "Cuando entra en juego o ataca, convierte la primera carta del "
            "Castillo oponente en un Oro sin habilidad y ponlo en tu Oro "
            "Pagado."
        ),
        "image_file": "mazo_dragon_014.png",
        "cloudinary_id": "dragon_014",
    },
    {
        "myl_id": "custom_mid_15",
        "edid": "MID-15",
        "slug": "daikaiju-furioso-mid",
        "name": "Daikaiju Furioso",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "3",
        "damage": "5",
        "ability": (
            "Cuando entra en juego, tu oponente en su siguiente turno no "
            "puede atacar ni jugar más de una carta de cada tipo y tú Robas "
            "dos cartas.\n"
            "Si está en tu Cementerio, puedes pagar un Oro para convertirlo "
            "en un Oro sin habilidad y ponerlo en tu Oro Pagado.\n"
            "Los Oros oponentes pierden su habilidad."
        ),
        "image_file": "mazo_dragon_015.png",
        "cloudinary_id": "dragon_015",
    },
    {
        "myl_id": "custom_mid_16",
        "edid": "MID-16",
        "slug": "daikaiju-renacido-mid",
        "name": "Daikaiju Renacido",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "1",
        "damage": "3",
        "ability": (
            "Furia. Imbloqueable.\n"
            "Cuando haga daño, puedes Barajar una carta de coste 2 o menos "
            "o buscar un Aliado en tu Castillo y ponlo en tu mano.\n"
            "En tu Fase Final, Baraja y/o Destierra hasta tres cartas de "
            "los Cementerios."
        ),
        "image_file": "mazo_dragon_016.png",
        "cloudinary_id": "dragon_016",
    },
    {
        "myl_id": "custom_mid_17",
        "edid": "MID-17",
        "slug": "apofis-del-caos-mid",
        "name": "Apofis del Caos",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "3",
        "damage": "4",
        "ability": (
            "Furia.\n"
            "Puedes Botar tres cartas para reducir su coste en dos Oros.\n"
            "Cuando ataca, una carta y todas sus copias pierden su habilidad "
            "y no pueden atacar ni bloquear hasta tu próximo turno."
        ),
        "image_file": "mazo_dragon_017.png",
        "cloudinary_id": "dragon_017",
    },
    {
        "myl_id": "custom_mid_18",
        "edid": "MID-18",
        "slug": "azi-dahaka-mid",
        "name": "Azi Dahaka",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "4",
        "damage": "5",
        "ability": (
            "Furia. Exhumar.\n"
            "En tu Vigilia, una vez por turno, Destruye una carta que no sea "
            "Oro o busca una carta en tu Castillo y ponlo en tu mano.\n"
            "Roba dos cartas. Tus Aliados no pueden perder su habilidad y "
            "ganan 1 de Fuerza.\n"
            "Tu oponente no puede utilizar habilidades de Oros."
        ),
        "image_file": "mazo_dragon_018.png",
        "cloudinary_id": "dragon_018",
    },
    {
        "myl_id": "custom_mid_19",
        "edid": "MID-19",
        "slug": "trentren-vilu-mid",
        "name": "Trentren Vilu",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "3",
        "damage": "6",
        "ability": (
            "No puede ser jugado sin pagar su coste.\n"
            "Cuando entra en juego, puedes Barajar las demás cartas en juego "
            "que no sean Oro.\n"
            "Una vez en tu turno, puedes pagar un Oro y Botar cuatro cartas "
            "para jugar un Aliado de coste 4 o menos de tu mano o Cementerio "
            "sin pagar su coste."
        ),
        "image_file": "mazo_dragon_019.png",
        "cloudinary_id": "dragon_019",
    },
    {
        "myl_id": "custom_mid_20",
        "edid": "MID-20",
        "slug": "piruquina-mid",
        "name": "Piruquina",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "cost": "6",
        "damage": "6",
        "ability": (
            "Furia.\n"
            "Reduce su coste en un Oro por cada Oro que controles, hasta un "
            "mínimo de 1.\n"
            "Si está en tu mano, puedes pagar un Oro y ponerlo en el fondo "
            "de tu Castillo para reducir a cero el próximo daño a tu Castillo."
        ),
        "image_file": "mazo_dragon_020.png",
        "cloudinary_id": "dragon_020",
    },
    {
        "myl_id": "custom_mid_21",
        "edid": "MID-21",
        "slug": "quicavi-mid",
        "name": "Quicaví",
        "type_slug": "totem",
        "race_slug": "dragon",
        "cost": "2",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Cuando entra en juego, genera un Oro por el turno. Esta "
            "habilidad no puede ser cancelada.\n"
            "Una vez por turno, puedes hacer que hasta tu próximo turno, una "
            "carta de tu Cementerio gane Exhumar y no recibes daño de combate."
        ),
        "image_file": "mazo_dragon_021.png",
        "cloudinary_id": "dragon_021",
    },
    {
        "myl_id": "custom_mid_22",
        "edid": "MID-22",
        "slug": "abrazo-de-maipu-mid",
        "name": "Abrazo de Maipú",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "3",
        "damage": None,
        "ability": (
            "Única.\n"
            "Cuando lo juegues, Destiérralo.\n"
            "Si es Anulado, genera un Oro por el turno.\n"
            "Baraja cualquier cantidad de cartas de tu Cementerio y Destierro "
            "en tu Castillo y Roba tres cartas."
        ),
        "image_file": "mazo_dragon_022.png",
        "cloudinary_id": "dragon_022",
    },
    {
        "myl_id": "custom_mid_23",
        "edid": "MID-23",
        "slug": "vision-heroica-mid",
        "name": "Visión Heroica",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Baraja una carta de coste 3 o menos o Anula un Talismán "
            "oponente.\n"
            "Puedes pagar un Oro para subir esta carta de tu Cementerio a "
            "tu mano y Robar una carta."
        ),
        "image_file": "mazo_dragon_023.png",
        "cloudinary_id": "dragon_023",
    },
    {
        "myl_id": "custom_mid_24",
        "edid": "MID-24",
        "slug": "ciempies-sp-mid",
        "name": "Ciempiés-SP",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Anula una carta de coste 3 o menos."
        ),
        "image_file": "mazo_dragon_024.png",
        "cloudinary_id": "dragon_024",
    },
    {
        "myl_id": "custom_mid_25",
        "edid": "MID-25",
        "slug": "tempilcahue-mid",
        "name": "Tempilcahue",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "0",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Elige un efecto:\n"
            "- Busca una carta en tu Castillo, ponla en tu mano y Roba una "
            "carta. No puedes jugar más cartas este turno.\n"
            "- Paga dos Oros para Barajar cartas cuyos costes sumen hasta 4 "
            "y Robar dos cartas."
        ),
        "image_file": "mazo_dragon_025.png",
        "cloudinary_id": "dragon_025",
    },
    {
        "myl_id": "custom_mid_26",
        "edid": "MID-26",
        "slug": "el-caleuche-mid",
        "name": "El Caleuche",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "No puede ser Anulado.\n"
            "Elige un efecto:\n"
            "- En respuesta a que se juegue una carta sin pagar su coste o "
            "que no pueda ser Anulada, esa carta entra en juego sin habilidad "
            "por el turno. Si es Talismán, se resuelve sin efecto.\n"
            "- Baraja una carta de coste 2 o menos y Roba dos cartas."
        ),
        "image_file": "mazo_dragon_026.png",
        "cloudinary_id": "dragon_026",
    },
    {
        "myl_id": "custom_mid_27",
        "edid": "MID-27",
        "slug": "red-de-plata-mid",
        "name": "Red de Plata",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Anula o cancela la habilidad de un Aliado. Si tenía coste 2 o "
            "menos, Destierra ese Aliado.\n"
            "Puedes Desterrarlo de tu Cementerio para que un Aliado pierda "
            "su habilidad por el turno."
        ),
        "image_file": "mazo_dragon_027.png",
        "cloudinary_id": "dragon_027",
    },
    {
        "myl_id": "custom_mid_28",
        "edid": "MID-28",
        "slug": "activar-tenshi-z-mid",
        "name": "Activar Tenshi Z",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Muestra cartas del tope de tu Castillo hasta mostrar un Oro y "
            "un Arma o Tótem. Pon el Oro en tu Oro Pagado, la otra carta en "
            "tu mano y Baraja el resto.\n"
            "Puedes Desterrarlo de tu Cementerio para que una carta pierda "
            "su habilidad por el turno."
        ),
        "image_file": "mazo_dragon_028.png",
        "cloudinary_id": "dragon_028",
    },
    {
        "myl_id": "custom_mid_29",
        "edid": "MID-29",
        "slug": "energia-suprema-mid",
        "name": "Energía Suprema",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Para jugarlo, muestra un Arma o Tótem de tu mano o Cementerio "
            "y Destierra este Talismán.\n"
            "Genera dos Oros para jugar un Aliado de coste 3 o más. Cuando "
            "los uses, Baraja hasta tantas cartas de los Cementerios como "
            "coste tenga ese Aliado y Roba esa misma cantidad de cartas."
        ),
        "image_file": "mazo_dragon_029.png",
        "cloudinary_id": "dragon_029",
    },
    {
        "myl_id": "custom_mid_30",
        "edid": "MID-30",
        "slug": "golpe-solar-mid",
        "name": "Golpe Solar",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando juegues esta carta, Destiérralo.\n"
            "Descarta hasta dos cartas y juega un Aliado de tu mano o "
            "Cementerio reduciendo su coste en tantos Oros como cartas hayas "
            "Descartado, hasta un mínimo de 0.\n"
            "Baraja hasta una carta oponente de coste 2 o menos."
        ),
        "image_file": "mazo_dragon_030.png",
        "cloudinary_id": "dragon_030",
    },
    {
        "myl_id": "custom_mid_31",
        "edid": "MID-31",
        "slug": "sheut-mid",
        "name": "Sheut",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Si controlas menos Oros que tu oponente, puedes jugarlo por un "
            "Oro menos. Cuando lo juegues, Destiérralo.\n"
            "Anula un Aliado o Tótem, de coste 1 o menos, o cancela la "
            "habilidad de una carta."
        ),
        "image_file": "mazo_dragon_031.png",
        "cloudinary_id": "dragon_031",
    },
    {
        "myl_id": "custom_mid_32",
        "edid": "MID-32",
        "slug": "duelo-espacial-mid",
        "name": "Duelo Espacial",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Busca una carta en un Castillo o Cementerio y ponlo en tu Oro "
            "Pagado como un Oro sin habilidad. Este efecto no puede ser "
            "prevenido.\n"
            "En tu Cementerio, no puede ser Desterrado y gana la habilidad "
            "\"En tu Vigilia, puedes Robar una carta. Sólo puedes utilizar "
            "esta habilidad de Duelo Espacial una vez por turno\"."
        ),
        "image_file": "mazo_dragon_032.png",
        "cloudinary_id": "dragon_032",
    },
    {
        "myl_id": "custom_mid_33",
        "edid": "MID-33",
        "slug": "acabar-la-esperanza-mid",
        "name": "Acabar La Esperanza",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Si es Anulado, genera un Oro y Roba una carta.\n"
            "Convierte un Oro o carta de coste 3 o menos en una carta del "
            "mismo tipo, sin habilidad.\n"
            "Muestra cartas del tope de tu Castillo hasta mostrar hasta dos "
            "cartas de ese tipo, ponlas en tu mano y Baraja el resto."
        ),
        "image_file": "mazo_dragon_033.png",
        "cloudinary_id": "dragon_033",
    },
    {
        "myl_id": "custom_mid_34",
        "edid": "MID-34",
        "slug": "dragon-dorado-mid",
        "name": "Dragón Dorado",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "0",
        "damage": None,
        "ability": (
            "Única.\n"
            "Cuando juegues este Talismán, Destiérralo.\n"
            "Anula una carta. Luego, Baraja tantas cartas de tu mano como "
            "coste tenga."
        ),
        "image_file": "mazo_dragon_034.png",
        "cloudinary_id": "dragon_034",
    },
    {
        "myl_id": "custom_mid_35",
        "edid": "MID-35",
        "slug": "cuervo-nocturno-mid",
        "name": "Cuervo Nocturno",
        "type_slug": "talisman",
        "race_slug": "dragon",
        "cost": "2",
        "damage": None,
        "ability": (
            "No puede ser Anulado. Si atacaste en tu turno anterior, tiene "
            "Exhumar en tu Cementerio.\n"
            "Puedes poner esta y otra carta de tu mano en el fondo de tu "
            "Castillo y Robar dos cartas. Sólo puedes utilizar esta habilidad "
            "de Cuervo Nocturno una vez por turno.\n"
            "Destierra seis cartas del tope del Castillo oponente."
        ),
        "image_file": "mazo_dragon_035.png",
        "cloudinary_id": "dragon_035",
    },
    {
        "myl_id": "custom_mid_36",
        "edid": "MID-36",
        "slug": "patria-vieja-mid",
        "name": "Patria Vieja",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "En tu Vigilia, si no has puesto Oros en juego este turno, puedes "
            "mirar las primeras seis cartas de tu Castillo y poner un Oro de "
            "ahí en tu Reserva. Esta habilidad no puede ser cancelada.\n"
            "Tus Aliados de coste 1 o más ganan 1 de Fuerza y no son "
            "Destruidos cuando bloquean."
        ),
        "image_file": "mazo_dragon_036.png",
        "cloudinary_id": "dragon_036",
    },
    {
        "myl_id": "custom_mid_37",
        "edid": "MID-37",
        "slug": "escarapela-nacional-mid",
        "name": "Escarapela Nacional",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Al comienzo de la Vigilia oponente, si no controlas más Oros que "
            "él puedes ponerlo en juego como si fuera tu Vigilia y no puedes "
            "poner Oros en juego en tu próximo turno.\n"
            "Cuando entra en juego, Roba dos cartas o busca un Aliado u Oro "
            "en tu Castillo y ponlo en tu mano."
        ),
        "image_file": "mazo_dragon_037.png",
        "cloudinary_id": "dragon_037",
    },
    {
        "myl_id": "custom_mid_38",
        "edid": "MID-38",
        "slug": "dracula-mid",
        "name": "Drácula",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Las habilidades de este Oro no pueden ser canceladas.\n"
            "Cuando entra en juego, Roba dos cartas.\n"
            "Puedes convertirlo en un Oro sin habilidad para prevenir que "
            "una habilidad sea cancelada o un Aliado de coste 1 sea Anulado.\n"
            "Puedes Desterrarlo de tu mano o Cementerio para cancelar el "
            "ataque de hasta dos Aliados."
        ),
        "image_file": "mazo_dragon_038.png",
        "cloudinary_id": "dragon_038",
    },
    {
        "myl_id": "custom_mid_39",
        "edid": "MID-39",
        "slug": "signo-amarillo-mid",
        "name": "Signo Amarillo",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Indesterrable.\n"
            "Cuando entra en juego, mira cuatro cartas del tope de tu "
            "Castillo. Pon una de ahí en tu mano, otra en tu Cementerio y "
            "ordena el resto.\n"
            "Puedes convertir este Oro en un Oro sin habilidad para cancelar "
            "la habilidad de una carta fuera del juego o un Oro."
        ),
        "image_file": "mazo_dragon_039.png",
        "cloudinary_id": "dragon_039",
    },
    {
        "myl_id": "custom_mid_40",
        "edid": "MID-40",
        "slug": "aegishjalmur-mid",
        "name": "Aegishjalmur",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Puedes poner este Oro en juego desde tu Cementerio como si "
            "estuviera en tu mano.\n"
            "Cuando entra en juego, elige dos efectos:\n"
            "- Sube un Aliado de tu Cementerio a tu mano.\n"
            "- Baraja hasta una carta de coste 2 o menos.\n"
            "- Roba una carta."
        ),
        "image_file": "mazo_dragon_040.png",
        "cloudinary_id": "dragon_040",
    },
    {
        "myl_id": "custom_mid_41",
        "edid": "MID-41",
        "slug": "don-de-amma-mid",
        "name": "Don de Amma",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando tu oponente ponga su segundo Oro en juego este turno, "
            "puedes poner este Oro desde tu mano o Cementerio en tu Oro "
            "Pagado.\n"
            "Una vez por turno, puedes Desterrar un Oro con habilidad de tu "
            "Reserva. Luego, busca un Oro en tu Castillo y ponlo en tu "
            "Reserva."
        ),
        "image_file": "mazo_dragon_041.png",
        "cloudinary_id": "dragon_041",
    },
    {
        "myl_id": "custom_mid_42",
        "edid": "MID-42",
        "slug": "tyet-mid",
        "name": "Tyet",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, busca un Arma o un Oro en tu Castillo y "
            "ponlo en tu mano.\n"
            "Puedes pagarlo para que un Oro pierda su habilidad este turno y "
            "muévelo al Oro Pagado.\n"
            "Puedes poner esta y otra carta de tu mano en el fondo de tu "
            "Castillo y Robar dos cartas. Sólo puedes utilizar esta habilidad "
            "de Tyet una vez por turno."
        ),
        "image_file": "mazo_dragon_042.png",
        "cloudinary_id": "dragon_042",
    },
    {
        "myl_id": "custom_mid_43",
        "edid": "MID-43",
        "slug": "perla-de-sangre-mid",
        "name": "Perla de Sangre",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "En tu Vigilia, una vez por turno, puedes pagarlo para buscar en "
            "tu Castillo un Aliado y ponerlo en tu mano o jugarlo reduciendo "
            "su coste en un Oro, hasta un mínimo de 1.\n"
            "Puedes convertirlo en un Oro sin habilidad para Barajar y/o "
            "Desterrar hasta cuatro cartas de los Cementerios y Robar hasta "
            "dos cartas."
        ),
        "image_file": "mazo_dragon_043.png",
        "cloudinary_id": "dragon_043",
    },
    {
        "myl_id": "custom_mid_44",
        "edid": "MID-44",
        "slug": "alicanto-mid",
        "name": "Alicanto",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "En respuesta a que fueras a recibir daño, puedes Desterrar este "
            "Oro para prevenirlo. Luego, puedes convertir una carta de tu "
            "mano en un Oro sin habilidad y ponerla en tu Oro Pagado.\n"
            "Los Aliados de coste 2 o más pagados con este Oro no pueden ser "
            "Anulados."
        ),
        "image_file": "mazo_dragon_044.png",
        "cloudinary_id": "dragon_044",
    },
    {
        "myl_id": "custom_mid_45",
        "edid": "MID-45",
        "slug": "pintura-sagrada-mid",
        "name": "Pintura Sagrada",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "Si no has puesto Oros en juego este turno, en tu Vigilia puedes "
            "ponerlo en tu Reserva.\n"
            "Cuando entra en juego, busca una carta en tu Castillo y ponla "
            "en tu Cementerio.\n"
            "En cada Fase Final, puedes Barajar o Desterrar una carta de un "
            "Cementerio."
        ),
        "image_file": "mazo_dragon_045.png",
        "cloudinary_id": "dragon_045",
    },
    {
        "myl_id": "custom_mid_46",
        "edid": "MID-46",
        "slug": "frankenstein-o-el-moderno-prometeo-mid",
        "name": "Frankenstein o El Moderno Prometeo",
        "type_slug": "oro",
        "race_slug": "dragon",
        "cost": None,
        "damage": None,
        "ability": (
            "En tu turno, puedes pagarlo y Barajar una carta de tu mano para "
            "cancelar la habilidad de un Oro o carta de coste 2 o menos.\n"
            "Una vez por turno, puedes Descartar una carta para que una carta "
            "pierda su habilidad por el turno."
        ),
        "image_file": "mazo_dragon_046.png",
        "cloudinary_id": "dragon_046",
    },
]

# ── Eterno Card data (46 cards: 45 numbered + 1 bonus) ─────────────
MAZO_ETERNO_CARDS = [
    {
        "myl_id": "custom_mie_01",
        "edid": "MIE-01",
        "slug": "campanita-mie",
        "name": "Campanita",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "1",
        "damage": "2",
        "ability": (
            "Indestructible.\n"
            "Cuando entra en juego, puedes Barajar hasta cuatro cartas de "
            "los Cementerios o subir un Aliado o Tótem de tu Cementerio a tu "
            "mano.\n"
            "Puedes Desterrarlo para cancelar una habilidad o Robar dos "
            "cartas."
        ),
        "image_file": "mazo_eterno_0.png",
        "cloudinary_id": "eterno_0",
    },
    {
        "myl_id": "custom_mie_02",
        "edid": "MIE-02",
        "slug": "angel-redentor-mie",
        "name": "Ángel Redentor",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "2",
        "damage": "3",
        "ability": (
            "Cuando entra o salga del juego, puedes Descartar una carta para "
            "buscar en tu Castillo una carta del mismo tipo y ponerla en tu "
            "mano.\n"
            "Una vez por turno, puedes prevenir que una carta sea Anulada o "
            "su habilidad cancelada.\n"
            "En la Agrupación, genera un Oro por el turno."
        ),
        "image_file": "mazo_eterno_02.png",
        "cloudinary_id": "eterno_02",
    },
    {
        "myl_id": "custom_mie_bonus_01",
        "edid": "MIE-B01",
        "slug": "sidhes-del-bosque-mie",
        "name": "Sidhes del Bosque",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "0",
        "damage": None,
        "ability": (
            "Puedes jugarlo en respuesta a que tu oponente fuera a buscar "
            "cartas en un Castillo. Nombra dos cartas. Este turno tu "
            "oponente debe mostrar las cartas que busca y no puede buscar "
            "las cartas nombradas. Roba una carta o sube un Aliado de tu "
            "Cementerio a tu mano."
        ),
        "image_file": "mazo_eterno_03.png",
        "cloudinary_id": "eterno_03",
    },
    {
        "myl_id": "custom_mie_03",
        "edid": "MIE-03",
        "slug": "polvo-de-hadas-mie",
        "name": "Polvo de Hadas",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, puedes mirar las primeras tres cartas de "
            "tu Castillo. Pon una carta de ahí en tu mano, otra en tu "
            "Cementerio y otra en tu Destierro o fondo de tu Castillo.\n"
            "Puedes convertirlo en un Oro sin habilidad para prevenir que "
            "Botes o Destierres cartas del tope de tu Castillo por un efecto "
            "oponente."
        ),
        "image_file": "mazo_eterno_04.png",
        "cloudinary_id": "eterno_04",
    },
    {
        "myl_id": "custom_mie_04",
        "edid": "MIE-04",
        "slug": "el-angel-y-su-juicio-mie",
        "name": "El Ángel y su Juicio",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "2",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Busca un Aliado en tu Castillo y juégalo reduciendo su coste en "
            "dos Oros, hasta un mínimo de 0. Si controlas o jugaste un Aliado "
            "Ángel desde tu turno anterior, reduce su coste en tres Oros en "
            "vez de dos y Roba una carta."
        ),
        "image_file": "mazo_eterno_05.png",
        "cloudinary_id": "eterno_05",
    },
    {
        "myl_id": "custom_mie_05",
        "edid": "MIE-05",
        "slug": "concilio-de-los-eternos-mie",
        "name": "Concilio de los Eternos",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Sólo puedes jugar esta carta si controlas y/o muestras de tu "
            "mano al menos cuatro tipos de carta distintos.\n"
            "Prevén un efecto y tu oponente sólo puede atacar con hasta dos "
            "Aliados este turno."
        ),
        "image_file": "mazo_eterno_06.png",
        "cloudinary_id": "eterno_06",
    },
    {
        "myl_id": "custom_mie_06",
        "edid": "MIE-06",
        "slug": "totem-de-la-vision-eterna-mie",
        "name": "Tótem de la Visión Eterna",
        "type_slug": "totem",
        "race_slug": "eterno",
        "cost": "2",
        "damage": None,
        "ability": (
            "En tu Vigilia, una vez por turno, elige un efecto:\n"
            "- Baraja cartas en juego cuyos costes sumen hasta 4 y Roba dos "
            "cartas. No puedes elegir este efecto en tu próximo turno.\n"
            "- Busca una carta en tu Castillo, ponla en tu mano y tu "
            "oponente Descarta una carta. No puedes elegir este efecto en tu "
            "próximo turno."
        ),
        "image_file": "mazo_eterno_07.png",
        "cloudinary_id": "eterno_07",
    },
    {
        "myl_id": "custom_mie_07",
        "edid": "MIE-07",
        "slug": "templo-de-los-eternos-mie",
        "name": "Templo de los Eternos",
        "type_slug": "totem",
        "race_slug": "eterno",
        "cost": "2",
        "damage": None,
        "ability": (
            "Puedes hacer que entre en juego sin habilidad por el turno para "
            "reducir su coste en un Oro.\n"
            "Una vez por turno, Baraja hasta un Aliado o Tótem y hasta tres "
            "cartas de los Cementerios.\n"
            "A tu oponente le cuesta un Oro adicional Barajar o Desterrar "
            "tus demás cartas en juego."
        ),
        "image_file": "mazo_eterno_08.png",
        "cloudinary_id": "eterno_08",
    },
    {
        "myl_id": "custom_mie_08",
        "edid": "MIE-08",
        "slug": "trono-del-rey-eterno-mie",
        "name": "Trono del Rey Eterno",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, mira tantas cartas del tope de tu "
            "Castillo como Oros controles, pon una carta de ahí en tu mano y "
            "ordena el resto.\n"
            "Si está en tu Reserva, los jugadores sólo pueden poner en juego "
            "hasta tantas cartas de cada tipo por turno como Oros controlen."
        ),
        "image_file": "mazo_eterno_09.png",
        "cloudinary_id": "eterno_09",
    },
    {
        "myl_id": "custom_mie_09",
        "edid": "MIE-09",
        "slug": "baculo-de-los-eternos-mie",
        "name": "Báculo de los Eternos",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "Una vez en tu turno, mira tantas cartas del tope de tu Castillo "
            "como Armas y Tótem controles y ordénalas. Puedes Robar una carta "
            "y si lo haces no Robas al finalizar tu turno.\n"
            "Los jugadores sólo pueden atacar con hasta tantos Aliados como "
            "Oros controlen."
        ),
        "image_file": "mazo_eterno_010.png",
        "cloudinary_id": "eterno_010",
    },
    {
        "myl_id": "custom_mie_10",
        "edid": "MIE-10",
        "slug": "ngenchen-mie",
        "name": "Ngenechén",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "4",
        "damage": "4",
        "ability": (
            "Indestructible.\n"
            "Cuando entra en juego Destierra cartas oponentes cuyos costes "
            "sumen hasta 6.\n"
            "Al comienzo del turno oponente, genera un Oro por el turno y "
            "Roba dos cartas.\n"
            "Una vez por turno, puedes Barajar una carta de tu mano para "
            "prevenir un efecto."
        ),
        "image_file": "mazo_eterno_011.png",
        "cloudinary_id": "eterno_011",
    },
    {
        "myl_id": "custom_mie_11",
        "edid": "MIE-11",
        "slug": "tenshi-z-mie",
        "name": "Tenshi Z",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "3",
        "damage": "5",
        "ability": (
            "Una vez por turno, puedes Barajar una carta de tu mano para "
            "Anular una carta.\n"
            "Una vez por turno, puedes convertir hasta dos cartas de coste 2 "
            "o menos en Tótem sin habilidad y ganar su control.\n"
            "En tu Fase Final, busca una carta en tu Castillo, ponla en tu "
            "mano y Roba una carta."
        ),
        "image_file": "mazo_eterno_012.png",
        "cloudinary_id": "eterno_012",
    },
    {
        "myl_id": "custom_mie_12",
        "edid": "MIE-12",
        "slug": "legendario-tenshi-mie",
        "name": "Legendario Tenshi",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "2",
        "damage": "3",
        "ability": (
            "Una vez por turno, Baraja una carta oponente de coste 2 o menos "
            "o Roba dos cartas.\n"
            "En tu Fase Final, puedes Barajar y/o Desterrar hasta tres "
            "cartas de los Cementerios.\n"
            "Los Aliados oponentes de coste 1 o menos pierden su habilidad y "
            "1 de Fuerza."
        ),
        "image_file": "mazo_eterno_013.png",
        "cloudinary_id": "eterno_013",
    },
    {
        "myl_id": "custom_mie_13",
        "edid": "MIE-13",
        "slug": "pachamama-mie",
        "name": "Pachamama",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "2",
        "damage": "3",
        "ability": (
            "Una vez por turno, puedes convertir una carta oponente de coste "
            "3 o menos en un Tótem sin habilidad y ganar su control.\n"
            "Una vez en tu turno, puedes mirar hasta tantas cartas del tope "
            "de tu Castillo como Tótem hay en juego y ordénalas. Roba dos "
            "cartas."
        ),
        "image_file": "mazo_eterno_014.png",
        "cloudinary_id": "eterno_014",
    },
    {
        "myl_id": "custom_mie_14",
        "edid": "MIE-14",
        "slug": "angel-vengador-mie",
        "name": "Ángel Vengador",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "3",
        "damage": "4",
        "ability": (
            "Sus habilidades no pueden ser canceladas.\n"
            "Cuando entra en juego, puedes buscar un Aliado, un Talismán y "
            "un Tótem en tu Castillo y ponerlos en tu mano.\n"
            "Una vez en tu turno, puedes Barajar hasta dos cartas oponentes "
            "de coste 3 o menos y cualquier cantidad de cartas de tu "
            "Cementerio."
        ),
        "image_file": "mazo_eterno_015.png",
        "cloudinary_id": "eterno_015",
    },
    {
        "myl_id": "custom_mie_15",
        "edid": "MIE-15",
        "slug": "shub-niggurath-mie",
        "name": "Shub-Niggurath",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "2",
        "damage": "3",
        "ability": (
            "Una vez en tu turno, Baraja una carta de coste 3 o menos o tu "
            "oponente Bota dos cartas por cada Aliado y/o Tótem que "
            "controles.\n"
            "En tu Vigilia, una vez por turno, puedes generar un Oro para "
            "jugar un Tótem de coste 2 o más y Robar una carta."
        ),
        "image_file": "mazo_eterno_016.png",
        "cloudinary_id": "eterno_016",
    },
    {
        "myl_id": "custom_mie_16",
        "edid": "MIE-16",
        "slug": "mot-mie",
        "name": "Mot",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "3",
        "damage": "4",
        "ability": (
            "Una vez por turno, genera dos Oros para jugar Tótem o sube hasta "
            "dos cartas que no sean Talismán de tu Cementerio a tu mano.\n"
            "Cuando pongas en juego un Aliado o Tótem, hasta dos veces por "
            "turno, Baraja una carta que no sea Oro o tu oponente Descarta "
            "una carta."
        ),
        "image_file": "mazo_eterno_017.png",
        "cloudinary_id": "eterno_017",
    },
    {
        "myl_id": "custom_mie_17",
        "edid": "MIE-17",
        "slug": "angel-gadreel-mie",
        "name": "Ángel Gadreel",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "1",
        "damage": "2",
        "ability": (
            "Indestructible.\n"
            "Cuando entra en juego, muestra cartas del tope de tu Castillo "
            "hasta mostrar un Tótem y un Oro. Ponlos en tu mano y Baraja el "
            "resto.\n"
            "Puedes Desterrarlo para prevenir que un Tótem sea Anulado o su "
            "habilidad cancelada."
        ),
        "image_file": "mazo_eterno_018.png",
        "cloudinary_id": "eterno_018",
    },
    {
        "myl_id": "custom_mie_18",
        "edid": "MIE-18",
        "slug": "escuadron-angel-mie",
        "name": "Escuadrón Ángel",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "cost": "3",
        "damage": "4",
        "ability": (
            "No puedes controlar más copias de esta carta.\n"
            "Cuando entra en juego, puedes buscar un Ángel, Eterno o Tótem "
            "de coste 3 o menos en tu Castillo y jugarlo sin pagar su coste.\n"
            "Tus demás Aliados y Tótem son Indestructibles."
        ),
        "image_file": "mazo_eterno_019.png",
        "cloudinary_id": "eterno_019",
    },
    {
        "myl_id": "custom_mie_19",
        "edid": "MIE-19",
        "slug": "templo-de-hatshepsut-mie",
        "name": "Templo de Hatshepsut",
        "type_slug": "totem",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Cuando entra en juego, Baraja o Destierra una carta oponente de "
            "coste 3 o menos.\n"
            "En tu Vigilia o al comienzo de tu Fase Final, una vez por turno, "
            "puedes Desterrar o Barajar hasta tres cartas de los Cementerios."
        ),
        "image_file": "mazo_eterno_020.png",
        "cloudinary_id": "eterno_020",
    },
    {
        "myl_id": "custom_mie_20",
        "edid": "MIE-20",
        "slug": "ciudad-de-los-cesares-mie",
        "name": "Ciudad de los Césares",
        "type_slug": "totem",
        "race_slug": "eterno",
        "cost": "2",
        "damage": None,
        "ability": (
            "Cuando entra o sale del juego, Baraja hasta una carta oponente "
            "de coste 3 o menos y Roba dos cartas.\n"
            "Una vez por turno, puedes Barajar una carta de tu mano para "
            "Anular o Desterrar una carta de coste 1 o menos, o pagar un Oro "
            "para Anular una carta de coste 2 o más."
        ),
        "image_file": "mazo_eterno_021.png",
        "cloudinary_id": "eterno_021",
    },
    {
        "myl_id": "custom_mie_21",
        "edid": "MIE-21",
        "slug": "carcosa-mie",
        "name": "Carcosa",
        "type_slug": "totem",
        "race_slug": "eterno",
        "cost": "2",
        "damage": None,
        "ability": (
            "Cuando entra en juego y al comienzo del turno oponente, "
            "Destierra una carta que no sea Oro o mira la mano de tu "
            "oponente y Destierra un Talismán de ahí. Roba una carta.\n"
            "Al comienzo de tu turno y cuando salga del juego, tu oponente "
            "Bota cuatro cartas."
        ),
        "image_file": "mazo_eterno_022.png",
        "cloudinary_id": "eterno_022",
    },
    {
        "myl_id": "custom_mie_22",
        "edid": "MIE-22",
        "slug": "paris-mie",
        "name": "París",
        "type_slug": "totem",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Una vez en tu turno, busca en tu Castillo un Oro sin habilidad y "
            "ponlo en tu Oro Pagado.\n"
            "Una vez en tu turno, puedes poner una carta de tu mano en el "
            "tope de tu Castillo y dos cartas del fondo Castillo en tu mano.\n"
            "Al comienzo de la Vigilia oponente, puedes jugar un Arma o "
            "Tótem de tu mano pagando su coste."
        ),
        "image_file": "mazo_eterno_023.png",
        "cloudinary_id": "eterno_023",
    },
    {
        "myl_id": "custom_mie_23",
        "edid": "MIE-23",
        "slug": "dragon-dorado-mie",
        "name": "Dragón Dorado",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "0",
        "damage": None,
        "ability": (
            "Única.\n"
            "Cuando juegues este Talismán, Destiérralo.\n"
            "Anula una carta. Luego, Baraja tantas cartas de tu mano como "
            "coste tenga."
        ),
        "image_file": "mazo_eterno_024.png",
        "cloudinary_id": "eterno_024",
    },
    {
        "myl_id": "custom_mie_24",
        "edid": "MIE-24",
        "slug": "energia-suprema-mie",
        "name": "Energía Suprema",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Para jugarlo, muestra un Arma o Tótem de tu mano o Cementerio "
            "y Destierra este Talismán.\n"
            "Genera dos Oros para jugar un Aliado de coste 3 o más. Cuando "
            "los uses, Baraja hasta tantas cartas de los Cementerios como "
            "coste tenga ese Aliado y Roba esa misma cantidad de cartas."
        ),
        "image_file": "mazo_eterno_025.png",
        "cloudinary_id": "eterno_025",
    },
    {
        "myl_id": "custom_mie_25",
        "edid": "MIE-25",
        "slug": "vision-heroica-mie",
        "name": "Visión Heroica",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Baraja una carta de coste 3 o menos o Anula un Talismán "
            "oponente.\n"
            "Puedes pagar un Oro para subir esta carta de tu Cementerio a "
            "tu mano y Robar una carta."
        ),
        "image_file": "mazo_eterno_026.png",
        "cloudinary_id": "eterno_026",
    },
    {
        "myl_id": "custom_mie_26",
        "edid": "MIE-26",
        "slug": "ciempies-sp-mie",
        "name": "Ciempiés-SP",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Anula una carta de coste 3 o menos."
        ),
        "image_file": "mazo_eterno_027.png",
        "cloudinary_id": "eterno_027",
    },
    {
        "myl_id": "custom_mie_27",
        "edid": "MIE-27",
        "slug": "sheut-mie",
        "name": "Sheut",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Si controlas menos Oros que tu oponente, puedes jugarlo por un "
            "Oro menos. Cuando lo juegues, Destiérralo.\n"
            "Anula un Aliado o Tótem, de coste 1 o menos, o cancela la "
            "habilidad de una carta."
        ),
        "image_file": "mazo_eterno_028.png",
        "cloudinary_id": "eterno_028",
    },
    {
        "myl_id": "custom_mie_28",
        "edid": "MIE-28",
        "slug": "colapso-global-mie",
        "name": "Colapso Global",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "En respuesta a que tu oponente fuera a mirar tu mano o buscar "
            "cartas en un Castillo, puedes Desterrar una carta de tu mano "
            "para jugarlo sin pagar su coste.\n"
            "Prevén que tu oponente mire tu mano o busque cartas y tú Robas "
            "una carta."
        ),
        "image_file": "mazo_eterno_029.png",
        "cloudinary_id": "eterno_029",
    },
    {
        "myl_id": "custom_mie_29",
        "edid": "MIE-29",
        "slug": "escudo-estelar-mie",
        "name": "Escudo Estelar",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Puedes jugarlo en respuesta a que se juegue o utilice la "
            "habilidad de una carta de coste 1 o menos.\n"
            "Los jugadores no pueden buscar, mirar, ni mostrar cartas de la "
            "mano ni los Castillos por efectos hasta tu próxima Fase Final."
        ),
        "image_file": "mazo_eterno_030.png",
        "cloudinary_id": "eterno_030",
    },
    {
        "myl_id": "custom_mie_30",
        "edid": "MIE-30",
        "slug": "transformacion-mie",
        "name": "Transformación",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Puedes jugarlo en respuesta a que tu oponente juegue una carta "
            "o utilice una habilidad y Destiérralo. Elige un efecto:\n"
            "- Prevén que una carta que controles sea afectada y Roba una "
            "carta.\n"
            "- Prevén un efecto que fuera a afectarte, busca un Aliado en tu "
            "Castillo y ponlo en tu mano."
        ),
        "image_file": "mazo_eterno_031.png",
        "cloudinary_id": "eterno_031",
    },
    {
        "myl_id": "custom_mie_31",
        "edid": "MIE-31",
        "slug": "fision-nuclear-mie",
        "name": "Fisión Nuclear",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Hasta tu próximo turno, no puedes ser afectado por efectos "
            "oponentes y para afectar tus cartas en juego tu oponente debe "
            "Desterrar una carta de su mano.\n"
            "En la próxima Fase Final oponente, Baraja una carta de coste 2 "
            "o menos o Roba dos cartas."
        ),
        "image_file": "mazo_eterno_032.png",
        "cloudinary_id": "eterno_032",
    },
    {
        "myl_id": "custom_mie_32",
        "edid": "MIE-32",
        "slug": "tempilcahue-mie",
        "name": "Tempilcahue",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "0",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Elige un efecto:\n"
            "- Busca una carta en tu Castillo, ponla en tu mano y Roba una "
            "carta. No puedes jugar más cartas este turno.\n"
            "- Paga dos Oros para Barajar cartas cuyos costes sumen hasta 4 "
            "y Robar dos cartas."
        ),
        "image_file": "mazo_eterno_033.png",
        "cloudinary_id": "eterno_033",
    },
    {
        "myl_id": "custom_mie_33",
        "edid": "MIE-33",
        "slug": "el-caleuche-mie",
        "name": "El Caleuche",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "No puede ser Anulado.\n"
            "Elige un efecto:\n"
            "- En respuesta a que se juegue una carta sin pagar su coste o "
            "que no pueda ser Anulada, esa carta entra en juego sin habilidad "
            "por el turno. Si es Talismán, se resuelve sin efecto.\n"
            "- Baraja una carta de coste 2 o menos y Roba dos cartas."
        ),
        "image_file": "mazo_eterno_034.png",
        "cloudinary_id": "eterno_034",
    },
    {
        "myl_id": "custom_mie_34",
        "edid": "MIE-34",
        "slug": "red-de-plata-mie",
        "name": "Red de Plata",
        "type_slug": "talisman",
        "race_slug": "eterno",
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Anula o cancela la habilidad de un Aliado. Si tenía coste 2 o "
            "menos, Destierra ese Aliado.\n"
            "Puedes Desterrarlo de tu Cementerio para que un Aliado pierda "
            "su habilidad por el turno."
        ),
        "image_file": "mazo_eterno_035.png",
        "cloudinary_id": "eterno_035",
    },
    {
        "myl_id": "custom_mie_35",
        "edid": "MIE-35",
        "slug": "terminal-p-12-mie",
        "name": "Terminal P-12",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "Si está en tu Reserva, las cartas que controles no pueden perder "
            "su habilidad por habilidades y efectos oponentes y él no puede "
            "mirar tu mano ni tu Castillo.\n"
            "En cada turno, los jugadores sólo pueden buscar hasta dos cartas "
            "por efectos y utilizar hasta dos habilidades de cartas fuera del "
            "juego."
        ),
        "image_file": "mazo_eterno_036.png",
        "cloudinary_id": "eterno_036",
    },
    {
        "myl_id": "custom_mie_36",
        "edid": "MIE-36",
        "slug": "dracula-mie",
        "name": "Drácula",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Las habilidades de este Oro no pueden ser canceladas.\n"
            "Cuando entra en juego, Roba dos cartas.\n"
            "Puedes convertirlo en un Oro sin habilidad para prevenir que "
            "una habilidad sea cancelada o un Aliado de coste 1 sea Anulado.\n"
            "Puedes Desterrarlo de tu mano o Cementerio para cancelar el "
            "ataque de hasta dos Aliados."
        ),
        "image_file": "mazo_eterno_037.png",
        "cloudinary_id": "eterno_037",
    },
    {
        "myl_id": "custom_mie_37",
        "edid": "MIE-37",
        "slug": "signo-amarillo-mie",
        "name": "Signo Amarillo",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Indesterrable.\n"
            "Cuando entra en juego, mira cuatro cartas del tope de tu "
            "Castillo. Pon una de ahí en tu mano, otra en tu Cementerio y "
            "ordena el resto.\n"
            "Puedes convertir este Oro en un Oro sin habilidad para cancelar "
            "la habilidad de una carta fuera del juego o un Oro."
        ),
        "image_file": "mazo_eterno_038.png",
        "cloudinary_id": "eterno_038",
    },
    {
        "myl_id": "custom_mie_38",
        "edid": "MIE-38",
        "slug": "aegishjalmur-mie",
        "name": "Aegishjalmur",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Puedes poner este Oro en juego desde tu Cementerio como si "
            "estuviera en tu mano.\n"
            "Cuando entra en juego, elige dos efectos:\n"
            "- Sube un Aliado de tu Cementerio a tu mano.\n"
            "- Baraja hasta una carta de coste 2 o menos.\n"
            "- Roba una carta."
        ),
        "image_file": "mazo_eterno_039.png",
        "cloudinary_id": "eterno_039",
    },
    {
        "myl_id": "custom_mie_39",
        "edid": "MIE-39",
        "slug": "don-de-amma-mie",
        "name": "Don de Amma",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando tu oponente ponga su segundo Oro en juego este turno, "
            "puedes poner este Oro desde tu mano o Cementerio en tu Oro "
            "Pagado.\n"
            "Una vez por turno, puedes Desterrar un Oro con habilidad de tu "
            "Reserva. Luego, busca un Oro en tu Castillo y ponlo en tu "
            "Reserva."
        ),
        "image_file": "mazo_eterno_040.png",
        "cloudinary_id": "eterno_040",
    },
    {
        "myl_id": "custom_mie_40",
        "edid": "MIE-40",
        "slug": "espiritu-de-la-maquina-mie",
        "name": "Espíritu de la Máquina",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, si no es tu primer turno, genera un Oro "
            "para jugar Armas o Tótem de coste 2 o más.\n"
            "Una vez por turno, puedes Barajar o Desterrar una carta de un "
            "Cementerio."
        ),
        "image_file": "mazo_eterno_041.png",
        "cloudinary_id": "eterno_041",
    },
    {
        "myl_id": "custom_mie_41",
        "edid": "MIE-41",
        "slug": "matriz-v-mie",
        "name": "Matriz V",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Esta carta no puede ser convertida.\n"
            "Cuando entra en juego, Roba una carta y hasta dos cartas que "
            "controles ganan Indesterrable mientras estén en juego.\n"
            "Si está en tu Reserva, tu oponente no puede disparar habilidades "
            "de cartas de coste 0 o 1 a menos que Destierre una carta de su "
            "mano."
        ),
        "image_file": "mazo_eterno_042.png",
        "cloudinary_id": "eterno_042",
    },
    {
        "myl_id": "custom_mie_42",
        "edid": "MIE-42",
        "slug": "alicanto-mie",
        "name": "Alicanto",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "En respuesta a que fueras a recibir daño, puedes Desterrar este "
            "Oro para prevenirlo. Luego, puedes convertir una carta de tu "
            "mano en un Oro sin habilidad y ponerla en tu Oro Pagado.\n"
            "Los Aliados de coste 2 o más pagados con este Oro no pueden ser "
            "Anulados."
        ),
        "image_file": "mazo_eterno_043.png",
        "cloudinary_id": "eterno_043",
    },
    {
        "myl_id": "custom_mie_43",
        "edid": "MIE-43",
        "slug": "perla-de-sangre-mie",
        "name": "Perla de Sangre",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "En tu Vigilia, una vez por turno, puedes pagarlo para buscar en "
            "tu Castillo un Aliado y ponerlo en tu mano o jugarlo reduciendo "
            "su coste en un Oro, hasta un mínimo de 1.\n"
            "Puedes convertirlo en un Oro sin habilidad para Barajar y/o "
            "Desterrar hasta cuatro cartas de los Cementerios y Robar hasta "
            "dos cartas."
        ),
        "image_file": "mazo_eterno_044.png",
        "cloudinary_id": "eterno_044",
    },
    {
        "myl_id": "custom_mie_44",
        "edid": "MIE-44",
        "slug": "diadema-celestial-mie",
        "name": "Diadema Celestial",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, muestra cartas del tope de tu Castillo "
            "hasta mostrar un Aliado y un Talismán y ponlos en tu mano.\n"
            "Tus Aliados bloqueadores ganan 1 de Fuerza y los Aliados "
            "oponentes pierden Imbloqueable.\n"
            "Si Botas esta carta por daño, dejas de Botar cartas y "
            "Destierras este Oro."
        ),
        "image_file": "mazo_eterno_045.png",
        "cloudinary_id": "eterno_045",
    },
    {
        "myl_id": "custom_mie_45",
        "edid": "MIE-45",
        "slug": "ukiyo-e-mie",
        "name": "Ukiyo-E",
        "type_slug": "oro",
        "race_slug": "eterno",
        "cost": None,
        "damage": None,
        "ability": "",
        "image_file": "mazo_eterno_046.png",
        "cloudinary_id": "eterno_046",
    },
]


class Command(BaseCommand):
    help = "Seed Mazo Dragón + Mazo Eterno (AYDV edition)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-url-check",
            action="store_true",
            help="Skip URL accessibility validation before seeding",
        )
        parser.add_argument(
            "--url-check-timeout",
            type=int,
            default=10,
            help="Timeout in seconds for URL accessibility checks",
        )

    def handle(self, *args, **options):
        imp_format = Format.objects.get(code="imp")

        # ── Ensure races exist ──────────────────────────────────────
        for race_slug, race_name in [("dragon", "Dragón"), ("eterno", "Eterno")]:
            Race.objects.get_or_create(
                slug=race_slug,
                defaults={"myl_id": f"custom_{race_slug}", "name": race_name},
            )

        # ── Load Cloudinary mappings ────────────────────────────────
        dragon_urls = {}
        if os.path.exists(DRAGON_MAPPING_FILE):
            with open(DRAGON_MAPPING_FILE, "r", encoding="utf-8") as f:
                dragon_urls = json.load(f)

        eterno_urls = {}
        if os.path.exists(ETERNO_MAPPING_FILE):
            with open(ETERNO_MAPPING_FILE, "r", encoding="utf-8") as f:
                eterno_urls = json.load(f)

        validate_mapping_urls(
            dragon_urls,
            self,
            "Mazo Dragón",
            skip_check=options["skip_url_check"],
            timeout=max(1, options["url_check_timeout"]),
        )
        validate_mapping_urls(
            eterno_urls,
            self,
            "Mazo Eterno",
            skip_check=options["skip_url_check"],
            timeout=max(1, options["url_check_timeout"]),
        )

        # ── Seed Dragon ─────────────────────────────────────────────
        dragon_ed, dc = Edition.objects.update_or_create(
            myl_id="custom_aydv_mazo_dragon",
            defaults={
                "slug": "aydv-mazo-dragon",
                "title": "Ángeles y Demonios: Vigilantes - Mazo Dragón",
                "image": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/MAZO_DRAGON.png",
                "date_release": "2026-07-03",
                "format": imp_format,
                "active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if dc else 'Updated'} edition: {dragon_ed.title}"
        ))
        self._seed_cards(MAZO_DRAGON_CARDS, dragon_ed, dragon_urls, "Dragon")

        # ── Seed Eterno ─────────────────────────────────────────────
        eterno_ed, ec = Edition.objects.update_or_create(
            myl_id="custom_aydv_mazo_eterno",
            defaults={
                "slug": "aydv-mazo-eterno",
                "title": "Ángeles y Demonios: Vigilantes - Mazo Eterno",
                "image": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/MAZO_ETERNO.png",
                "date_release": "2026-07-03",
                "format": imp_format,
                "active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if ec else 'Updated'} edition: {eterno_ed.title}"
        ))
        self._seed_cards(MAZO_ETERNO_CARDS, eterno_ed, eterno_urls, "Eterno")

    def _seed_cards(self, cards_data, edition, cloudinary_urls, label):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nSeeding {len(cards_data)} {label} cards..."
        ))

        promo_rarity = Rarity.objects.filter(slug="promo").first()
        created_count = 0
        updated_count = 0

        for card_data in cards_data:
            card_type = CardType.objects.filter(
                slug=card_data["type_slug"]
            ).first()
            race = None
            if card_data["race_slug"]:
                race = Race.objects.filter(slug=card_data["race_slug"]).first()

            image_url = cloudinary_urls.get(card_data["cloudinary_id"], "")

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
                    "flavour": "",
                    "custom_image_url": image_url,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            status = "Created" if created else "Updated"
            self.stdout.write(
                f"  {status}: {card.name} ({card.edid})"
                + (f" → {image_url[:60]}..." if image_url else " [NO IMAGE]")
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone {label}! Created: {created_count}, Updated: "
            f"{updated_count} ({len(cards_data)} total)"
        ))
