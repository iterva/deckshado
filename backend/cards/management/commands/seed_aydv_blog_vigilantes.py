"""
Seed Ángeles y Demonios: Vigilantes - Cartas Blog (Promos, Secretas, Ultra Secretas, Showcase).
  - Creates the main AYDV edition (booster set)
  - Uses pre-uploaded Cloudinary images (aydv_blog_vigilantes_mapping.json)
  - Creates 28 cards: 19 promos, 3 secretas, 3 ultra secretas, 3 showcase (base set)

Usage:
    python manage.py seed_aydv_blog_vigilantes
"""
import os
import json

from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, Race, CardType, Rarity


MAPPING_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "aydv_blog_vigilantes_mapping.json",
)

# ── Card Data ────────────────────────────────────────────────────────────────

CARDS = [
    # ═══ KIT DE BATALLA - REPRINTS (shared) ═══════════════════════════════════
    {
        "myl_id": "custom_aydv_175",
        "edid": "AYDV-175",
        "slug": "serafin-aydv-p",
        "name": "Serafín",
        "type_slug": "aliado",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Cuando entra en juego, nombra una carta. Utilizar habilidades "
            "de la carta nombrada cuesta un Oro adicional hasta tu próximo "
            "turno. Puedes Desterrarlo para prevenir que un Aliado o Tótem "
            "sea Anulado o su habilidad cancelada."
        ),
        "cloudinary_id": "aydv_175",
    },
    {
        "myl_id": "custom_aydv_176",
        "edid": "AYDV-176",
        "slug": "santo-santo-santo-aydv-p",
        "name": "Santo, Santo, Santo",
        "type_slug": "talisman",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "2",
        "damage": None,
        "ability": (
            "Sólo puede jugarse pagando su coste impreso. Tu oponente "
            "Descarta tres cartas al azar de su mano. Por cada carta "
            "Descartada de esta forma, tu oponente puede Desterrar cuatro "
            "cartas del tope de su Castillo para subir esa carta del "
            "Cementerio a su mano y tú Robas una carta."
        ),
        "cloudinary_id": "aydv_176",
    },
    {
        "myl_id": "custom_aydv_179",
        "edid": "AYDV-179",
        "slug": "mano-de-destruccion-aydv-p",
        "name": "Mano de Destrucción",
        "type_slug": "talisman",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "1",
        "damage": None,
        "ability": (
            "Convierte un Oro oponente en un Oro sin habilidad, o una carta "
            "de coste 4 o menos pierde su habilidad y es Desterrada. Puedes "
            "Desterrarlo de tu Cementerio para buscar un Oro en tu Castillo. "
            "Si es tu turno y no has puesto Oros en juego este turno, ponlo "
            "en tu Oro Pagado. Si no, ponlo en tu mano."
        ),
        "cloudinary_id": "aydv_179",
    },
    {
        "myl_id": "custom_aydv_180",
        "edid": "AYDV-180",
        "slug": "miguel-grau-aydv-p",
        "name": "Miguel Grau",
        "type_slug": "aliado",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "2",
        "damage": "1",
        "ability": (
            "Cuando entra en juego, Baraja hasta tres cartas de los "
            "Cementerios y Roba dos cartas. Puedes Barajarlo para Destruir "
            "una carta de coste 2 o menos. Si Botas esta carta desde tu "
            "Castillo por daño, dejas de Botar cartas y Destierra este Aliado."
        ),
        "cloudinary_id": "aydv_180",
    },
    {
        "myl_id": "custom_aydv_181",
        "edid": "AYDV-181",
        "slug": "alicia-en-wonderland-aydv-p",
        "name": "Alicia en Wonderland",
        "type_slug": "aliado",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Cuando entra en juego, muestra cartas del tope de tu Castillo "
            "hasta mostrar dos Aliados de distinto coste y ponlos en tu mano. "
            "Cuando entra en juego, nombra una carta para que pierdan su "
            "habilidad en todas las Zonas mientras este Aliado esté en juego."
        ),
        "cloudinary_id": "aydv_181",
    },
    # ═══ KIT BATALLA SERAFÍN (exclusivas) ═════════════════════════════════════
    {
        "myl_id": "custom_aydv_182",
        "edid": "AYDV-182",
        "slug": "lanza-argenta-aydv-p",
        "name": "Lanza Argenta",
        "type_slug": "arma",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "1",
        "damage": None,
        "ability": (
            "El portador gana 2 de Fuerza e Indesterrable. Puedes Destruir "
            "esta Arma para cancelar una habilidad o Robar tres cartas. "
            "Cuando sea puesta en tu Cementerio, Baraja esta carta y hasta "
            "otras dos cartas de un Cementerio en el Castillo de su dueño."
        ),
        "cloudinary_id": "aydv_182",
    },
    {
        "myl_id": "custom_aydv_183",
        "edid": "AYDV-183",
        "slug": "dulce-canasta-aydv-p",
        "name": "Dulce Canasta",
        "type_slug": "oro",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, busca un Oro en tu Castillo o Cementerio "
            "y ponlo en tu mano. Una vez por turno, un Aliado gana o pierde "
            "2 de Fuerza permanentemente. Si está en tu Reserva, los Aliados "
            "de coste 1 o menos no pueden ser Desterrados."
        ),
        "cloudinary_id": "aydv_183",
    },
    # ═══ KIT BATALLA BELIAL (exclusivas) ══════════════════════════════════════
    {
        "myl_id": "custom_aydv_184",
        "edid": "AYDV-184",
        "slug": "belial-aydv-p",
        "name": "Belial",
        "type_slug": "aliado",
        "race_slug": "demonio",
        "rarity_slug": "promo",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Puedes Botar dos cartas para subirlo de tu Cementerio a tu mano. "
            "Sólo puedes utilizar esta habilidad de Belial una vez por turno. "
            "Cuando entra en juego, Destierra hasta una carta de coste 2 o "
            "menos y Roba una carta."
        ),
        "cloudinary_id": "aydv_184",
    },
    {
        "myl_id": "custom_aydv_186",
        "edid": "AYDV-186",
        "slug": "don-de-belial-aydv-p",
        "name": "Don de Belial",
        "type_slug": "oro",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": None,
        "damage": None,
        "ability": (
            "Cuando entra en juego, busca un Oro en tu Castillo y ponlo en "
            "tu mano. Puedes pagarlo y convertirlo en un Oro sin habilidad "
            "para subir otro Oro que controles a la mano. Si lo haces, pon "
            "un Oro de tu mano en tu Oro Pagado."
        ),
        "cloudinary_id": "aydv_186",
    },
    # ═══ TORNEO LANZAMIENTO ═══════════════════════════════════════════════════
    {
        "myl_id": "custom_aydv_190",
        "edid": "AYDV-190",
        "slug": "gehena-aydv-p",
        "name": "Gehena",
        "type_slug": "totem",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "2",
        "damage": None,
        "ability": (
            "Una vez por turno, puedes mirar la mano de tu oponente y nombrar "
            "dos cartas que no sean Talismán. Busca una de ellas en el "
            "Castillo oponente y Destiérrala y busca la otra en tu Castillo "
            "y ponla en tu mano. En tu Fase Final, agrupa un Oro y Roba una "
            "carta."
        ),
        "cloudinary_id": "aydv_190",
    },
    {
        "myl_id": "custom_aydv_191",
        "edid": "AYDV-191",
        "slug": "altar-de-moloch-aydv-p",
        "name": "Altar de Moloch",
        "type_slug": "totem",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "2",
        "damage": None,
        "ability": (
            "Cuando entra en juego, Roba una carta y tus Aliados no pueden "
            "salir del juego en Batalla Mitológica hasta tu próximo turno. "
            "Una vez por turno, puedes pagar el coste de una carta oponente "
            "de la que seas dueño para subirla a tu mano y jugarla sin pagar "
            "su coste."
        ),
        "cloudinary_id": "aydv_191",
    },
    # ═══ PROFECÍAS ════════════════════════════════════════════════════════════
    {
        "myl_id": "custom_aydv_192",
        "edid": "AYDV-192",
        "slug": "custodios-aydv-p",
        "name": "Custodios",
        "type_slug": "aliado",
        "race_slug": "caballero/guerrero/heroe",
        "rarity_slug": "promo",
        "cost": "5",
        "damage": "3",
        "ability": (
            "Furia. Imbloqueable. Cuando entra en juego, puedes jugar un "
            "Arma de coste 2 o menos desde tu mano o Cementerio sin pagar "
            "su coste. Una vez por turno, puedes Barajar un Arma que "
            "controles o de tu mano para prevenir un efecto que fuera a "
            "afectar una de tus cartas."
        ),
        "cloudinary_id": "aydv_192",
    },
    {
        "myl_id": "custom_aydv_194",
        "edid": "AYDV-194",
        "slug": "nefandos-aydv-p",
        "name": "Nefandos",
        "type_slug": "aliado",
        "race_slug": "bestia/dragon/sombra",
        "rarity_slug": "promo",
        "cost": "4",
        "damage": "3",
        "ability": (
            "Furia. Exhumar. Cuando entra en juego, puedes jugar un Aliado "
            "de coste 2 o menos desde tu mano o Cementerio sin pagar su "
            "coste. Tus demás Aliados no pueden ser Desterrados y hacen daño "
            "de combate al Destierro."
        ),
        "cloudinary_id": "aydv_194",
    },
    {
        "myl_id": "custom_aydv_195",
        "edid": "AYDV-195",
        "slug": "paladin-david-aydv-p",
        "name": "Paladín David",
        "type_slug": "aliado",
        "race_slug": "caballero/guerrero/heroe",
        "rarity_slug": "promo",
        "cost": "4",
        "damage": "2",
        "ability": (
            "Indestructible. Una vez por turno, puedes buscar un Aliado, "
            "Arma u Oro en tu Castillo y ponlo en tu mano. En cada Fase "
            "Final, puedes Barajar y/o Desterrar hasta dos cartas de los "
            "Cementerios. Tus Aliados ganan Imbloqueable y si portan Armas, "
            "hacen daño de combate al Destierro."
        ),
        "cloudinary_id": "aydv_195",
    },
    {
        "myl_id": "custom_aydv_199",
        "edid": "AYDV-199",
        "slug": "torre-de-babel-aydv-p",
        "name": "Torre de Babel",
        "type_slug": "totem",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "2",
        "damage": None,
        "ability": (
            "Exhumar. Cuando entra en juego, elige cartas cuyos costes sumen "
            "4 o menos para que pierdan su habilidad y sean Barajadas. Una "
            "vez por turno, puedes Barajar una carta de tu mano para Barajar "
            "y/o Desterrar hasta cinco cartas de los Cementerios y Robar dos "
            "cartas."
        ),
        "cloudinary_id": "aydv_199",
    },
    # ═══ BUY-A-BOX (Jinetes del Apocalipsis) ═════════════════════════════════
    {
        "myl_id": "custom_aydv_213",
        "edid": "AYDV-213",
        "slug": "jinete-de-la-peste-aydv-p",
        "name": "Jinete de la Peste",
        "type_slug": "aliado",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "1",
        "damage": "1",
        "ability": (
            "Exhumar. Imbloqueable. Una vez por turno, busca en un Castillo "
            "dos cartas de distinto nombre y Destiérralas. Si controlas otro "
            "Jinete, además Roba una carta. Si controlas cuatro Aliados "
            "Jinete, tu oponente no puede poner cartas en su mano por "
            "efectos."
        ),
        "cloudinary_id": "aydv_213",
    },
    {
        "myl_id": "custom_aydv_214",
        "edid": "AYDV-214",
        "slug": "jinete-de-la-guerra-aydv-p",
        "name": "Jinete de la Guerra",
        "type_slug": "aliado",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "2",
        "damage": "1",
        "ability": (
            "Exhumar. Furia. Una vez en tu turno, puedes Destruir hasta una "
            "carta de coste 1 o menos. Si controlas otro Jinete, además "
            "busca en tu Castillo o Cementerio un Jinete y ponlo en tu mano. "
            "Si controlas cuatro Aliados Jinete, ganan Furia y su daño es "
            "enviado al Destierro."
        ),
        "cloudinary_id": "aydv_214",
    },
    {
        "myl_id": "custom_aydv_215",
        "edid": "AYDV-215",
        "slug": "jinete-del-hambre-aydv-p",
        "name": "Jinete del Hambre",
        "type_slug": "aliado",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "3",
        "damage": "1",
        "ability": (
            "Exhumar. Indestructible. Una vez por turno, puedes Desterrar "
            "una carta de tu mano para prevenir que un Jinete salga del "
            "juego o Robar una carta. Si controlas otro Jinete, además tu "
            "oponente Descarta una carta. Si controlas cuatro Aliados "
            "Jinete, tu oponente puede utilizar hasta tres habilidades por "
            "turno."
        ),
        "cloudinary_id": "aydv_215",
    },
    {
        "myl_id": "custom_aydv_216",
        "edid": "AYDV-216",
        "slug": "jinete-de-la-muerte-aydv-p",
        "name": "Jinete de la Muerte",
        "type_slug": "aliado",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "4",
        "damage": "2",
        "ability": (
            "Exhumar. Indesterrable. Una vez por turno, si está en tu "
            "Destierro, puedes Barajarlo con hasta a otro Jinete de ahí. "
            "Una vez por turno, Destierra una carta que no sea Oro. Si "
            "controlas cuatro Aliados Jinete, en vez de eso, las cartas que "
            "no sean Jinete ni Oro pierden su habilidad y son Destruidas."
        ),
        "cloudinary_id": "aydv_216",
    },
    # ═══ SECRETAS ═════════════════════════════════════════════════════════════
    {
        "myl_id": "custom_aydv_160",
        "edid": "AYDV-160",
        "slug": "miguel-aydv-s",
        "name": "Miguel",
        "type_slug": "aliado",
        "race_slug": "caballero",
        "rarity_slug": "secreta",
        "cost": "5",
        "damage": "3",
        "ability": (
            "Furia. Imbloqueable. Cuando entra en juego, tu oponente "
            "Descarta dos cartas y tú Robas hasta dos cartas. Esta habilidad "
            "no puede ser cancelada. Una vez en tu turno, juega una carta de "
            "tu mano o de un Cementerio reduciendo su coste en un Oro, hasta "
            "un mínimo de 0."
        ),
        "cloudinary_id": "aydv_160_s",
    },
    {
        "myl_id": "custom_aydv_161",
        "edid": "AYDV-161",
        "slug": "angel-gabriel-aydv-s",
        "name": "Ángel Gabriel",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "rarity_slug": "secreta",
        "cost": "4",
        "damage": "3",
        "ability": (
            "Una vez por turno, puedes ganar el control de una carta en "
            "juego que no sea Oro. Al comienzo de tu próximo turno, esa "
            "carta pierde su habilidad y es Barajada. Una vez por turno, "
            "puedes Barajar una carta que no sea Oro o Robar hasta dos "
            "cartas o puedes pagar un Oro para Anular una carta."
        ),
        "cloudinary_id": "aydv_161_s",
    },
    {
        "myl_id": "custom_aydv_167",
        "edid": "AYDV-167",
        "slug": "lucifer-aydv-s",
        "name": "Lucifer",
        "type_slug": "aliado",
        "race_slug": "sombra",
        "rarity_slug": "secreta",
        "cost": "4",
        "damage": "2",
        "ability": (
            "Exhumar. Una vez por turno, puedes Descartar una carta para "
            "prevenir que otra carta sea afectada por un efecto oponente o "
            "generar un Oro para Aliados. Una vez en tu turno, puedes jugar "
            "hasta un Aliado del Destierro oponente, Desterrar dos cartas "
            "del fondo de su Castillo y Robar una carta."
        ),
        "cloudinary_id": "aydv_167_s",
    },
    # ═══ ULTRA SECRETAS (Enoquiano) ═══════════════════════════════════════════
    {
        "myl_id": "custom_aydv_us_gabriel",
        "edid": "AYDV-US01",
        "slug": "gabriel-aydv-us",
        "name": "Gabriel (Ultra Secreta)",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "rarity_slug": "milenaria",
        "cost": "4",
        "damage": "3",
        "ability": (
            "Una vez por turno, puedes ganar el control de una carta en "
            "juego que no sea Oro. Al comienzo de tu próximo turno, esa "
            "carta pierde su habilidad y es Barajada. Una vez por turno, "
            "puedes Barajar una carta que no sea Oro o Robar hasta dos "
            "cartas o puedes pagar un Oro para Anular una carta.\n"
            "(Versión en lenguaje Enoquiano)"
        ),
        "cloudinary_id": "aydv_us_gabriel",
    },
    {
        "myl_id": "custom_aydv_us_semyazza",
        "edid": "AYDV-US02",
        "slug": "semyazza-aydv-us",
        "name": "Semyazza (Ultra Secreta)",
        "type_slug": "aliado",
        "race_slug": "eterno",
        "rarity_slug": "milenaria",
        "cost": "3",
        "damage": "2",
        "ability": (
            "(Texto en lenguaje Enoquiano - habilidad pendiente de "
            "traducción oficial)"
        ),
        "cloudinary_id": "aydv_us_semyazza",
    },
    {
        "myl_id": "custom_aydv_us_lucifer",
        "edid": "AYDV-US03",
        "slug": "lucifer-aydv-us",
        "name": "Lucifer (Ultra Secreta)",
        "type_slug": "aliado",
        "race_slug": "sombra",
        "rarity_slug": "milenaria",
        "cost": "4",
        "damage": "2",
        "ability": (
            "Exhumar. Una vez por turno, puedes Descartar una carta para "
            "prevenir que otra carta sea afectada por un efecto oponente o "
            "generar un Oro para Aliados. Una vez en tu turno, puedes jugar "
            "hasta un Aliado del Destierro oponente, Desterrar dos cartas "
            "del fondo de su Castillo y Robar una carta.\n"
            "(Versión en lenguaje Enoquiano)"
        ),
        "cloudinary_id": "aydv_us_lucifer",
    },
    # ═══ SHOWCASE (Base Set - distintas raridades) ════════════════════════════
    {
        "myl_id": "custom_aydv_002",
        "edid": "AYDV-002",
        "slug": "miguel-aydv",
        "name": "Miguel",
        "type_slug": "aliado",
        "race_slug": "caballero",
        "rarity_slug": "ultra-real",
        "cost": "5",
        "damage": "3",
        "ability": (
            "Furia. Imbloqueable. Cuando entra en juego, tu oponente "
            "Descarta dos cartas y tú Robas hasta dos cartas. Esta habilidad "
            "no puede ser cancelada. Una vez en tu turno, juega una carta de "
            "tu mano o de un Cementerio reduciendo su coste en un Oro, hasta "
            "un mínimo de 0."
        ),
        "cloudinary_id": "aydv_002_u",
    },
    {
        "myl_id": "custom_aydv_021",
        "edid": "AYDV-021",
        "slug": "belfegor-aydv",
        "name": "Belfegor",
        "type_slug": "aliado",
        "race_slug": "bestia",
        "rarity_slug": "mega-real",
        "cost": "3",
        "damage": "1",
        "ability": (
            "En tu Vigilia, puedes Botar tres cartas para jugarlo desde tu "
            "Cementerio pagando su coste. En tu Vigilia, una vez por turno, "
            "busca una carta en tu Castillo, ponla en tu Cementerio y un "
            "Aliado gana Furia por el turno. Tus demás Aliados ganan 1 de "
            "Fuerza."
        ),
        "cloudinary_id": "aydv_021_m",
    },
    {
        "myl_id": "custom_aydv_123",
        "edid": "AYDV-123",
        "slug": "paladin-del-tiempo-aydv",
        "name": "Paladín del Tiempo",
        "type_slug": "aliado",
        "race_slug": "caballero",
        "rarity_slug": "vasallo",
        "cost": "4",
        "damage": "3",
        "ability": (
            "Cuando entra en juego, no recibes daño de combate hasta tu "
            "próximo turno. Una vez por turno, tu oponente Descarta una "
            "carta de su mano. Si controlas Armas, tu oponente Descarta "
            "una carta adicional."
        ),
        "cloudinary_id": "aydv_123_v",
    },
]


class Command(BaseCommand):
    help = "Seed AYDV Blog Vigilantes (Promos, Secretas, Ultra Secretas, Showcase)"

    def handle(self, *args, **options):
        imp_format = Format.objects.get(code="imp")

        # ── Ensure races exist ──────────────────────────────────────
        new_races = [
            ("demonio", "Demonio"),
        ]
        for race_slug, race_name in new_races:
            Race.objects.get_or_create(
                slug=race_slug,
                defaults={"myl_id": f"custom_{race_slug}", "name": race_name},
            )

        # ── Load Cloudinary mapping ─────────────────────────────────
        cloudinary_urls = {}
        if os.path.exists(MAPPING_FILE):
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                cloudinary_urls = json.load(f)
            self.stdout.write(f"Loaded {len(cloudinary_urls)} Cloudinary URLs")
        else:
            self.stdout.write(self.style.WARNING(
                f"Mapping file not found: {MAPPING_FILE}"
            ))

        # ── Create/Update AYDV main edition ─────────────────────────
        edition, created = Edition.objects.update_or_create(
            myl_id="custom_aydv",
            defaults={
                "slug": "aydv",
                "title": "Ángeles y Demonios: Vigilantes",
                "image": "https://blog.myl.cl/wp-content/uploads/2025/05/AYDV-blog.jpg",
                "date_release": "2025-07-03",
                "format": imp_format,
                "active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} edition: {edition.title}"
        ))

        # ── Seed cards ──────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nSeeding {len(CARDS)} cards..."
        ))

        created_count = 0
        updated_count = 0

        for card_data in CARDS:
            card_type = CardType.objects.filter(
                slug=card_data["type_slug"]
            ).first()
            race = None
            if card_data["race_slug"]:
                race = Race.objects.filter(slug=card_data["race_slug"]).first()

            rarity = Rarity.objects.filter(
                slug=card_data["rarity_slug"]
            ).first()

            image_url = cloudinary_urls.get(card_data["cloudinary_id"], "")

            card, was_created = Card.objects.update_or_create(
                myl_id=card_data["myl_id"],
                defaults={
                    "edid": card_data["edid"],
                    "slug": card_data["slug"],
                    "name": card_data["name"],
                    "edition": edition,
                    "rarity": rarity,
                    "race": race,
                    "card_type": card_type,
                    "cost": card_data["cost"],
                    "damage": card_data["damage"],
                    "ability": card_data["ability"],
                    "flavour": "",
                    "custom_image_url": image_url,
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1
            status = "Created" if was_created else "Updated"
            self.stdout.write(
                f"  {status}: {card.name} ({card.edid})"
                + (f" → {image_url[:60]}..." if image_url else " [NO IMAGE]")
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created_count}, Updated: {updated_count} "
            f"({len(CARDS)} total)"
        ))
