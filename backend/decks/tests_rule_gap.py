"""Server-side validation of MyL deck hard limits (QA 2026-09-16, tarea 2.2).

El backend revalida al crear/editar via API: 50 cartas principales / 15 de
sideboard, copias maximas (3, o 1 para "Unica", sumando main + side y versiones
con el mismo nombre), banlist del formato/sub-formato y cantidad >= 1.
Un mazo incompleto (<50) sigue siendo valido (borradores).
La restriccion racial se mantiene solo en el frontend (`deck-builder.component.ts`).
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


class DeckServerSideRuleTests(APITestCase):
    """El backend rechaza mazos que el constructor no permitiria armar."""

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

    def _post(self, entries, **extra):
        _auth(self.client, self.user)
        payload = {"name": "Mazo", "format": "imp", "sub_format": "racial", "entries": entries, **extra}
        return self.client.post(reverse("my-deck-list"), payload, format="json")

    def test_rejects_more_than_3_copies_of_a_regular_card(self):
        resp = self._post([{"card": self.card.id, "quantity": 4, "is_sideboard": False}])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("entries", resp.data)
        self.assertFalse(Deck.objects.exists())

    def test_copies_are_counted_across_main_and_side(self):
        resp = self._post([
            {"card": self.card.id, "quantity": 2, "is_sideboard": False},
            {"card": self.card.id, "quantity": 2, "is_sideboard": True},
        ])
        self.assertEqual(resp.status_code, 400)

    def test_copies_are_counted_across_versions_with_same_name(self):
        variant = Card.objects.create(
            myl_id="gap-card-v2", edid="010", slug="gap-card-v2", name="Carta Gap (v2)", edition=self.edition,
        )
        resp = self._post([
            {"card": self.card.id, "quantity": 2, "is_sideboard": False},
            {"card": variant.id, "quantity": 2, "is_sideboard": False},
        ])
        self.assertEqual(resp.status_code, 400)

    def test_rejects_2_copies_of_a_unique_card(self):
        unique = Card.objects.create(
            myl_id="gap-unique", edid="003", slug="gap-unique", name="Carta Unica",
            ability="Única. Texto.", edition=self.edition,
        )
        resp = self._post([{"card": unique.id, "quantity": 2, "is_sideboard": False}])
        self.assertEqual(resp.status_code, 400)

    def test_rejects_more_than_50_cards_in_main_deck(self):
        cards = [
            Card.objects.create(myl_id=f"gap-m{i}", edid=f"1{i:02d}", slug=f"gap-m{i}", name=f"Relleno {i}", edition=self.edition)
            for i in range(17)
        ]
        resp = self._post([{"card": c.id, "quantity": 3, "is_sideboard": False} for c in cards])  # 51
        self.assertEqual(resp.status_code, 400)

    def test_rejects_more_than_15_cards_in_sideboard(self):
        cards = [
            Card.objects.create(myl_id=f"gap-s{i}", edid=f"2{i:02d}", slug=f"gap-s{i}", name=f"Side {i}", edition=self.edition)
            for i in range(6)
        ]
        entries = [{"card": c.id, "quantity": 3, "is_sideboard": True} for c in cards[:5]]
        entries.append({"card": cards[5].id, "quantity": 1, "is_sideboard": True})  # 16
        resp = self._post(entries)
        self.assertEqual(resp.status_code, 400)

    def test_rejects_a_banned_card(self):
        resp = self._post([{"card": self.banned_card.id, "quantity": 1, "is_sideboard": False}])
        self.assertEqual(resp.status_code, 400)

    def test_rejects_zero_quantity(self):
        resp = self._post([{"card": self.card.id, "quantity": 0, "is_sideboard": False}])
        self.assertEqual(resp.status_code, 400)

    def test_incomplete_valid_deck_is_still_accepted(self):
        resp = self._post([{"card": self.card.id, "quantity": 3, "is_sideboard": False}])
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_update_is_validated_and_keeps_previous_entries(self):
        resp = self._post([{"card": self.card.id, "quantity": 2, "is_sideboard": False}])
        deck_id = resp.data["id"]
        url = reverse("deck-detail", args=[deck_id])
        resp = self.client.put(url, {
            "name": "Mazo", "format": "imp", "sub_format": "racial",
            "entries": [{"card": self.card.id, "quantity": 60, "is_sideboard": False}],
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(DeckEntry.objects.get(deck_id=deck_id).quantity, 2)

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


class DeckEntryEndpointTests(APITestCase):
    """QA #2 A1: `POST my/<id>/entries/` valida tipo, rango, existencia y reglas."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="entrygap", password="x")
        cls.fmt = Format.objects.create(code="imp", name="Imperio")
        cls.edition = Edition.objects.create(
            myl_id="ed-entry", slug="ed-entry", title="Edicion Entry", format=cls.fmt, active=True,
        )
        cls.card = Card.objects.create(
            myl_id="entry-card", edid="001", slug="entry-card", name="Daga Ritual", edition=cls.edition,
        )

    def setUp(self):
        self.deck = Deck.objects.create(owner=self.user, name="Mazo", format="imp", sub_format="racial")
        _auth(self.client, self.user)
        self.url = reverse("deck-entries", args=[self.deck.id])

    def _assert_rejected(self, body):
        resp = self.client.post(self.url, body, format="json")
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertFalse(DeckEntry.objects.filter(deck=self.deck).exists())

    def test_negative_quantity(self):
        self._assert_rejected({"card_id": self.card.id, "quantity": -5})

    def test_non_numeric_quantity(self):
        self._assert_rejected({"card_id": self.card.id, "quantity": "abc"})

    def test_missing_card(self):
        self._assert_rejected({"card_id": 99999999, "quantity": 1})

    def test_non_numeric_card_id(self):
        self._assert_rejected({"card_id": "xyz", "quantity": 1})

    def test_too_many_copies(self):
        self._assert_rejected({"card_id": self.card.id, "quantity": 60})

    def test_valid_add_and_update(self):
        resp = self.client.post(self.url, {"card_id": self.card.id, "quantity": 2}, format="json")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(self.url, {"card_id": self.card.id, "quantity": 3}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(DeckEntry.objects.get(deck=self.deck).quantity, 3)

    def test_sideboard_counts_towards_copy_limit(self):
        self.client.post(self.url, {"card_id": self.card.id, "quantity": 3}, format="json")
        resp = self.client.post(
            self.url, {"card_id": self.card.id, "quantity": 1, "is_sideboard": True}, format="json",
        )
        self.assertEqual(resp.status_code, 400)


class DeckMetadataValidationTests(APITestCase):
    """QA #2 M1: formato, sub-formato y raza inventados se rechazan aunque no haya cartas."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="metagap", password="x")
        Format.objects.create(code="imp", name="Imperio")

    def _post(self, **fields):
        _auth(self.client, self.user)
        payload = {"name": "Mazo", "format": "imp", "sub_format": "racial", "race": "dragon", "entries": [], **fields}
        return self.client.post(reverse("my-deck-list"), payload, format="json")

    def test_valid_metadata(self):
        self.assertEqual(self._post().status_code, 201)

    def test_unknown_format(self):
        resp = self._post(format="zzz")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("format", resp.data)

    def test_unknown_sub_format(self):
        resp = self._post(sub_format="xxx")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("sub_format", resp.data)

    def test_invalid_race(self):
        resp = self._post(race="<script>")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("race", resp.data)


class DeckInvalidInputTests(APITestCase):
    """Portada, importación, snapshots y comentarios con datos inválidos (QA 2026-09-21, A2, A3 y M6)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="deck-input", password="x")
        cls.fmt = Format.objects.create(code="imp", name="Imperio")
        cls.edition = Edition.objects.create(
            myl_id="ed-in", slug="ed-in", title="Edicion In", format=cls.fmt, active=True,
        )
        cls.card = Card.objects.create(myl_id="in-card", edid="001", slug="in-card", name="Carta In", edition=cls.edition)
        cls.card2 = Card.objects.create(myl_id="in-card2", edid="002", slug="in-card2", name="Carta In 2", edition=cls.edition)

    def setUp(self):
        _auth(self.client, self.user)
        self.deck = Deck.objects.create(owner=self.user, name="Mazo", format="imp")
        DeckEntry.objects.create(deck=self.deck, card=self.card, quantity=2)

    def test_cover_with_non_numeric_card_id(self):
        resp = self.client.post(reverse("deck-cover", args=[self.deck.id]), {"card_id": "xyz"}, format="json")
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(
            reverse("deck-cover", args=[self.deck.id]), {"card_id": 99999999999999999999}, format="json",
        )
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(reverse("deck-cover", args=[self.deck.id]), {"card_id": self.card.id}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_import_garbage_creates_no_deck(self):
        before = Deck.objects.count()
        for body in (
            {"data": "no soy un mazo"},
            {"entries": []},
            {"entries": ["x"]},
            {"entries": [{"myl_id": "in-card", "quantity": "abc"}]},
            {"entries": [{"myl_id": "in-card"}], "sideboard": "x"},
            {"name": 123, "entries": [{"myl_id": "in-card"}]},
            {"entries": [{"myl_id": ["lista"]}]},
            {"entries": [{"myl_id": "no-existe"}]},
        ):
            resp = self.client.post(reverse("deck-import"), body, format="json")
            self.assertEqual(resp.status_code, 400, body)
        self.assertEqual(Deck.objects.count(), before)

    def test_import_valid_file_merges_duplicates(self):
        resp = self.client.post(reverse("deck-import"), {
            "name": "Importado",
            "entries": [{"myl_id": "in-card", "quantity": 1}, {"myl_id": "in-card", "quantity": 2}],
            "sideboard": [{"myl_id": "in-card2", "quantity": 1}],
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        deck = Deck.objects.get(id=resp.data["id"])
        self.assertEqual(deck.entries.get(card=self.card, is_sideboard=False).quantity, 3)
        self.assertEqual(deck.entries.filter(is_sideboard=True).count(), 1)

    def test_snapshot_label_is_trimmed_to_model_limit(self):
        resp = self.client.post(reverse("deck-snapshots", args=[self.deck.id]), {"label": "a" * 300}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp.data["label"]), 100)
        resp = self.client.post(reverse("deck-snapshots", args=[self.deck.id]), {"label": 5}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_restore_snapshot_skips_cards_deleted_from_catalog(self):
        from decks.models import DeckSnapshot

        snap = DeckSnapshot.objects.create(deck=self.deck, label="v1", snapshot_data={
            "name": "Mazo v1", "entries": [
                {"card_id": self.card.id, "quantity": 3, "is_sideboard": False},
                {"card_id": 99999999, "quantity": 1, "is_sideboard": False},
            ],
            "starting_gold": 99999999,
        })
        resp = self.client.post(reverse("restore-snapshot", args=[snap.id]))
        self.assertEqual(resp.status_code, 200)
        self.deck.refresh_from_db()
        self.assertEqual(self.deck.name, "Mazo v1")
        self.assertIsNone(self.deck.starting_gold_id)
        self.assertEqual(list(self.deck.entries.values_list("card_id", "quantity")), [(self.card.id, 3)])

    def test_comment_must_be_text(self):
        self.deck.is_public = True
        self.deck.save()
        resp = self.client.post(reverse("deck-comments", args=[self.deck.id]), {"text": ["x"]}, format="json")
        self.assertEqual(resp.status_code, 400)
