"""Datos inválidos en la carpeta MyL responden 400/404, nunca 500 (QA 2026-09-21, A1 y B1)."""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cards.models import Card, Edition
from carpeta.models import CollectionEntry, WishlistEntry

User = get_user_model()


def _auth(client, user):
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class CarpetaInvalidInputTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="carpeta-gap", password="x")
        cls.edition = Edition.objects.create(myl_id="ed-cg", slug="ed-cg", title="Edicion CG")
        cls.card = Card.objects.create(myl_id="cg1", edid="001", slug="cg1", name="Carta CG", edition=cls.edition)

    def setUp(self):
        _auth(self.client, self.user)

    def test_upsert_invalid_payloads(self):
        url = reverse("collection-upsert")
        cases = [
            ({"card": "xyz", "quantity": 1}, 400),
            ({"card": 99999999, "quantity": 1}, 404),
            ({"card": self.card.id, "quantity": "abc"}, 400),
            ({"card": self.card.id, "quantity": -5}, 400),
            ({"card": self.card.id, "price": "abc"}, 400),
            ({"card": self.card.id, "condition": "XX"}, 400),
        ]
        for payload, expected in cases:
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, expected, payload)
        self.assertFalse(CollectionEntry.objects.exists())

    def test_upsert_invalid_field_does_not_modify_existing_entry(self):
        CollectionEntry.objects.create(user=self.user, card=self.card, quantity=2)
        resp = self.client.post(reverse("collection-upsert"), {"card": self.card.id, "quantity": "abc"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(CollectionEntry.objects.get(user=self.user, card=self.card).quantity, 2)

    def test_upsert_empty_numeric_fields_use_defaults(self):
        resp = self.client.post(
            reverse("collection-upsert"),
            {"card": self.card.id, "quantity": None, "selling_quantity": None},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        entry = CollectionEntry.objects.get(user=self.user, card=self.card)
        self.assertEqual((entry.quantity, entry.selling_quantity), (1, 0))

    def test_batch_upsert_is_all_or_nothing(self):
        resp = self.client.post(
            reverse("collection-batch-upsert"),
            [{"card": self.card.id, "quantity": 2}, {"card": "xyz"}],
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(CollectionEntry.objects.exists())

    def test_batch_upsert_rejects_non_objects(self):
        resp = self.client.post(reverse("collection-batch-upsert"), [1, 2], format="json")
        self.assertEqual(resp.status_code, 400)

    def test_bulk_import_non_text(self):
        resp = self.client.post(reverse("collection-bulk-import"), {"text": 12345}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_wishlist_toggle_invalid_payloads(self):
        url = reverse("wishlist-toggle")
        cases = [
            ({"card": "xyz"}, 400),
            ({"card": 99999999}, 404),
            ({"card": self.card.id, "desired_quantity": "abc"}, 400),
        ]
        for payload, expected in cases:
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, expected, payload)
        self.assertFalse(WishlistEntry.objects.exists())

    def test_wishlist_update_invalid_quantity(self):
        WishlistEntry.objects.create(user=self.user, card=self.card, desired_quantity=1)
        url = reverse("wishlist-update", args=[self.card.id])
        resp = self.client.patch(url, {"desired_quantity": "abc"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_wishlist_desired_quantity_is_capped(self):
        resp = self.client.post(
            reverse("wishlist-toggle"), {"card": self.card.id, "desired_quantity": 99999999}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WishlistEntry.objects.get(user=self.user).desired_quantity, 99)
        url = reverse("wishlist-update", args=[self.card.id])
        resp = self.client.patch(url, {"desired_quantity": 500}, format="json")
        self.assertEqual(resp.data["desired_quantity"], 99)
        resp = self.client.patch(url, {"desired_quantity": -3}, format="json")
        self.assertEqual(resp.data["desired_quantity"], 1)


class CarpetaOutOfRangeTests(APITestCase):
    """Enteros enormes responden 400, nunca 500 por OverflowError (QA 2026-09-26, A1)."""

    HUGE = 99999999999999999999

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="carpeta-range", password="x")
        cls.edition = Edition.objects.create(myl_id="ed-cr", slug="ed-cr", title="Edicion CR")
        cls.card = Card.objects.create(myl_id="cr1", edid="001", slug="cr1", name="Carta Rango", edition=cls.edition)

    def setUp(self):
        _auth(self.client, self.user)

    def test_upsert_out_of_range_values(self):
        url = reverse("collection-upsert")
        cases = [
            {"card": self.HUGE, "quantity": 1},
            {"card": self.card.id, "quantity": self.HUGE},
            {"card": self.card.id, "quantity": 10000},
            {"card": self.card.id, "quantity": 1, "price": self.HUGE},
            {"card": self.card.id, "quantity": 1, "selling_quantity": self.HUGE},
        ]
        for payload in cases:
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400, payload)
        self.assertFalse(CollectionEntry.objects.exists())

    def test_upsert_accepts_values_at_the_limit(self):
        resp = self.client.post(
            reverse("collection-upsert"),
            {"card": self.card.id, "quantity": 9999, "price": 99_999_999},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_bulk_import_out_of_range_quantity_is_not_found(self):
        resp = self.client.post(
            reverse("collection-bulk-import"),
            {"text": f"{self.HUGE} Carta Rango\n99999 Carta Rango"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["not_found"], 2)
        self.assertFalse(CollectionEntry.objects.exists())

    def test_binder_avatar_rejects_foreign_urls(self):
        url = reverse("binder-avatar")
        for bad in ("https://evil.test/x.png", "javascript:alert(1)", "http://res.cloudinary.com/x.png"):
            resp = self.client.post(url, {"avatar_url": bad}, format="json")
            self.assertEqual(resp.status_code, 400, bad)
