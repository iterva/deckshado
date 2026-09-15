"""Regression tests documenting a known gap (see DECKBUILDER_CONTEXT.md, seccion 4):

El backend de mazos MyL NO revalida en el servidor los limites de 50 cartas
principales / 15 de sideboard, copias maximas (3, o 1 para "Unica"), banlist
ni restriccion racial al crear/editar un mazo via API. Toda esa logica vive
solo en el frontend (`deck-builder.component.ts`).

Estos tests documentan el comportamiento ACTUAL (inseguro) para que:
  1) quede constancia explicita del riesgo con un test que falla si alguien
     agrega validacion server-side (senal de que hay que actualizar el test
     y el documento de contexto), y
  2) sirvan de red de seguridad: si algun cambio futuro rompe la unica
     validacion que si existe (coherencia formato/edicion), se detecte aqui.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cards.models import BanlistEntry, Card, Edition, Format
from decks.models import Deck, DeckEntry

User = get_user_model()


def _auth(client, user):
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class DeckServerSideRuleGapTests(APITestCase):
    """Documenta que el backend acepta mazos que romperian las reglas de negocio
    si se enviaran directamente contra la API (sin pasar por la UI de Angular)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="rulegap", password="x")
        cls.fmt = Format.objects.create(code="imp", name="Imperio")
        cls.edition = Edition.objects.create(
            myl_id="ed-gap", slug="ed-gap", title="Edicion Gap", format=cls.fmt, active=True,
        )
        cls.card = Card.objects.create(
            myl_id="gap-card", edid="001", slug="gap-card", name="Carta Gap", edition=cls.edition,
        )
        cls.banned_card = Card.objects.create(
            myl_id="gap-banned", edid="002", slug="gap-banned", name="Carta Prohibida", edition=cls.edition,
        )
        BanlistEntry.objects.create(
            card_name="Carta Prohibida", card=cls.banned_card,
            format_code="imp", sub_format="racial",
            status=BanlistEntry.BANNED, max_copies=0,
        )

    def test_api_currently_accepts_more_than_3_copies_of_a_regular_card(self):
        """La UI limita a 3 copias (getMaxCopies) pero la API no revalida esto."""
        _auth(self.client, self.user)
        url = reverse("my-deck-list")
        payload = {
            "name": "Mazo con 10 copias",
            "format": "imp",
            "entries": [{"card": self.card.id, "quantity": 10, "is_sideboard": False}],
        }
        resp = self.client.post(url, payload, format="json")

        self.assertEqual(resp.status_code, 201, resp.data)
        entry = DeckEntry.objects.get(deck_id=resp.data["id"])
        self.assertEqual(entry.quantity, 10)

    def test_api_currently_accepts_more_than_50_cards_in_main_deck(self):
        """La UI bloquea en 50 cartas (addCard) pero el backend no lo revalida."""
        _auth(self.client, self.user)
        url = reverse("my-deck-list")
        payload = {
            "name": "Mazo con 90 cartas",
            "format": "imp",
            "entries": [{"card": self.card.id, "quantity": 90, "is_sideboard": False}],
        }
        resp = self.client.post(url, payload, format="json")

        self.assertEqual(resp.status_code, 201, resp.data)
        entry = DeckEntry.objects.get(deck_id=resp.data["id"])
        self.assertEqual(entry.quantity, 90)

    def test_api_currently_accepts_a_banned_card(self):
        """`BanlistEntry` existe y se expone via /api/cards/banlist/, pero el
        create/update del mazo no la consulta."""
        _auth(self.client, self.user)
        url = reverse("my-deck-list")
        payload = {
            "name": "Mazo con carta prohibida",
            "format": "imp",
            "sub_format": "racial",
            "entries": [{"card": self.banned_card.id, "quantity": 1, "is_sideboard": False}],
        }
        resp = self.client.post(url, payload, format="json")

        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(DeckEntry.objects.filter(deck_id=resp.data["id"], card=self.banned_card).exists())

    def test_format_edition_mismatch_is_still_rejected(self):
        """Esta SI es la unica validacion server-side que existe hoy
        (`DeckCreateSerializer._card_matches_deck_format`); confirma que sigue activa."""
        other_fmt = Format.objects.create(code="fx", name="Fenix")
        other_edition = Edition.objects.create(
            myl_id="ed-other", slug="ed-other", title="Otra Edicion", format=other_fmt, active=True,
        )
        other_card = Card.objects.create(
            myl_id="other-card", edid="001", slug="other-card", name="Carta de Otro Formato", edition=other_edition,
        )
        _auth(self.client, self.user)
        url = reverse("my-deck-list")
        payload = {
            "name": "Mazo formato incorrecto",
            "format": "imp",
            "entries": [{"card": other_card.id, "quantity": 1, "is_sideboard": False}],
        }
        resp = self.client.post(url, payload, format="json")

        self.assertEqual(resp.status_code, 400)
        self.assertIn("entries", resp.data)
