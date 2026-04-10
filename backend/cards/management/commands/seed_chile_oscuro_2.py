"""
Seed Chile Oscuro 2 cards (custom edition, not in MYL API).
Card data extracted manually from card images.
"""
from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity

MEDIA_BASE = "https://iterva.pythonanywhere.com/media/extra_cards"

CHILE_OSCURO_2_CARDS = [
    {
        "myl_id": "custom_co2_01",
        "edid": "CHI-01",
        "slug": "la-rubia-de-kennedy-co2",
        "name": "La Rubia de Kennedy",
        "type_slug": "aliado",
        "race_slug": "eterno/faerie",
        "cost": "2",
        "damage": "1",
        "ability": (
            "Exhumar.\n"
            "Cuando entra en juego, puedes buscar una carta en tu Castillo y ponerla "
            "en tu mano o Barajar una carta de coste 2 o menos.\n"
            "Cuando tu oponente juegue una carta o utilice una habilidad, puedes "
            "Barajarla para reducir en cuatro el próximo daño que reciba tu Castillo."
        ),
        "flavour": (
            "Calles vacías y luces parpadeantes; su silueta atrae a los incautos "
            "conductores de las calles de Santiago."
        ),
        "image_file": "c-o-2_0-1.png",
    },
    {
        "myl_id": "custom_co2_03",
        "edid": "CHI-03",
        "slug": "yeti-de-rengo-co2",
        "name": "Yeti de Rengo",
        "type_slug": "aliado",
        "race_slug": "bestia/guerrero",
        "cost": "2",
        "damage": "1",
        "ability": (
            "Furia.\n"
            "Cuando entra en juego, un Aliado gana 2 de Fuerza permanentemente "
            "o Destruye una carta oponente de coste 1 o menos.\n"
            "Cuando este u otro Aliado salga del juego por efectos, una vez por turno, "
            "un Aliado gana su Fuerza permanentemente."
        ),
        "flavour": (
            "Una abominable criatura sembró el pánico en la cordillera Rancagüina. "
            "Su terrible apariencia aterrorizó a los pobladores desamparados."
        ),
        "image_file": "c-o-2_03-1.png",
    },
    {
        "myl_id": "custom_co2_06",
        "edid": "CHI-06",
        "slug": "la-hora-del-diablo-co2",
        "name": "La Hora del Diablo",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando juegues este Talismán, Destiérralo.\n"
            "Busca dos cartas en cada Castillo, ponlas en el Cementerio de su dueño "
            "y Roba una carta.\n"
            "Puedes pagar tres Oros y Barajar tres copias de La Hora del Diablo "
            "de tu Destierro en tu Castillo para Desterrar hasta tres cartas oponentes "
            "de distinto tipo."
        ),
        "flavour": (
            "En la hora más lejana a la muerte del Cristo; las presencias demoníacas "
            "y fenómenos espectrales se concentran maléficamente."
        ),
        "image_file": "c-o-2_06-1.png",
    },
    {
        "myl_id": "custom_co2_07",
        "edid": "CHI-07",
        "slug": "fantasmas-del-palacio-co2",
        "name": "Fantasmas del Palacio",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando lo juegues, puedes pagar un Oro adicional para elegir una carta "
            "de cualquier coste en vez de coste 3 o menos.\n"
            "Baraja una carta de coste 3 o menos.\n"
            "Si está en tu Cementerio, puedes pagar el coste de un Aliado en tu "
            "Cementerio para poner este Talismán en juego como una copia de ese Aliado."
        ),
        "flavour": (
            "El Palacio Echeverría fue el centro del espiritismo nacional. "
            "Incontables espectros aún recorren los pasillos de "
            "\"La casa de los Espíritus\"."
        ),
        "image_file": "c-o-2_07-2.png",
    },
    {
        "myl_id": "custom_co2_10",
        "edid": "CHI-10",
        "slug": "abduccion-del-cabo-co2",
        "name": "Abducción del Cabo",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Sube a la mano de su dueño una carta oponente de coste 3 o menos. "
            "Si esa carta era un Aliado o Tótem, tu oponente no puede jugar cartas "
            "con ese nombre hasta tu próximo turno y tú generas un Oro para jugar "
            "Armas o Tótem."
        ),
        "flavour": (
            "Desaparecido por 15 minutos, el cabo es encontrado con una crecida "
            "barba y su reloj adelantado cinco días del presente."
        ),
        "image_file": "c-o-2_010.png",
    },
    {
        "myl_id": "custom_co2_11",
        "edid": "CHI-11",
        "slug": "avistamientos-co2",
        "name": "Avistamientos",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Elige un efecto. Muestra la primera carta de tu Castillo y si es un "
            "Aliado, elige ambos:\n"
            "- Mira la mano de tu oponente, elige una carta de ahí que no sea Oro "
            "y Barájala en su Castillo.\n"
            "- En la próxima Fase Final oponente, puedes mover un Oro oponente "
            "a su Oro Pagado."
        ),
        "flavour": (
            "Extrañas luces e imposibles objetos recorren las carreteras del norte "
            "Chileno. Camioneros y viajeros son silentes testigos de estos "
            "inexplicables fenómenos."
        ),
        "image_file": "c-o-2_011.png",
    },
    {
        "myl_id": "custom_co2_13",
        "edid": "CHI-13",
        "slug": "contacto-con-friendship-co2",
        "name": "Contacto con Friendship",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Gana el control de un Arma. Si eres el dueño de esa Arma, genera un "
            "Oro por el turno.\n"
            "Si atacaste o bloqueaste desde tu turno anterior, puedes Desterrarlo "
            "de tu mano o Cementerio para prevenir que tu oponente Baraje y/o "
            "Destierre cartas de los Cementerios."
        ),
        "flavour": (
            "Un grupo de radioaficionados estableció contacto con seres de "
            "habilidades curativas únicas y tecnología avanzada. Habitantes de "
            "una isla imposible en el sur del mundo."
        ),
        "image_file": "c-o-2_013-1.png",
    },
    {
        "myl_id": "custom_co2_17",
        "edid": "CHI-17",
        "slug": "cementerio-general-co2",
        "name": "Cementerio General",
        "type_slug": "totem",
        "race_slug": None,
        "cost": "2",
        "damage": None,
        "ability": (
            "Exhumar.\n"
            "Cuando entra en juego, Baraja hasta tantas cartas oponentes de coste 3 "
            "o menos como cartas Exhumar controles y Roba dos cartas.\n"
            "Las cartas en tu Cementerio no pueden perder su habilidad ni ser "
            "Desterradas por efectos.\n"
            "Tus Aliados con Exhumar ganan Furia."
        ),
        "flavour": (
            "Entre sus mausoleos y nichos, terribles apariciones e inexplicables "
            "sensaciones envuelven al epicentro del misterio nacional."
        ),
        "image_file": "c-o-2_017.png",
    },
    {
        "myl_id": "custom_co2_18",
        "edid": "CHI-18",
        "slug": "la-ouija-co2",
        "name": "La Ouija",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, pon la primera o la última carta de tu Castillo "
            "en tu mano.\n"
            "Una vez por turno, puedes jugar una carta de tu Cementerio o del tope "
            "de tu Castillo.\n"
            "Juega mostrando la primera carta de tu Castillo."
        ),
        "flavour": (
            "Las Hermanas Morla y el palacio Echeverría fueron el centro del "
            "espiritismo nacional. En sus sesiones se utilizó para contactar con "
            "fuerzas desconocidas."
        ),
        "image_file": "c-o-2_018.png",
    },
    {
        "myl_id": "custom_co2_19",
        "edid": "CHI-19",
        "slug": "romualdito-co2",
        "name": "Romualdito",
        "type_slug": "oro",
        "race_slug": None,
        "cost": None,
        "damage": None,
        "ability": (
            "Al comienzo de la Vigilia, si no tienes Oros en Reserva, Destierra dos "
            "cartas del tope de un Castillo y hasta una carta de un Cementerio.\n"
            "Puedes convertirlo en un Oro sin habilidad para prevenir que un Aliado "
            "sea Destruido, cambie de controlador o sea convertido, por un efecto "
            "oponente."
        ),
        "flavour": (
            "Perdido entre el humo y la cera de miles de velas, poco queda de la "
            "animita original. En su lugar, un muro inmenso reúne peticiones y "
            "agradecimientos."
        ),
        "image_file": "c-o-2_019-1.png",
    },
    {
        "myl_id": "custom_co2_20",
        "edid": "CHI-20",
        "slug": "psicofonia-co2",
        "name": "Psicofonía",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Elige un efecto. Si pagaste dos Oros por este Talismán, no se pueden "
            "jugar cartas ni utilizar habilidades en respuesta a esta carta.\n"
            "- Una carta de coste 2 o menos pierde su habilidad, es Desterrada "
            "y Roba una carta.\n"
            "- Paga un Oro para que un Aliado pierda su habilidad, sea Desterrado "
            "y Roba dos cartas."
        ),
        "flavour": (
            "A veces de manera intencionada, a veces por azar. Voces espectrales "
            "son atrapadas en ondas de audio. ¿Interferencias casuales o mensajes "
            "del más allá?"
        ),
        "image_file": "c-o-2_020.png",
    },
    {
        "myl_id": "custom_co2_21",
        "edid": "CHI-21",
        "slug": "sesion-espiritista-co2",
        "name": "Sesión Espiritista",
        "type_slug": "talisman",
        "race_slug": None,
        "cost": "1",
        "damage": None,
        "ability": (
            "Cuando lo juegues, Destiérralo.\n"
            "Hasta tu próximo turno cada vez que tu oponente ponga cartas en su mano "
            "por un efecto, puedes poner esa misma cantidad de cartas del tope de "
            "tu Castillo en tu mano.\n"
            "Por el resto del juego el daño de combate a tu Castillo se reduce en dos."
        ),
        "flavour": (
            "Velas y murmullos llenan la habitación. La sesión abre puertas entre "
            "vivos y espíritus, conectando dos mundos que no deberían coexistir."
        ),
        "image_file": "c-o-2_021-1.png",
    },
]


class Command(BaseCommand):
    help = "Seed Chile Oscuro 2 extra cards"

    def handle(self, *args, **options):
        imp_format = Format.objects.filter(code="imp").first()
        edition, created = Edition.objects.get_or_create(
            myl_id="custom_chile_oscuro_2",
            defaults={
                "slug": "chile_oscuro_2",
                "title": "IMP - Chile Oscuro 2",
                "format": imp_format,
                "active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created edition: {edition.title}"))
        else:
            self.stdout.write(f"Edition already exists: {edition.title}")

        promo_rarity = Rarity.objects.filter(slug="promo").first()

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
            f"\nDone! {len(CHILE_OSCURO_2_CARDS)} Chile Oscuro 2 cards seeded."
        ))
