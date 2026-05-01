"""Tests for carpeta app: collection upsert, wishlist toggle, share token."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cards.models import Edition, Card
from carpeta.models import CollectionEntry, WishlistEntry, BinderProfile

User = get_user_model()


def _auth(client, user):
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class CarpetaSetupMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="alice", password="x")
        cls.other = User.objects.create_user(username="bob", password="x")
        cls.edition = Edition.objects.create(myl_id="ed1", slug="ed1", title="Edición 1")
        cls.card = Card.objects.create(myl_id="c1", edid="001", slug="c1", name="Carta 1", edition=cls.edition)
        cls.card2 = Card.objects.create(myl_id="c2", edid="002", slug="c2", name="Carta 2", edition=cls.edition)


class CollectionTests(CarpetaSetupMixin, APITestCase):
    def test_anonymous_cannot_upsert(self):
        url = reverse("collection-upsert")
        resp = self.client.post(url, {"card": self.card.id, "quantity": 2}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_upsert_creates_entry(self):
        _auth(self.client, self.user)
        url = reverse("collection-upsert")
        resp = self.client.post(url, {"card": self.card.id, "quantity": 3, "condition": "NM"}, format="json")
        self.assertEqual(resp.status_code, 200)
        entry = CollectionEntry.objects.get(user=self.user, card=self.card)
        self.assertEqual(entry.quantity, 3)
        self.assertEqual(entry.condition, "NM")

    def test_upsert_updates_existing_entry(self):
        CollectionEntry.objects.create(user=self.user, card=self.card, quantity=1)
        _auth(self.client, self.user)
        url = reverse("collection-upsert")
        resp = self.client.post(url, {"card": self.card.id, "quantity": 5, "is_foil": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        entry = CollectionEntry.objects.get(user=self.user, card=self.card)
        self.assertEqual(entry.quantity, 5)
        self.assertTrue(entry.is_foil)

    def test_upsert_caps_selling_qty_to_total(self):
        _auth(self.client, self.user)
        url = reverse("collection-upsert")
        resp = self.client.post(url, {"card": self.card.id, "quantity": 2, "selling_quantity": 99}, format="json")
        self.assertEqual(resp.status_code, 200)
        entry = CollectionEntry.objects.get(user=self.user, card=self.card)
        self.assertLessEqual(entry.selling_quantity, 2)

    def test_upsert_requires_card(self):
        _auth(self.client, self.user)
        url = reverse("collection-upsert")
        resp = self.client.post(url, {"quantity": 1}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_delete_own_entry(self):
        CollectionEntry.objects.create(user=self.user, card=self.card, quantity=1)
        _auth(self.client, self.user)
        url = reverse("collection-delete", args=[self.card.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(CollectionEntry.objects.filter(user=self.user, card=self.card).exists())

    def test_delete_others_entry_returns_404(self):
        CollectionEntry.objects.create(user=self.other, card=self.card, quantity=1)
        _auth(self.client, self.user)
        url = reverse("collection-delete", args=[self.card.id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 404)
        # Other user's entry remains
        self.assertTrue(CollectionEntry.objects.filter(user=self.other, card=self.card).exists())

    def test_collection_list_only_returns_own_entries(self):
        CollectionEntry.objects.create(user=self.user, card=self.card, quantity=1)
        CollectionEntry.objects.create(user=self.other, card=self.card2, quantity=2)
        _auth(self.client, self.user)
        url = reverse("collection-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)


class WishlistTests(CarpetaSetupMixin, APITestCase):
    def test_toggle_creates_then_removes(self):
        _auth(self.client, self.user)
        url = reverse("wishlist-toggle")
        # First call adds
        resp = self.client.post(url, {"card": self.card.id, "desired_quantity": 2}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["wishlisted"])
        self.assertEqual(WishlistEntry.objects.filter(user=self.user).count(), 1)
        # Second call removes
        resp = self.client.post(url, {"card": self.card.id}, format="json")
        self.assertFalse(resp.data["wishlisted"])
        self.assertEqual(WishlistEntry.objects.filter(user=self.user).count(), 0)

    def test_anonymous_cannot_toggle(self):
        url = reverse("wishlist-toggle")
        resp = self.client.post(url, {"card": self.card.id}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_update_desired_qty(self):
        WishlistEntry.objects.create(user=self.user, card=self.card, desired_quantity=1)
        _auth(self.client, self.user)
        url = reverse("wishlist-update", args=[self.card.id])
        resp = self.client.patch(url, {"desired_quantity": 4}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WishlistEntry.objects.get(user=self.user, card=self.card).desired_quantity, 4)


class ShareTokenTests(CarpetaSetupMixin, APITestCase):
    def test_get_share_token_creates_profile(self):
        _auth(self.client, self.user)
        url = reverse("share-token")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("share_token", resp.data)
        self.assertTrue(BinderProfile.objects.filter(user=self.user).exists())

    def test_regenerate_changes_token(self):
        _auth(self.client, self.user)
        # First trigger creation
        first = self.client.get(reverse("share-token")).data["share_token"]
        # Regenerate
        resp = self.client.post(reverse("share-token-regen"), {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(resp.data["share_token"], first)

    def test_anonymous_cannot_access_share_token(self):
        resp = self.client.get(reverse("share-token"))
        self.assertEqual(resp.status_code, 401)
