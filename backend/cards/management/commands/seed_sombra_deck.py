"""
Comando para crear un mazo Sombra Exhumar/Destierro con sinergia.
Uso: python manage.py seed_sombra_deck [--user USERNAME]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cards.models import Card
from decks.models import Deck, DeckEntry


# ─── MAIN DECK (50 cartas) ────────────────────────────────────
# Estrategia: Exhumar + Destierro. Recurrir aliados del cementerio,
# desterrar cartas clave del oponente, generar ventaja de cartas.
#
# Sinergia central:
# - Recta Provincia / El Mandinga / La Fiura como motores de búsqueda y draw
# - Cthulhu / Reina Bruja / Calchona como remoción con Exhumar
# - Mung como finisher (crece con cada aliado Exhumar en mesa)
# - Oros de draw (Drácula, Hidromiel) y control (Compendium, Grimorio)
# - Directorium se juega desde cementerio = nunca muerto
# - Talismanes de anulación para proteger el plan

MAIN_DECK = [
    # ── ALIADOS (16) ──
    # Recta Provincia: Exhumar, draw 2 al entrar, combo con flood de aliados
    ("recta provincia", 3),
    # Cthulhu: Exhumar, convierte hasta 2 cartas coste ≤3 (remoción + recursión)
    ("cthulhu", 3),
    # Reina Bruja: Exhumar, destierra coste ≤3 + roba carta (2-for-1)
    ("reina bruja", 2),
    # Mung: Fury + Exhumar, +2 Fuerza por cada aliado Exhumar/vanilla (finisher)
    ("mung", 2),
    # El Mandinga: Exhumar, busca en ambos castillos (disruptivo)
    ("el mandinga", 2),
    # La Fiura: Exhumar, tutora cualquier carta desde castillo
    ("la fiura", 2),
    # Seth El Destructor: Exhumar, roba 2 O el oponente bota 3 (flexible)
    ("seth el destructor", 1),
    # Calchona: Exhumar, destruye cartas con costes que sumen ≤2
    ("calchona", 1),
    # James Moriarty: Exhumar, roba carta, bonus con 8+ destierro oponente
    ("james moriarty", 1),

    # ── TALISMANES (5) ──
    # Cienpies SP: Anula carta coste ≤3 (protección barata)
    ("cienpies sp", 2),
    # Dragon Dorado: Anula cualquier cosa + recicla cartas al castillo
    ("dragon dorado", 2),
    # Sheut: Anula/cancela habilidad, barato si tienes menos oros
    ("sheut", 1),

    # ── ARMAS (2) ──
    # Pistola de Dos Cañones: +2 Fuerza, baraja carta oponente al hacer daño
    ("pistola de dos caones", 2),

    # ── OROS (27) ──
    # Drácula: Roba 2, se convierte en oro sin hab para prevenir daño
    ("dracula", 3),
    # Hidromiel: Baraja hasta 3 del cementerio + Roba 2 (gas + reciclaje)
    ("hidromiel", 3),
    # Animita: Ambos botan 3 del castillo + robas 1 (alimenta Exhumar)
    ("animita", 3),
    # Compendium Maleficarum: Nombra carta, oponente no puede jugarla (lock)
    ("compendium maleficarum", 2),
    # Grimorio: Busca en castillo oponente (disrupción + info)
    ("grimorio", 2),
    # Directorium Inquisitorum: Se juega desde cementerio! + busca aliado
    ("directorium inquisitorum", 2),
    # Huitzilin: Desde reserva, baraja para anular. Recursivo
    ("huitzilin", 2),
    # Flor de Lis: Busca un oro del castillo (consistencia)
    ("flor de lis", 2),
    # Hervidero de Sangre: Intercambia control con oro oponente (tempo)
    ("hervidero de sangre", 2),
    # Dulce Canasta: Busca oro del castillo/cementerio + oro extra para aliados
    ("dulce canasta", 2),
    # Espejo Mágico: Ve mano oponente + roba, cancela habilidad
    ("espejo magico", 2),
    # Camino del Inca: Desde reserva, cosas cuestan -1 (aceleración)
    ("camino del inca", 1),
]

# ─── SIDE DECK (15 cartas) ────────────────────────────────────
# Opciones situacionales según matchup

SIDE_DECK = [
    # Primer Shoggoth: Sacrifica aliado para desterrar cartas (vs decks lentos)
    ("primer shoggoth", 2),
    # Lenore: Exhumar, destierra coste ≤2 + roba (vs aggro con aliados baratos)
    ("lenore", 2),
    # Red de Plata: Anula/cancela habilidad, si coste ≤2 lo destierra
    ("red de plata", 2),
    # Jack: Si oponente tiene 3+ en destierro, copia una (vs matchups de valor)
    ("jack", 1),
    # Invunche: Coste 0! Recursivo desde cementerio (vs decks de attrition)
    ("invunche", 1),
    # En las Montañas de la Locura: Protege aliados + destierra al ser afectados
    ("en las montaas de la locura", 2),
    # Lucy: Si oponente tiene 8+ en destierro, copia carta desterrada (vs control)
    ("lucy", 2),
    # Onryo: Exhumar, ambos botan 2 cada vigilia, mill + alimenta Exhumar
    ("onryo", 2),
    # Escorpio: Imbloqueable, destierra hasta 3 aliados de línea oponente (vs midrange)
    ("escorpio", 1),
]


class Command(BaseCommand):
    help = "Crea un mazo Sombra Exhumar/Destierro con main + sidedeck"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", type=str, default="iterva",
            help="Username del dueño del mazo (default: iterva)",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["user"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Usuario '{username}' no existe."))
            return

        # Crear el deck
        deck = Deck.objects.create(
            owner=user,
            name="Sombra Exhumar Control",
            description=(
                "Mazo Sombra centrado en Exhumar y Destierro. "
                "Recurre aliados desde el cementerio, destierra cartas clave "
                "del oponente y genera ventaja con Recta Provincia + motores de draw. "
                "Mung es el finisher que crece con cada aliado Exhumar en juego."
            ),
            race="sombra",
            is_public=True,
        )
        self.stdout.write(f"Deck creado: {deck.name} (id={deck.id})")

        errors = []
        total_main = 0
        total_side = 0

        # Agregar Main Deck
        for card_name, qty in MAIN_DECK:
            card = self._find_card(card_name)
            if card is None:
                errors.append(f"  ✗ No encontré: '{card_name}'")
                continue
            DeckEntry.objects.create(deck=deck, card=card, quantity=qty, is_sideboard=False)
            total_main += qty
            self.stdout.write(f"  Main: {qty}x {card.name} (id={card.id})")

        # Agregar Side Deck
        for card_name, qty in SIDE_DECK:
            card = self._find_card(card_name)
            if card is None:
                errors.append(f"  ✗ No encontré: '{card_name}'")
                continue
            DeckEntry.objects.create(deck=deck, card=card, quantity=qty, is_sideboard=True)
            total_side += qty
            self.stdout.write(f"  Side: {qty}x {card.name} (id={card.id})")

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Mazo listo: {total_main} main + {total_side} side"
        ))
        if errors:
            self.stdout.write(self.style.WARNING("\nCartas no encontradas:"))
            for e in errors:
                self.stdout.write(e)

    def _find_card(self, name):
        """Busca carta por slug exacto, luego por nombre parcial. Prefiere ediciones activas."""
        # Intentar por slug exacto
        qs = Card.objects.filter(slug=name).select_related("edition")
        if qs.exists():
            # Preferir edición activa
            active = qs.filter(edition__active=True).first()
            return active if active else qs.first()

        # Intentar por nombre case-insensitive
        qs = Card.objects.filter(name__iexact=name).select_related("edition")
        if qs.exists():
            active = qs.filter(edition__active=True).first()
            return active if active else qs.first()

        # Intentar por nombre parcial
        qs = Card.objects.filter(name__icontains=name).select_related("edition")
        if qs.exists():
            active = qs.filter(edition__active=True).first()
            return active if active else qs.first()

        return None
