"""Tests for decks app: visibility, likes, comments."""
from io import StringIO
from datetime import date

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cards.models import Card, Edition, Format
from decks.models import Deck, DeckLike, DeckComment, DeckEntry

User = get_user_model()


def _auth(client, user):
    """Authenticate APIClient using a JWT for the given user."""
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class DeckVisibilityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice", password="x")
        cls.bob = User.objects.create_user(username="bob", password="x")
        cls.public_deck = Deck.objects.create(
            owner=cls.alice, name="Public", is_public=True,
        )
        cls.private_deck = Deck.objects.create(
            owner=cls.alice, name="Private", is_public=False,
        )

    def test_public_list_excludes_private_decks(self):
        url = reverse("public-deck-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", resp.data)
        names = [d["name"] for d in results]
        self.assertIn("Public", names)
        self.assertNotIn("Private", names)

    def test_private_deck_not_visible_to_others(self):
        _auth(self.client, self.bob)
        url = reverse("public-deck-detail", args=[self.private_deck.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_owner_can_access_own_private_deck_via_my_endpoint(self):
        _auth(self.client, self.alice)
        url = reverse("deck-detail", args=[self.private_deck.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "Private")


class DeckLikeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice2", password="x")
        cls.bob = User.objects.create_user(username="bob2", password="x")
        cls.deck = Deck.objects.create(owner=cls.alice, name="Deck", is_public=True)

    def test_anonymous_cannot_like(self):
        url = reverse("deck-like", args=[self.deck.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 401)

    def test_toggle_like_on_off(self):
        _auth(self.client, self.bob)
        url = reverse("deck-like", args=[self.deck.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["liked"])
        self.assertEqual(resp.data["like_count"], 1)
        self.assertEqual(DeckLike.objects.filter(deck=self.deck).count(), 1)
        resp = self.client.post(url)
        self.assertFalse(resp.data["liked"])
        self.assertEqual(resp.data["like_count"], 0)
        self.assertEqual(DeckLike.objects.filter(deck=self.deck).count(), 0)


class DeckCommentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice3", password="x")
        cls.bob = User.objects.create_user(username="bob3", password="x")
        cls.deck = Deck.objects.create(owner=cls.alice, name="Deck", is_public=True)

    def test_list_comments_is_public(self):
        DeckComment.objects.create(user=self.alice, deck=self.deck, text="hola")
        url = reverse("deck-comments", args=[self.deck.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["text"], "hola")

    def test_anonymous_cannot_post_comment(self):
        url = reverse("deck-comments", args=[self.deck.id])
        resp = self.client.post(url, {"text": "spam"}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_user_can_post_comment(self):
        _auth(self.client, self.bob)
        url = reverse("deck-comments", args=[self.deck.id])
        resp = self.client.post(url, {"text": "buen mazo!"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(DeckComment.objects.count(), 1)

    def test_empty_comment_rejected(self):
        _auth(self.client, self.bob)
        url = reverse("deck-comments", args=[self.deck.id])
        resp = self.client.post(url, {"text": "   "}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_overlong_comment_rejected(self):
        _auth(self.client, self.bob)
        url = reverse("deck-comments", args=[self.deck.id])
        resp = self.client.post(url, {"text": "x" * 1001}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_user_can_delete_own_comment(self):
        c = DeckComment.objects.create(user=self.bob, deck=self.deck, text="hi")
        _auth(self.client, self.bob)
        url = reverse("delete-comment", args=[c.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(DeckComment.objects.count(), 0)

    def test_owner_can_delete_any_comment_on_own_deck(self):
        c = DeckComment.objects.create(user=self.bob, deck=self.deck, text="hi")
        _auth(self.client, self.alice)
        url = reverse("delete-comment", args=[c.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)

    def test_other_user_cannot_delete_comment(self):
        c = DeckComment.objects.create(user=self.alice, deck=self.deck, text="hi")
        _auth(self.client, self.bob)
        url = reverse("delete-comment", args=[c.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 403)


class FixDeckEntriesByNameCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="owner_fix", password="x")

        cls.fmt_imp = Format.objects.create(code="imp", name="Imperio")
        cls.fmt_impr = Format.objects.create(code="imp_r", name="Imperio R")

        cls.ed_imp = Edition.objects.create(
            myl_id="ed_imp",
            slug="ed-imp",
            title="Ed IMP",
            format=cls.fmt_imp,
            active=True,
            date_release=date(2026, 1, 1),
        )
        cls.ed_impr = Edition.objects.create(
            myl_id="ed_impr",
            slug="ed-impr",
            title="Ed IMPR",
            format=cls.fmt_impr,
            active=True,
            date_release=date(2026, 2, 1),
        )

        cls.card_imp_shadow = Card.objects.create(
            myl_id="c_imp_shadow",
            edid="1",
            slug="shadow-ban-imp",
            name="Shadow Ban",
            edition=cls.ed_imp,
        )
        cls.card_impr_shadow = Card.objects.create(
            myl_id="c_impr_shadow",
            edid="2",
            slug="shadow-ban-impr",
            name="Shadow Ban",
            edition=cls.ed_impr,
        )
        cls.card_impr_unmatched = Card.objects.create(
            myl_id="c_impr_unmatched",
            edid="3",
            slug="sin-equivalente",
            name="Nombre Sin Equivalente",
            edition=cls.ed_impr,
        )

    def test_replaces_and_merges_same_name_into_deck_format(self):
        deck = Deck.objects.create(owner=self.user, name="Deck Merge", format="imp")
        DeckEntry.objects.create(deck=deck, card=self.card_imp_shadow, quantity=1, is_sideboard=False)
        DeckEntry.objects.create(deck=deck, card=self.card_impr_shadow, quantity=2, is_sideboard=False)

        call_command("fix_deck_entries_by_name")

        entries = list(DeckEntry.objects.filter(deck=deck).order_by("id"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].card_id, self.card_imp_shadow.id)
        self.assertEqual(entries[0].quantity, 3)

    def test_removes_unmatched_off_format_entry_by_default(self):
        deck = Deck.objects.create(owner=self.user, name="Deck Remove", format="imp")
        DeckEntry.objects.create(deck=deck, card=self.card_impr_unmatched, quantity=1, is_sideboard=False)

        call_command("fix_deck_entries_by_name")

        self.assertEqual(DeckEntry.objects.filter(deck=deck).count(), 0)

    def test_dry_run_does_not_modify_entries(self):
        deck = Deck.objects.create(owner=self.user, name="Deck Dry", format="imp")
        DeckEntry.objects.create(deck=deck, card=self.card_impr_shadow, quantity=2, is_sideboard=False)

        out = StringIO()
        call_command("fix_deck_entries_by_name", "--dry-run", stdout=out)

        entry = DeckEntry.objects.get(deck=deck)
        self.assertEqual(entry.card_id, self.card_impr_shadow.id)
        self.assertIn("(dry-run)", out.getvalue())

    def test_keep_unmatched_preserves_entry(self):
        deck = Deck.objects.create(owner=self.user, name="Deck Keep", format="imp")
        DeckEntry.objects.create(deck=deck, card=self.card_impr_unmatched, quantity=1, is_sideboard=False)

        call_command("fix_deck_entries_by_name", "--keep-unmatched")

        entry = DeckEntry.objects.get(deck=deck)
        self.assertEqual(entry.card_id, self.card_impr_unmatched.id)
