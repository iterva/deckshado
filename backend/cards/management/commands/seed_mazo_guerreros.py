"""
Seed Mazo Imperio de Guerreros (AYDV edition).
  - Creates edition "Ángeles y Demonios: Vigilantes" (format=imp)
  - Uploads 43 card images to Cloudinary
  - Creates 43 cards in the database

Usage:
    python manage.py seed_mazo_guerreros [--skip-upload]
"""
import os
import json

import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity

# Cloudinary config
cloudinary.config(
    cloud_name="dmvu6tuee",
    api_key="618467334728855",
    api_secret="egB_Ypv0wdVVBL2oRhUaoHr8bY8",
    secure=True,
)

CLOUDINARY_FOLDER = "deckshado/myl_cards/aydv_mazo_guerreros"

# Source images folder
SOURCE_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "cartas por subir 9",
)

MAPPING_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "mazo_guerreros_mapping.json",
)

# ── Card data ───────────────────────────────────────────────────────
MAZO_GUERREROS_CARDS = [
    {
        "myl_id": "custom_mig_01",
        "edid": "MIG-01",
        "slug": "auguste-dupin-mig",
        "name": "Auguste Dupin",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "4",
        "damage": "2",
        "ability": (
            "Furia.\n"
            "Cuando entra en juego, mira la mano de tu oponente y Descarta "
            "los Talismanes o Tótem de ahí. Si atacaste en tu turno anterior, "
            "esta habilidad no puede ser cancelada ni prevenida.\n"
            "Si está en tu Cementerio o en juego, no se pueden Barajar cartas "
            "de los Cementerios."
        ),
        "image_file": "mazo_guerreros_0.png",
        "cloudinary_id": "guerreros_01",
    },
    {
        "myl_id": "custom_mig_02",
        "edid": "MIG-02",
        "slug": "bandido-medieval-mig",
        "name": "Bandido Medieval",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "2",
        "damage": "1",
        "ability": (
            "Furia.\n"
            "Cuando entra en juego, busca en tu Castillo una carta Bandido o "
            "un Aliado de coste 2 o menos y ponlo en tu mano o convierte un "
            "Oro oponente en un Oro sin habilidad.\n"
            "Una vez por turno, un Aliado o tus Aliados Bandido ganan 1 de "
            "Fuerza permanentemente."
        ),
        "image_file": "mazo_guerreros_02.png",
        "cloudinary_id": "guerreros_02",
    },
    {
        "myl_id": "custom_mig_03",
        "edid": "MIG-03",
        "slug": "principe-orion-mig",
        "name": "Príncipe Orión",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Furia.\n"
            "Cuando entra en juego, Roba una carta o sube un Aliado de tu "
            "Cementerio a tu mano. Si controlas Aliados en tu Línea de Ataque "
            "o que porten Armas de coste 1 o más, puedes Desterrarlo para "
            "Anular un Talismán."
        ),
        "image_file": "mazo_guerreros_03.png",
        "cloudinary_id": "guerreros_03",
    },
    {
        "myl_id": "custom_mig_04",
        "edid": "MIG-04",
        "slug": "motin-a-bordo-mig",
        "name": "Motín A Bordo",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "Puedes jugarlo al comienzo de la Vigilia y cuando lo juegues, "
            "Destiérralo. Elige un efecto:\n"
            "- No eres afectado por habilidades y efectos oponentes este turno. "
            "Roba una carta.\n"
            "- No pagas costes adicionales este turno. Sube hasta un Aliado de "
            "coste 2 o menos a la mano."
        ),
        "image_file": "mazo_guerreros_04.png",
        "cloudinary_id": "guerreros_04",
    },
    {
        "myl_id": "custom_mig_05",
        "edid": "MIG-05",
        "slug": "camino-del-guerrero-mig",
        "name": "Camino del Guerrero",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Sólo puedes jugar esta carta si controlas y/o muestras de tu mano "
            "al menos cuatro Aliados.\n"
            "Prevén un efecto y tus Aliados ganan 1 de Fuerza permanentemente."
        ),
        "image_file": "mazo_guerreros_05.png",
        "cloudinary_id": "guerreros_05",
    },
    {
        "myl_id": "custom_mig_06",
        "edid": "MIG-06",
        "slug": "espada-del-guerrero-inmortal-mig",
        "name": "Espada del Guerrero Inmortal",
        "type_slug": "arma",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "El portador gana 2 de Fuerza y Furia.\n"
            "En tu Vigilia, una vez por turno, puedes buscar un Aliado y un "
            "Arma en tu Castillo y ponerlos en tu mano o Robar dos cartas.\n"
            "Los Aliados que controlas ganan 1 de Fuerza."
        ),
        "image_file": "mazo_guerreros_06.png",
        "cloudinary_id": "guerreros_06",
    },
    {
        "myl_id": "custom_mig_07",
        "edid": "MIG-07",
        "slug": "armadura-dorada-mig",
        "name": "Armadura Dorada",
        "type_slug": "arma",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "El portador gana 2 de Fuerza e Indestructible.\n"
            "Cuando entra en juego, Roba dos cartas.\n"
            "Puedes Desterrar esta Arma o pagar un Oro y Desterrarla de tu "
            "mano para prevenir que tus Aliados sean afectados o un Aliado Anulado."
        ),
        "image_file": "mazo_guerreros_07.png",
        "cloudinary_id": "guerreros_07",
    },
    {
        "myl_id": "custom_mig_08",
        "edid": "MIG-08",
        "slug": "insignia-del-guerrero-mig",
        "name": "Insignia del Guerrero",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, puedes mostrar cartas del tope de tu "
            "Castillo hasta mostrar un Aliado y un Arma, de coste 2 o menos. "
            "Ponlas en tu mano y Baraja el resto.\n"
            "En Batalla Mitológica, puedes Desterrar este Oro para prevenir "
            "un efecto que afecte Aliados."
        ),
        "image_file": "mazo_guerreros_08.png",
        "cloudinary_id": "guerreros_08",
    },
    {
        "myl_id": "custom_mig_09",
        "edid": "MIG-09",
        "slug": "estandarte-del-guerrero-mig",
        "name": "Estandarte del Guerrero",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, Roba una carta.\n"
            "Puedes pagarlo para buscar dos cartas en cada Castillo y ponerlas "
            "en el Cementerio.\n"
            "Si está en tu Reserva, las cartas que sean puestas en el Cementerio "
            "por daño de combate no tienen habilidad por el turno."
        ),
        "image_file": "mazo_guerreros_09.png",
        "cloudinary_id": "guerreros_09",
    },
    {
        "myl_id": "custom_mig_10",
        "edid": "MIG-10",
        "slug": "armeria-del-guerrero-mig",
        "name": "Armería del Guerrero",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "Al comienzo del turno oponente, Baraja y/o Destierra hasta dos "
            "cartas de los Cementerios.\n"
            "Los jugadores no pueden poner Oros en juego por efectos si ya "
            "pusieron Oros en juego por efectos durante esta partida.\n"
            "Tus Aliados de coste 1 o más ganan 1 de Fuerza."
        ),
        "image_file": "mazo_guerreros_010.png",
        "cloudinary_id": "guerreros_10",
    },
    {
        "myl_id": "custom_mig_11",
        "edid": "MIG-11",
        "slug": "kuchiku-el-cazador-mig",
        "name": "Kuchiku El Cazador",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "4",
        "damage": "2",
        "ability": (
            "Furia.\n"
            "Una vez en tu turno, busca en tu Castillo o Cementerio un Aliado "
            "y juégalo reduciendo su coste en un Oro, hasta un mínimo de 0.\n"
            "Una vez en tu turno, puedes Destruir hasta una carta de coste 3 "
            "o menos y tu oponente Bota cartas igual a la Fuerza de este Aliado."
        ),
        "image_file": "mazo_guerreros_011.png",
        "cloudinary_id": "guerreros_11",
    },
    {
        "myl_id": "custom_mig_12",
        "edid": "MIG-12",
        "slug": "shinji-mig",
        "name": "Shinji",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "4",
        "damage": "2",
        "ability": (
            "Furia.\n"
            "Reduce su coste en un Oro si muestras un Arma o Tótem de tu "
            "mano o Cementerio.\n"
            "Cuando entra en juego, juega un Arma o Tótem de coste 1 desde "
            "tu mano o Cementerio sin pagar su coste."
        ),
        "image_file": "mazo_guerreros_012.png",
        "cloudinary_id": "guerreros_12",
    },
    {
        "myl_id": "custom_mig_13",
        "edid": "MIG-13",
        "slug": "gurzil-mig",
        "name": "Gurzil",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "5",
        "damage": "3",
        "ability": (
            "Furia.\n"
            "Si atacaste en tu anterior turno puedes pagar dos Oros para "
            "jugarlo sin pagar su coste.\n"
            "Cuando ataques, tu oponente muestra tantas cartas del tope de "
            "su Castillo como Fuerza tengan hasta dos Aliados que controles, "
            "ponlas en su Destierro y Roba una carta."
        ),
        "image_file": "mazo_guerreros_013.png",
        "cloudinary_id": "guerreros_13",
    },
    {
        "myl_id": "custom_mig_14",
        "edid": "MIG-14",
        "slug": "mariano-osorio-mig",
        "name": "Mariano Osorio",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Furia.\n"
            "Cuando entra en juego, muestra dos cartas del tope de tu Castillo "
            "y ponlas en tu mano. Si mostraste un Aliado o Arma de esta forma, "
            "convierte un Oro en Oro sin habilidad.\n"
            "En tu Vigilia o Fase Final, Destierra hasta tres cartas del "
            "Cementerio oponente."
        ),
        "image_file": "mazo_guerreros_014.png",
        "cloudinary_id": "guerreros_14",
    },
    {
        "myl_id": "custom_mig_15",
        "edid": "MIG-15",
        "slug": "kuchiku-kan-mig",
        "name": "Kuchiku Kan",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Cuando entra en juego, busca un Aliado en tu Castillo o "
            "Cementerio, ponlo en tu mano y tus Aliados ganan 1 de Fuerza "
            "permanentemente.\n"
            "Una vez por turno, puedes Descartar una carta para que una carta "
            "pierda su habilidad y no pueda atacar ni bloquear mientras este "
            "Aliado esté en juego."
        ),
        "image_file": "mazo_guerreros_015.png",
        "cloudinary_id": "guerreros_15",
    },
    {
        "myl_id": "custom_mig_16",
        "edid": "MIG-16",
        "slug": "antonio-pincheira-mig",
        "name": "Antonio Pincheira",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "5",
        "damage": "3",
        "ability": (
            "Furia.\n"
            "Cuando entra en juego o ataca, tu oponente Bota seis cartas. "
            "Pon hasta un Oro de su Cementerio en tu Reserva.\n"
            "Una vez por turno, Roba dos cartas.\n"
            "En tu Fase Final, agrupa hasta dos Aliados.\n"
            "Los Talismanes cuestan un Oro adicional."
        ),
        "image_file": "mazo_guerreros_016.png",
        "cloudinary_id": "guerreros_16",
    },
    {
        "myl_id": "custom_mig_17",
        "edid": "MIG-17",
        "slug": "bandido-esqueleto-mig",
        "name": "Bandido Esqueleto",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Furia.\n"
            "Cuando entra en juego, Roba una carta y puedes jugar un Aliado "
            "o Arma de tu mano o Cementerio pagando su coste. Si jugaste un "
            "Bandido de esta forma, genera un Oro por el turno para jugar "
            "Aliados o Armas."
        ),
        "image_file": "mazo_guerreros_017.png",
        "cloudinary_id": "guerreros_17",
    },
    {
        "myl_id": "custom_mig_18",
        "edid": "MIG-18",
        "slug": "bandido-neira-mig",
        "name": "Bandido Neira",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Furia.\n"
            "Cuando hace daño al Castillo oponente, puedes Desterrar hasta "
            "dos cartas de un Cementerio. Si controlas dos o más Bandido, en "
            "vez de eso puedes poner un Oro de un Cementerio como un Oro sin "
            "habilidad en tu Oro Pagado."
        ),
        "image_file": "mazo_guerreros_018.png",
        "cloudinary_id": "guerreros_18",
    },
    {
        "myl_id": "custom_mig_19",
        "edid": "MIG-19",
        "slug": "la-torre-mig",
        "name": "La Torre",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "3",
        "damage": "2",
        "ability": (
            "Furia.\n"
            "Sólo puede ser puesto en juego un La Torre por turno.\n"
            "Cuando entra en juego, busca en tu Castillo o Cementerio un "
            "Aliado de coste 2 o menos y juégalo sin pagar su coste.\n"
            "Gana 1 de Fuerza por cada otro Aliado que controles."
        ),
        "image_file": "mazo_guerreros_019.png",
        "cloudinary_id": "guerreros_19",
    },
    {
        "myl_id": "custom_mig_20",
        "edid": "MIG-20",
        "slug": "dhampir-mig",
        "name": "Dhampir",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "4",
        "damage": "2",
        "ability": (
            "Furia.\n"
            "Cuando ataca, entra o sale del juego, muestra un Aliado de tu "
            "mano y Destierra hasta una carta de coste 3 o menos o Roba dos "
            "cartas.\n"
            "Cuando tu oponente juegue una carta, hasta tres veces por turno, "
            "él Bota dos cartas. Si es tu turno, en vez de eso las Destierra."
        ),
        "image_file": "mazo_guerreros_020.png",
        "cloudinary_id": "guerreros_20",
    },
    {
        "myl_id": "custom_mig_21",
        "edid": "MIG-21",
        "slug": "shakar-raj-mig",
        "name": "Shakar Raj",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": "0",
        "ability": (
            "Única. Furia.\n"
            "Cuando entra en juego, un Aliado gana 1 de Fuerza permanentemente.\n"
            "En tu Fase Final, Destierra hasta tantas cartas de un Cementerio "
            "como Aliados hayan modificado su Fuerza este turno más uno."
        ),
        "image_file": "mazo_guerreros_021.png",
        "cloudinary_id": "guerreros_21",
    },
    {
        "myl_id": "custom_mig_22",
        "edid": "MIG-22",
        "slug": "sacrificio-solar-mig",
        "name": "Sacrificio Solar",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "0",
        "damage": None,
        "ability": (
            "Única.\n"
            "Anula o cancela la habilidad de una carta de coste 0 o jugada "
            "sin pagar su coste este turno.\n"
            "Puedes pagar un Oro y Barajar esta carta desde tu mano para "
            "Desterrar o Barajar una carta de coste 2 o menos y Robar una carta."
        ),
        "image_file": "mazo_guerreros_022.png",
        "cloudinary_id": "guerreros_22",
    },
    {
        "myl_id": "custom_mig_23",
        "edid": "MIG-23",
        "slug": "ciempies-sp-mig",
        "name": "Ciempiés-SP",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": "Única.\nAnula una carta de coste 3 o menos.",
        "image_file": "mazo_guerreros_023.png",
        "cloudinary_id": "guerreros_23",
    },
    {
        "myl_id": "custom_mig_24",
        "edid": "MIG-24",
        "slug": "sheut-mig",
        "name": "Sheut",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "Si controlas menos Oros que tu oponente, puedes jugarlo por un "
            "Oro menos. Cuando lo juegues, Destiérralo.\n"
            "Anula un Aliado o Tótem, de coste 1 o menos, o cancela la "
            "habilidad de una carta."
        ),
        "image_file": "mazo_guerreros_024.png",
        "cloudinary_id": "guerreros_24",
    },
    {
        "myl_id": "custom_mig_25",
        "edid": "MIG-25",
        "slug": "ataque-bandido-mig",
        "name": "Ataque Bandido",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "0",
        "damage": None,
        "ability": (
            "Busca un Bandido en tu Castillo y ponlo en tu mano o juega un "
            "Arma o Tótem de tu Cementerio o Destierro pagando su coste.\n"
            "Puedes pagar un Oro y Desterrarlo de tu Cementerio para que un "
            "Arma o Tótem de coste 3 o menos pierda su habilidad y sea Destruido."
        ),
        "image_file": "mazo_guerreros_025.png",
        "cloudinary_id": "guerreros_25",
    },
    {
        "myl_id": "custom_mig_26",
        "edid": "MIG-26",
        "slug": "dragon-dorado-mig",
        "name": "Dragón Dorado",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "0",
        "damage": None,
        "ability": (
            "Única.\n"
            "Cuando juegues este Talismán, Destiérralo.\n"
            "Anula una carta. Luego, Baraja tantas cartas de tu mano como "
            "coste tenga."
        ),
        "image_file": "mazo_guerreros_026.png",
        "cloudinary_id": "guerreros_26",
    },
    {
        "myl_id": "custom_mig_27",
        "edid": "MIG-27",
        "slug": "cuervo-nocturno-mig",
        "name": "Cuervo Nocturno",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "2",
        "damage": None,
        "ability": (
            "No puede ser Anulado. Si atacaste en tu turno anterior, tiene "
            "Exhumar en tu Cementerio.\n"
            "Puedes poner esta y otra carta de tu mano en el fondo de tu "
            "Castillo y Robar dos cartas.\n"
            "Sólo puedes utilizar esta habilidad de Cuervo Nocturno una vez "
            "por turno.\n"
            "Destierra seis cartas del tope del Castillo oponente."
        ),
        "image_file": "mazo_guerreros_027.png",
        "cloudinary_id": "guerreros_27",
    },
    {
        "myl_id": "custom_mig_28",
        "edid": "MIG-28",
        "slug": "aaru-mig",
        "name": "Aaru",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "3",
        "damage": None,
        "ability": (
            "Sólo puedes jugar un Aaru por turno y cuesta un Oro menos por "
            "cada Oro que controles.\n"
            "Baraja cualquier cantidad de cartas de tu mano en tu Castillo. "
            "Luego, pon la misma cantidad de cartas de la parte superior de "
            "tu Castillo en tu mano más dos cartas."
        ),
        "image_file": "mazo_guerreros_028.png",
        "cloudinary_id": "guerreros_28",
    },
    {
        "myl_id": "custom_mig_29",
        "edid": "MIG-29",
        "slug": "tempilcahue-mig",
        "name": "Tempilcahue",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "0",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo. Elige un efecto:\n"
            "- Busca una carta en tu Castillo, ponla en tu mano y Roba una "
            "carta. No puedes jugar más cartas este turno.\n"
            "- Paga dos Oros para Barajar cartas cuyos costes sumen hasta 4 "
            "y Robar dos cartas."
        ),
        "image_file": "mazo_guerreros_029.png",
        "cloudinary_id": "guerreros_29",
    },
    {
        "myl_id": "custom_mig_30",
        "edid": "MIG-30",
        "slug": "vision-heroica-mig",
        "name": "Visión Heroica",
        "type_slug": "talisman",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "Única.\n"
            "Baraja una carta de coste 3 o menos o Anula un Talismán oponente.\n"
            "Puedes pagar un Oro para subir esta carta de tu Cementerio a tu "
            "mano y Robar una carta."
        ),
        "image_file": "mazo_guerreros_030.png",
        "cloudinary_id": "guerreros_30",
    },
    {
        "myl_id": "custom_mig_31",
        "edid": "MIG-31",
        "slug": "chakram-mig",
        "name": "Chakram",
        "type_slug": "arma",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "El portador gana 2 de Fuerza e Indesterrable.\n"
            "Una vez por turno, puedes mirar la mano de tu oponente y elegir "
            "una carta de ahí que no sea Oro para que no pueda ser jugada "
            "hasta tu próximo turno y Roba una carta."
        ),
        "image_file": "mazo_guerreros_031.png",
        "cloudinary_id": "guerreros_31",
    },
    {
        "myl_id": "custom_mig_32",
        "edid": "MIG-32",
        "slug": "espada-vikinga-mig",
        "name": "Espada Vikinga",
        "type_slug": "arma",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "El portador gana 2 de Fuerza.\n"
            "Cuando entra en juego, Roba dos cartas y Baraja una carta "
            "oponente de coste igual o menor a la cantidad de Aliados que "
            "controles.\n"
            "Puedes pagar un Oro y Desterrar esta carta de tu mano para "
            "Anular una carta de coste 1."
        ),
        "image_file": "mazo_guerreros_032.png",
        "cloudinary_id": "guerreros_32",
    },
    {
        "myl_id": "custom_mig_33",
        "edid": "MIG-33",
        "slug": "estaca-mig",
        "name": "Estaca",
        "type_slug": "arma",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "El portador gana 2 de Fuerza y Furia.\n"
            "Una vez por turno, puedes Robar tres cartas, Barajar una carta "
            "oponente que no sea Oro y tantas cartas de tu mano como coste "
            "tenga.\n"
            "Puedes Desterrarla para prevenir que una carta sea afectada por "
            "un efecto oponente."
        ),
        "image_file": "mazo_guerreros_033.png",
        "cloudinary_id": "guerreros_33",
    },
    {
        "myl_id": "custom_mig_34",
        "edid": "MIG-34",
        "slug": "canon-helios-mig",
        "name": "Cañón Helios",
        "type_slug": "arma",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "El portador gana 2 de Fuerza y Furia.\n"
            "Cuando entra en juego, Roba dos cartas.\n"
            "Cuando el portador ataca, puedes elegir un Aliado oponente para "
            "que lo bloquee.\n"
            "Puedes Desterrarlo para Anular un Talismán o prevenir que un "
            "Aliado sea afectado por un efecto oponente."
        ),
        "image_file": "mazo_guerreros_034.png",
        "cloudinary_id": "guerreros_34",
    },
    {
        "myl_id": "custom_mig_35",
        "edid": "MIG-35",
        "slug": "espada-de-ohiggins-mig",
        "name": "Espada de O'Higgins",
        "type_slug": "arma",
        "race_slug": "guerrero",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "El portador gana 2 de Fuerza e Indesterrable.\n"
            "En tu Vigilia, una vez por turno, puedes Barajar una carta que "
            "no sea Oro o buscar un Oro en tu Castillo y ponerlo en tu mano.\n"
            "En tu Fase Final, Destierra hasta tres cartas de los Cementerios "
            "y Roba dos cartas."
        ),
        "image_file": "mazo_guerreros_035.png",
        "cloudinary_id": "guerreros_35",
    },
    {
        "myl_id": "custom_mig_36",
        "edid": "MIG-36",
        "slug": "biblioteca-de-caballeria-mig",
        "name": "Biblioteca de Caballería",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "En la Fase Final oponente, si no controlas Aliados o si en tu "
            "turno anterior un Aliado fue Anulado o su habilidad fue cancelada, "
            "Roba una carta y pon bajo tu control la primera carta de un "
            "Castillo como un Aliado de Fuerza 2 sin habilidad."
        ),
        "image_file": "mazo_guerreros_036.png",
        "cloudinary_id": "guerreros_36",
    },
    {
        "myl_id": "custom_mig_37",
        "edid": "MIG-37",
        "slug": "fuente-de-la-juventud-mig",
        "name": "Fuente de la Juventud",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, Roba dos cartas.\n"
            "A los jugadores les cuesta un Oro adicional jugar Talismanes si "
            "han jugado Talismanes este turno y les cuesta un Oro adicional "
            "poner Oros en juego si han puesto Oros en juego este turno."
        ),
        "image_file": "mazo_guerreros_037.png",
        "cloudinary_id": "guerreros_37",
    },
    {
        "myl_id": "custom_mig_38",
        "edid": "MIG-38",
        "slug": "don-de-amma-mig",
        "name": "Don de Amma",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando tu oponente ponga su segundo Oro en juego este turno, "
            "puedes poner este Oro desde tu mano o Cementerio en tu Oro Pagado.\n"
            "Una vez por turno, puedes Desterrar un Oro con habilidad de tu "
            "Reserva. Luego, busca un Oro en tu Castillo y ponlo en tu Reserva."
        ),
        "image_file": "mazo_guerreros_038.png",
        "cloudinary_id": "guerreros_38",
    },
    {
        "myl_id": "custom_mig_39",
        "edid": "MIG-39",
        "slug": "dracula-mig",
        "name": "Drácula",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Las habilidades de este Oro no pueden ser canceladas.\n"
            "Cuando entra en juego, Roba dos cartas.\n"
            "Puedes convertirlo en un Oro sin habilidad para prevenir que una "
            "habilidad sea cancelada o un Aliado de coste 1 sea Anulado.\n"
            "Puedes Desterrarlo de tu mano o Cementerio para cancelar el "
            "ataque de hasta dos Aliados."
        ),
        "image_file": "mazo_guerreros_039.png",
        "cloudinary_id": "guerreros_39",
    },
    {
        "myl_id": "custom_mig_40",
        "edid": "MIG-40",
        "slug": "signo-amarillo-mig",
        "name": "Signo Amarillo",
        "type_slug": "oro",
        "race_slug": "guerrero",
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
        "image_file": "mazo_guerreros_040.png",
        "cloudinary_id": "guerreros_40",
    },
    {
        "myl_id": "custom_mig_41",
        "edid": "MIG-41",
        "slug": "aegishjalmur-mig",
        "name": "Aegishjalmur",
        "type_slug": "oro",
        "race_slug": "guerrero",
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
        "image_file": "mazo_guerreros_041.png",
        "cloudinary_id": "guerreros_41",
    },
    {
        "myl_id": "custom_mig_42",
        "edid": "MIG-42",
        "slug": "estrella-de-kirin-mig",
        "name": "Estrella de Kirin",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, muestra cartas del tope de tu Castillo "
            "hasta mostrar un Oro y un Arma o Tótem y ponlos en tu mano.\n"
            "Puedes pagarlo y convertirlo en un Oro sin habilidad para "
            "convertir un Oro o carta de coste 2 o menos en una carta del "
            "mismo tipo sin habilidad."
        ),
        "image_file": "mazo_guerreros_042.png",
        "cloudinary_id": "guerreros_42",
    },
    {
        "myl_id": "custom_mig_43",
        "edid": "MIG-43",
        "slug": "tyet-mig",
        "name": "Tyet",
        "type_slug": "oro",
        "race_slug": "guerrero",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, busca un Arma o un Oro en tu Castillo y "
            "ponlo en tu mano.\n"
            "Puedes pagarlo para que un Oro pierda su habilidad este turno y "
            "muévelo al Oro Pagado.\n"
            "Puedes poner esta y otra carta de tu mano en el fondo de tu "
            "Castillo y Robar dos cartas.\n"
            "Sólo puedes utilizar esta habilidad de Tyet una vez por turno."
        ),
        "image_file": "mazo_guerreros_043.png",
        "cloudinary_id": "guerreros_43",
    },
]


class Command(BaseCommand):
    help = "Seed Mazo Imperio de Guerreros (43 cards) into AYDV edition"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-upload",
            action="store_true",
            help="Skip Cloudinary upload (use existing mapping)",
        )

    def handle(self, *args, **options):
        # ── 1. Create/get edition ───────────────────────────────────
        imp_format = Format.objects.get(code="imp")
        edition, ed_created = Edition.objects.update_or_create(
            myl_id="custom_aydv_mazo_guerreros",
            defaults={
                "slug": "aydv-mazo-guerreros",
                "title": "Ángeles y Demonios: Vigilantes - Mazo Guerreros",
                "image": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/MAZO_GUERRERO.png",
                "date_release": "2026-07-03",
                "format": imp_format,
                "active": True,
            },
        )
        action = "Created" if ed_created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{action} edition: {edition.title} (pk={edition.pk})"
        ))

        # ── 2. Upload images to Cloudinary ──────────────────────────
        cloudinary_urls = {}
        if os.path.exists(MAPPING_FILE):
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                cloudinary_urls = json.load(f)

        if not options["skip_upload"]:
            self.stdout.write(self.style.MIGRATE_HEADING(
                "\nUploading images to Cloudinary..."
            ))
            source = os.path.normpath(SOURCE_FOLDER)
            if not os.path.isdir(source):
                self.stderr.write(
                    f"Source folder not found: {source}\n"
                    f"Run 'python download_mazo_guerreros.py --download-only' first."
                )
                return

            for card_data in MAZO_GUERREROS_CARDS:
                cid = card_data["cloudinary_id"]
                if cid in cloudinary_urls:
                    continue

                filepath = os.path.join(source, card_data["image_file"])
                if not os.path.exists(filepath):
                    self.stderr.write(f"  Missing: {card_data['image_file']}")
                    continue

                public_id = f"{CLOUDINARY_FOLDER}/{cid}"
                try:
                    result = cloudinary.uploader.upload(
                        filepath,
                        public_id=public_id,
                        overwrite=True,
                        resource_type="image",
                    )
                    url = result["secure_url"]
                    cloudinary_urls[cid] = url
                    self.stdout.write(f"  Uploaded: {cid} → {url}")
                except Exception as e:
                    self.stderr.write(f"  ERROR uploading {cid}: {e}")

            # Save mapping
            with open(MAPPING_FILE, "w", encoding="utf-8") as f:
                json.dump(cloudinary_urls, f, indent=2, ensure_ascii=False)
            self.stdout.write(f"  Mapping saved: {MAPPING_FILE}")

        # ── 3. Create cards ─────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nSeeding {len(MAZO_GUERREROS_CARDS)} cards..."
        ))

        promo_rarity = Rarity.objects.filter(slug="promo").first()
        created_count = 0
        updated_count = 0

        for card_data in MAZO_GUERREROS_CARDS:
            card_type = CardType.objects.filter(slug=card_data["type_slug"]).first()
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
            f"\nDone! Created: {created_count}, Updated: {updated_count} "
            f"({len(MAZO_GUERREROS_CARDS)} total cards in AYDV Mazo Guerreros)"
        ))
