"""Tests for cards app: banlist endpoint, card list filtering, search."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from cards.models import Edition, Card, BanlistEntry, CardType, Race


class BanlistEndpointTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.edition = Edition.objects.create(myl_id="ed1", slug="ed1", title="Edición 1")
        cls.card_a = Card.objects.create(myl_id="a", edid="001", slug="a", name="Carta A", edition=cls.edition)
        cls.card_b = Card.objects.create(myl_id="b", edid="002", slug="b", name="Carta B", edition=cls.edition)
        BanlistEntry.objects.create(
            card_name="Carta A", card=cls.card_a,
            format_code="imp", sub_format="racial",
            status=BanlistEntry.BANNED, max_copies=0,
        )
        BanlistEntry.objects.create(
            card_name="Carta B", card=cls.card_b,
            format_code="imp", sub_format="vcr",
            status=BanlistEntry.LIMITED_1, max_copies=1,
        )
        BanlistEntry.objects.create(
            card_name="Carta A", card=cls.card_a,
            format_code="fx", sub_format="racial",
            status=BanlistEntry.LIMITED_2, max_copies=2,
        )

    def test_banlist_no_filters_returns_all(self):
        url = reverse("banlist")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 3)

    def test_banlist_filter_by_format(self):
        url = reverse("banlist")
        resp = self.client.get(url, {"fmt": "imp"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)
        for entry in resp.data:
            self.assertEqual(entry["format_code"], "imp")

    def test_banlist_filter_by_format_and_subformat(self):
        url = reverse("banlist")
        resp = self.client.get(url, {"fmt": "imp", "sub": "vcr"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        entry = resp.data[0]
        self.assertEqual(entry["card_name"], "Carta B")
        self.assertEqual(entry["sub_format"], "vcr")
        self.assertEqual(entry["max_copies"], 1)

    def test_banlist_unique_per_format_and_subformat(self):
        # The same card can appear with different status in different formats
        with self.assertRaises(Exception):
            BanlistEntry.objects.create(
                card_name="Carta A", card=self.card_a,
                format_code="imp", sub_format="racial",
                status=BanlistEntry.BANNED, max_copies=0,
            )

    def test_status_max_copies_consistency(self):
        banned = BanlistEntry.objects.get(card_name="Carta A", format_code="imp")
        self.assertEqual(banned.status, BanlistEntry.BANNED)
        self.assertEqual(banned.max_copies, 0)
        limited2 = BanlistEntry.objects.get(card_name="Carta A", format_code="fx")
        self.assertEqual(limited2.status, BanlistEntry.LIMITED_2)
        self.assertEqual(limited2.max_copies, 2)


class CardListSearchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        ed = Edition.objects.create(myl_id="ed", slug="ed", title="Ed")
        Card.objects.create(myl_id="x1", edid="001", slug="samurai", name="Samurai del Norte", edition=ed)
        Card.objects.create(myl_id="x2", edid="002", slug="dragon", name="Dragón", edition=ed)
        Card.objects.create(myl_id="x3", edid="003", slug="dragon-rojo", name="Dragón Rojo", edition=ed)

    def test_search_is_accent_insensitive(self):
        url = reverse("card-list")
        resp = self.client.get(url, {"search": "dragon"})
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", resp.data)
        names = [c["name"] for c in results]
        self.assertIn("Dragón", names)
        self.assertIn("Dragón Rojo", names)
        self.assertNotIn("Samurai del Norte", names)

    def test_search_case_insensitive(self):
        url = reverse("card-list")
        resp = self.client.get(url, {"search": "SAMURAI"})
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", resp.data)
        names = [c["name"] for c in results]
        self.assertIn("Samurai del Norte", names)
