"""Tests for carpeta app: collection upsert, wishlist toggle, share token."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cards.models import Edition, Card
from carpeta.models import CollectionEntry, WishlistEntry, BinderProfile, StoreOrder

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


class StoreOrderTests(CarpetaSetupMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.seller = cls.other
        cls.profile = BinderProfile.objects.create(user=cls.seller, is_store_public=True)
        cls.entry = CollectionEntry.objects.create(
            user=cls.seller,
            card=cls.card,
            quantity=5,
            price=1000,
            selling_quantity=4,
            condition="NM",
            language="ES",
            is_foil=False,
        )

    def _create_order(self):
        payload = {
            "buyer_name": "Comprador Test",
            "buyer_whatsapp": "+56911111111",
            "buyer_note": "Retiro en metro",
            "items": [{"entry_id": self.entry.id, "quantity": 2}],
        }
        create_url = reverse("public-store-orders", args=[str(self.profile.share_token)])
        return self.client.post(create_url, payload, format="json")

    def test_public_create_order_reserves_selling_stock(self):
        resp = self._create_order()
        self.assertEqual(resp.status_code, 201)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.quantity, 5)
        self.assertEqual(self.entry.selling_quantity, 2)
        self.assertEqual(resp.data["status"], StoreOrder.STATUS_PENDING)

    def test_owner_list_only_returns_own_orders(self):
        self._create_order()

        _auth(self.client, self.seller)
        mine = self.client.get(reverse("my-store-orders"))
        self.assertEqual(mine.status_code, 200)
        mine_results = mine.data.get("results", mine.data)
        self.assertEqual(len(mine_results), 1)

        _auth(self.client, self.user)
        other = self.client.get(reverse("my-store-orders"))
        self.assertEqual(other.status_code, 200)
        other_results = other.data.get("results", other.data)
        self.assertEqual(len(other_results), 0)

    def test_accept_order_discounts_real_stock(self):
        created = self._create_order()
        order_id = created.data["id"]

        _auth(self.client, self.seller)
        resp = self.client.post(reverse("accept-store-order", args=[order_id]), {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], StoreOrder.STATUS_ACCEPTED)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.quantity, 3)
        self.assertEqual(self.entry.selling_quantity, 2)
        self.assertIsNotNone(resp.data["responded_at"])

    def test_cancel_order_restores_reserved_selling_stock(self):
        created = self._create_order()
        order_id = created.data["id"]

        _auth(self.client, self.seller)
        resp = self.client.post(reverse("cancel-store-order", args=[order_id]), {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], StoreOrder.STATUS_CANCELLED)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.quantity, 5)
        self.assertEqual(self.entry.selling_quantity, 4)
        self.assertIsNotNone(resp.data["responded_at"])

    def test_assigned_summary_counts_only_pending_orders(self):
        created = self._create_order()
        order_id = created.data["id"]

        _auth(self.client, self.seller)
        summary = self.client.get(reverse("my-store-order-assignments"))
        self.assertEqual(summary.status_code, 200)
        assigned_map = summary.data["assigned_by_entry"]
        assigned = assigned_map.get(self.entry.id, assigned_map.get(str(self.entry.id)))
        self.assertEqual(assigned, 2)

        self.client.post(reverse("accept-store-order", args=[order_id]), {}, format="json")
        summary_after = self.client.get(reverse("my-store-order-assignments"))
        self.assertEqual(summary_after.status_code, 200)
        key_set = set(summary_after.data["assigned_by_entry"].keys())
        self.assertNotIn(self.entry.id, key_set)
        self.assertNotIn(str(self.entry.id), key_set)

    def test_non_owner_cannot_manage_order(self):
        created = self._create_order()
        order_id = created.data["id"]

        _auth(self.client, self.user)
        resp = self.client.post(reverse("accept-store-order", args=[order_id]), {}, format="json")
        self.assertEqual(resp.status_code, 404)
