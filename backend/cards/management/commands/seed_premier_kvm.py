"""
Seed extra Premier KVM cards that are not available in the MYL API.
Card data extracted manually from card images.
"""
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity

# PythonAnywhere media base URL
MEDIA_BASE = "https://iterva.pythonanywhere.com/media/extra_cards"

PREMIER_KVM_CARDS = [
    {
        "myl_id": "custom_kvm_219",
        "edid": "219",
        "slug": "resistencia-de-acero-kvm",
        "name": "Resistencia de Acero",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Si está en tu Destierro puedes pagar un Oro para Barajarlo en tu Castillo "
            "y que tu oponente Destierre tres cartas del tope de su Castillo.\n"
            "Busca tres cartas de distinto tipo en el Castillo oponente, Destiérralas y Roba una carta."
        ),
        "flavour": (
            "Los colosos de la tierra son amalgamas de acero y voluntad. "
            "Héroes altruistas que no dudan en ponerse al frente de la lucha."
        ),
        "image_file": "kvm_219.png",
    },
    {
        "myl_id": "custom_kvm_220",
        "edid": "220",
        "slug": "furia-de-titan-kvm",
        "name": "Furia de Titán",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "0",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Elige un Aliado que controles. Hasta tu próximo turno, si está en tu Línea de Ataque "
            "no puede salir del juego por efectos y su daño de combate es enviado al Destierro, "
            "de lo contrario, tu oponente no puede atacar con Aliados de mayor Fuerza que ese Aliado."
        ),
        "flavour": (
            "Los invasores monstruosos tienen muchas formas y objetivos. "
            "Vestigios de lo que alguna vez fue una civilización estelar."
        ),
        "image_file": "kvm_220.png",
    },
    {
        "myl_id": "custom_kvm_221",
        "edid": "221",
        "slug": "sin-tregua-kvm",
        "name": "Sin Tregua",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Busca dos cartas en un Castillo y Destiérralas.\n"
            "Si está en tu Cementerio, los jugadores deben Barajar una carta de su mano "
            "para jugar cartas de coste 0 o sin pagar su coste.\n"
            "Al comienzo de tu Vigilia, puedes subir esta carta de tu Cementerio a tu mano."
        ),
        "flavour": (
            "Las Guerras Titán cambiarán el futuro de la galaxia para siempre. "
            "Creando alianzas imposibles y forjando héroes eternos."
        ),
        "image_file": "kvm_221.png",
    },
    {
        "myl_id": "custom_kvm_230",
        "edid": "230",
        "slug": "dracula-kvm",
        "name": "Drácula",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Las habilidades de este Oro no pueden ser canceladas.\n"
            "Cuando entra en juego, Roba dos cartas.\n"
            "Puedes convertirlo en un Oro sin habilidad para prevenir que una habilidad "
            "sea cancelada o un Aliado de coste 1 sea Anulado.\n"
            "Puedes Desterrarlo de tu mano o Cementerio para cancelar el ataque de hasta dos Aliados."
        ),
        "flavour": None,
        "image_file": "kvm_230.png",
    },
    {
        "myl_id": "custom_kvm_231",
        "edid": "231",
        "slug": "signo-amarillo-kvm",
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
        "flavour": None,
        "image_file": "kvm_231.png",
    },
    {
        "myl_id": "custom_kvm_232",
        "edid": "232",
        "slug": "ciudad-de-los-cesares-kvm",
        "name": "Ciudad de los Césares",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Cuando entra o sale del juego, Baraja hasta una carta oponente de coste 3 o menos "
            "y Roba dos cartas.\n"
            "Una vez por turno, puedes Barajar una carta de tu mano para Anular o Desterrar "
            "una carta de coste 1 o menos, o pagar un Oro para Anular una carta de coste 2 o más."
        ),
        "flavour": None,
        "image_file": "kvm_232.png",
    },
    {
        "myl_id": "custom_kvm_233",
        "edid": "233",
        "slug": "guerrillero-rodriguez-kvm",
        "name": "Guerrillero Rodríguez",
        "type_slug": "aliado",
        "race_slug": "noraza",
        "cost": "2",
        "damage": "1",
        "ability": (
            "Indestructible.\n"
            "Puedes jugarlo al comienzo de la Vigilia.\n"
            "No puede ser afectado por Oros oponentes.\n"
            "Cuando entra en juego, Roba una carta.\n"
            "Las cartas sólo pueden ser puestas en juego desde la mano de su dueño."
        ),
        "flavour": None,
        "image_file": "kvm_233.png",
    },
    {
        "myl_id": "custom_kvm_234",
        "edid": "234",
        "slug": "patria-vieja-kvm",
        "name": "Patria Vieja",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Oro Inicial.\n"
            "En tu Vigilia, si no has puesto Oros en juego este turno, puedes mirar las primeras "
            "seis cartas de tu Castillo y poner un Oro de ahí en tu Reserva.\n"
            "Esta habilidad no puede ser cancelada.\n"
            "Tus Aliados de coste 1 o más ganan 1 de Fuerza y no son Destruidos cuando bloquean."
        ),
        "flavour": None,
        "image_file": "kvm_234.png",
    },
]


class Command(BaseCommand):
    help = "Seed Premier KVM extra cards from blog images"

    def handle(self, *args, **options):
        # Get or create the edition
        imp_format = Format.objects.filter(code="imp").first()
        edition, created = Edition.objects.get_or_create(
            myl_id="custom_premier_kvm",
            defaults={
                "slug": "premier_kvm",
                "title": "IMP - Premier KVM",
                "format": imp_format,
                "active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created edition: {edition.title}"))
        else:
            self.stdout.write(f"Edition already exists: {edition.title}")

        promo_rarity = Rarity.objects.filter(slug="promo").first()

        for card_data in PREMIER_KVM_CARDS:
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
            self.stdout.write(f"  {action}: {card.name} (KVM-{card.edid})")

        self.stdout.write(self.style.SUCCESS(f"\nDone! {len(PREMIER_KVM_CARDS)} Premier KVM cards seeded."))
