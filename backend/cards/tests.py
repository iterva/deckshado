"""Tests for cards app: banlist endpoint, card list filtering, search."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from cards.models import BanlistEntry, Card, CardType, Edition, Format, Race
from cards.serializers import CardListSerializer


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

    def test_search_with_regex_special_chars_does_not_500(self):
        url = reverse("card-list")
        for q in ["(", "[", "?", "\\", "a**", "Dragón ("]:
            resp = self.client.get(url, {"search": q})
            self.assertEqual(resp.status_code, 200, q)
            resp = self.client.get(url, {"ability_search": q})
            self.assertEqual(resp.status_code, 200, q)

    def test_search_dot_is_literal(self):
        url = reverse("card-list")
        resp = self.client.get(url, {"search": "."})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 0)


class CardImageCdnPriorityTests(TestCase):
    def test_imagekit_url_has_priority_over_cloudinary_and_legacy_url(self):
        edition = Edition.objects.create(myl_id="cdn-ed", slug="cdn-ed", title="CDN Edition")
        card = Card.objects.create(
            myl_id="custom-cdn-card",
            edid="001",
            slug="cdn-card",
            name="Carta CDN",
            edition=edition,
            imagekit_image_url="https://ik.imagekit.io/deckshadow/cards/cdn-card.png",
            cloudinary_image_url="https://res.cloudinary.com/daobfx9yb/image/upload/cdn-card.png",
            custom_image_url="https://example.test/legacy-card.png",
        )

        self.assertEqual(
            CardListSerializer(card).data["image_url"],
            "https://ik.imagekit.io/deckshadow/cards/cdn-card.png",
        )


class PublicCardsActiveEditionFilterTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fmt = Format.objects.create(code="imp", name="Imperio")
        cls.active_edition = Edition.objects.create(
            myl_id="aed",
            slug="active-ed",
            title="Active Edition",
            format=cls.fmt,
            active=True,
        )
        cls.inactive_edition = Edition.objects.create(
            myl_id="ied",
            slug="inactive-ed",
            title="Inactive Edition",
            format=cls.fmt,
            active=False,
        )
        cls.active_card = Card.objects.create(
            myl_id="ac1",
            edid="001",
            slug="active-card",
            name="Active Card",
            edition=cls.active_edition,
        )
        cls.inactive_card = Card.objects.create(
            myl_id="ic1",
            edid="001",
            slug="inactive-card",
            name="Inactive Card",
            edition=cls.inactive_edition,
        )

    def test_card_list_excludes_cards_from_inactive_editions(self):
        response = self.client.get(reverse("card-list"), {"fmt": "imp"})

        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", response.data)
        names = [item["name"] for item in results]
        self.assertIn("Active Card", names)
        self.assertNotIn("Inactive Card", names)

    def test_cards_by_format_excludes_cards_from_inactive_editions(self):
        response = self.client.get(reverse("cards-by-format", kwargs={"format_code": "imp"}))

        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.data]
        self.assertIn("Active Card", names)
        self.assertNotIn("Inactive Card", names)

    def test_card_detail_returns_404_for_inactive_edition_card(self):
        response = self.client.get(reverse("card-detail", kwargs={"pk": self.inactive_card.pk}))
        self.assertEqual(response.status_code, 404)

    def test_edition_list_excludes_inactive_editions(self):
        response = self.client.get(reverse("edition-list"), {"fmt": "imp"})

        self.assertEqual(response.status_code, 200)
        slugs = [item["slug"] for item in response.data]
        self.assertIn("active-ed", slugs)
        self.assertNotIn("inactive-ed", slugs)


@override_settings(CARDS_ADMIN_OWNER_USERNAME="iterva")
class CardsAdminToggleEditionsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="iterva",
            email="iterva@test.local",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(self.owner)

    def test_active_checked_syncs_selection_and_unselection(self):
        fmt = Format.objects.create(code="imp", name="Imperio")
        kept = Edition.objects.create(myl_id="e1", slug="e1", title="Ed 1", format=fmt, active=True)
        removed = Edition.objects.create(myl_id="e2", slug="e2", title="Ed 2", format=fmt, active=True)
        added = Edition.objects.create(myl_id="e3", slug="e3", title="Ed 3", format=fmt, active=False)

        url = reverse("cards-admin-toggle-editions")
        response = self.client.post(url, {"edition_ids": [kept.id, added.id], "active": "on"})

        self.assertEqual(response.status_code, 302)
        kept.refresh_from_db()
        removed.refresh_from_db()
        added.refresh_from_db()

        self.assertTrue(kept.active)
        self.assertFalse(removed.active)
        self.assertTrue(added.active)

    def test_active_unchecked_deactivates_only_selected(self):
        fmt = Format.objects.create(code="fx", name="Fenix")
        target = Edition.objects.create(myl_id="f1", slug="f1", title="Fx 1", format=fmt, active=True)
        untouched = Edition.objects.create(myl_id="f2", slug="f2", title="Fx 2", format=fmt, active=True)

        url = reverse("cards-admin-toggle-editions")
        response = self.client.post(url, {"edition_ids": [target.id]})

        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        untouched.refresh_from_db()

        self.assertFalse(target.active)
        self.assertTrue(untouched.active)
