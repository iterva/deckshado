"""Tests para el validador de mazos Riftbound (`riftbound/validation.py`).

No existia cobertura previa para esta pieza central de reglas de negocio
(unico validador server-side de todo el proyecto, ver DECKBUILDER_CONTEXT.md).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    RiftboundBanlistEntry,
    RiftboundCard,
    RiftboundDeck,
    RiftboundDeckEntry,
    RiftboundFormat,
    RiftboundSet,
    ZONE_BATTLEFIELD,
    ZONE_CHAMPION,
    ZONE_MAIN,
    ZONE_RUNE,
    ZONE_SIDE,
)
from .validation import validate_riftbound_deck

User = get_user_model()


def make_card(number, name=None, description="", card_type="unit"):
    return RiftboundCard.objects.create(
        card_number=number,
        name=name or number,
        slug=number.lower(),
        card_type=card_type,
        rarity="common",
        description=description,
    )


class RiftboundValidationBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="rb_owner", password="x")
        cls.fmt = RiftboundFormat.objects.create(code="standard", name="Standard")
        cls.rb_set = RiftboundSet.objects.create(code="OGN", name="Origins")

    def make_deck(self, fmt=None):
        return RiftboundDeck.objects.create(owner=self.owner, name="Test Deck", format=fmt if fmt is not None else self.fmt)

    def fill_zone(self, deck, zone, count, prefix, start=1, card_type="unit", per_card_qty=1):
        """Crea `count` copias repartidas en cartas distintas con `per_card_qty` cada una."""
        created = 0
        idx = start
        while created < count:
            card = make_card(f"{prefix}-{idx:03d}", card_type=card_type)
            qty = min(per_card_qty, count - created)
            RiftboundDeckEntry.objects.create(deck=deck, card=card, quantity=qty, zone=zone)
            created += qty
            idx += 1
        return idx


class LegalDeckTests(RiftboundValidationBaseTestCase):
    def test_fully_legal_deck_is_valid_with_no_errors_or_warnings(self):
        deck = self.make_deck()
        self.fill_zone(deck, ZONE_MAIN, 40, "MN", per_card_qty=2)  # 20 cartas x2 = 40
        self.fill_zone(deck, ZONE_RUNE, 12, "RN", per_card_qty=1)
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")

        result = validate_riftbound_deck(deck)

        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["counts"][ZONE_MAIN], 40)
        self.assertEqual(result["counts"][ZONE_RUNE], 12)
        self.assertEqual(result["counts"][ZONE_CHAMPION], 1)
        self.assertEqual(result["counts"][ZONE_BATTLEFIELD], 3)

    def test_legal_deck_with_exact_tournament_sideboard_has_no_warning(self):
        deck = self.make_deck()
        self.fill_zone(deck, ZONE_MAIN, 40, "MN", per_card_qty=2)
        self.fill_zone(deck, ZONE_RUNE, 12, "RN")
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")
        self.fill_zone(deck, ZONE_SIDE, 10, "SB")

        result = validate_riftbound_deck(deck)

        self.assertTrue(result["valid"])
        self.assertEqual(result["warnings"], [])


class ZoneSizeTests(RiftboundValidationBaseTestCase):
    def test_empty_deck_reports_all_exact_zone_errors(self):
        deck = self.make_deck()
        result = validate_riftbound_deck(deck)

        self.assertFalse(result["valid"])
        joined = " ".join(result["errors"])
        self.assertIn("main", joined)
        self.assertIn("rune", joined)
        self.assertIn("champion", joined)
        self.assertIn("bg", joined)

    def test_main_deck_with_39_cards_is_invalid(self):
        deck = self.make_deck()
        self.fill_zone(deck, ZONE_MAIN, 39, "MN")
        self.fill_zone(deck, ZONE_RUNE, 12, "RN")
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")

        result = validate_riftbound_deck(deck)

        self.assertFalse(result["valid"])
        self.assertTrue(any("main" in e and "39" in e for e in result["errors"]))

    def test_main_deck_with_41_cards_is_invalid(self):
        deck = self.make_deck()
        self.fill_zone(deck, ZONE_MAIN, 41, "MN")
        self.fill_zone(deck, ZONE_RUNE, 12, "RN")
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")

        result = validate_riftbound_deck(deck)

        self.assertFalse(result["valid"])
        self.assertTrue(any("main" in e and "41" in e for e in result["errors"]))

    def test_sideboard_with_5_cards_is_only_a_warning_not_an_error(self):
        deck = self.make_deck()
        self.fill_zone(deck, ZONE_MAIN, 40, "MN", per_card_qty=2)
        self.fill_zone(deck, ZONE_RUNE, 12, "RN")
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")
        self.fill_zone(deck, ZONE_SIDE, 5, "SB")

        result = validate_riftbound_deck(deck)

        self.assertTrue(result["valid"])  # sideboard no bloquea
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("sideboard", result["warnings"][0].lower())

    def test_battlefields_with_duplicate_card_is_invalid(self):
        deck = self.make_deck()
        self.fill_zone(deck, ZONE_MAIN, 40, "MN", per_card_qty=2)
        self.fill_zone(deck, ZONE_RUNE, 12, "RN")
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        bg_card = make_card("BG-001")
        RiftboundDeckEntry.objects.create(deck=deck, card=bg_card, quantity=2, zone=ZONE_BATTLEFIELD)
        other_bg = make_card("BG-002")
        RiftboundDeckEntry.objects.create(deck=deck, card=other_bg, quantity=1, zone=ZONE_BATTLEFIELD)

        result = validate_riftbound_deck(deck)

        self.assertFalse(result["valid"])
        self.assertTrue(any("distintas" in e for e in result["errors"]))


class CopyLimitTests(RiftboundValidationBaseTestCase):
    def _legal_skeleton(self, deck):
        """Rellena todas las zonas obligatorias con cartas neutras para aislar el chequeo de copias."""
        self.fill_zone(deck, ZONE_RUNE, 12, "RN")
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")

    def test_four_copies_of_a_normal_card_is_invalid(self):
        deck = self.make_deck()
        self._legal_skeleton(deck)
        card = make_card("MN-001")
        RiftboundDeckEntry.objects.create(deck=deck, card=card, quantity=4, zone=ZONE_MAIN)
        self.fill_zone(deck, ZONE_MAIN, 36, "MN", start=2)

        result = validate_riftbound_deck(deck)

        self.assertFalse(result["valid"])
        self.assertTrue(any("Máximo 3 copias" in e for e in result["errors"]))

    def test_three_copies_of_a_normal_card_is_valid(self):
        deck = self.make_deck()
        self._legal_skeleton(deck)
        card = make_card("MN-001")
        RiftboundDeckEntry.objects.create(deck=deck, card=card, quantity=3, zone=ZONE_MAIN)
        self.fill_zone(deck, ZONE_MAIN, 37, "MN", start=2)

        result = validate_riftbound_deck(deck)

        self.assertTrue(result["valid"], result["errors"])

    def test_unique_keyword_card_limited_to_one_copy(self):
        deck = self.make_deck()
        self._legal_skeleton(deck)
        unique_card = make_card("MN-001", description="Some text [Unique] more text")
        RiftboundDeckEntry.objects.create(deck=deck, card=unique_card, quantity=2, zone=ZONE_MAIN)
        self.fill_zone(deck, ZONE_MAIN, 38, "MN", start=2)

        result = validate_riftbound_deck(deck)

        self.assertFalse(result["valid"])
        self.assertTrue(any("[Unique]" in e for e in result["errors"]))

    def test_unique_keyword_card_with_one_copy_is_valid(self):
        deck = self.make_deck()
        self._legal_skeleton(deck)
        unique_card = make_card("MN-001", description="[Unique]")
        RiftboundDeckEntry.objects.create(deck=deck, card=unique_card, quantity=1, zone=ZONE_MAIN)
        self.fill_zone(deck, ZONE_MAIN, 39, "MN", start=2)

        result = validate_riftbound_deck(deck)

        self.assertTrue(result["valid"], result["errors"])

    def test_rune_zone_is_exempt_from_the_default_copy_limit(self):
        deck = self.make_deck()
        self.fill_zone(deck, ZONE_MAIN, 40, "MN", per_card_qty=2)
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")
        rune_card = make_card("RN-001")
        RiftboundDeckEntry.objects.create(deck=deck, card=rune_card, quantity=12, zone=ZONE_RUNE)

        result = validate_riftbound_deck(deck)

        self.assertTrue(result["valid"], result["errors"])

    def test_banned_card_is_always_invalid_regardless_of_quantity(self):
        deck = self.make_deck()
        self._legal_skeleton(deck)
        banned_card = make_card("MN-001")
        RiftboundBanlistEntry.objects.create(
            format=self.fmt, card=banned_card, status=RiftboundBanlistEntry.BANNED, max_copies=0,
        )
        RiftboundDeckEntry.objects.create(deck=deck, card=banned_card, quantity=1, zone=ZONE_MAIN)
        self.fill_zone(deck, ZONE_MAIN, 39, "MN", start=2)

        result = validate_riftbound_deck(deck)

        self.assertFalse(result["valid"])
        self.assertTrue(any("prohibida" in e.lower() for e in result["errors"]))

    def test_limited_to_one_banlist_entry_rejects_second_copy(self):
        deck = self.make_deck()
        self._legal_skeleton(deck)
        limited_card = make_card("MN-001")
        RiftboundBanlistEntry.objects.create(
            format=self.fmt, card=limited_card, status=RiftboundBanlistEntry.LIMITED_1, max_copies=1,
        )
        RiftboundDeckEntry.objects.create(deck=deck, card=limited_card, quantity=2, zone=ZONE_MAIN)
        self.fill_zone(deck, ZONE_MAIN, 38, "MN", start=2)

        result = validate_riftbound_deck(deck)

        self.assertFalse(result["valid"])
        self.assertTrue(any("limitada a 1 copia" in e.lower() for e in result["errors"]))

    def test_banlist_entry_for_a_different_format_does_not_apply(self):
        other_fmt = RiftboundFormat.objects.create(code="casual", name="Casual")
        deck = self.make_deck(fmt=other_fmt)
        self.fill_zone(deck, ZONE_MAIN, 40, "MN", per_card_qty=2)
        self.fill_zone(deck, ZONE_RUNE, 12, "RN")
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")

        # Ban solo aplica al formato "standard", no a "casual"
        first_main_card = deck.entries.filter(zone=ZONE_MAIN).first().card
        RiftboundBanlistEntry.objects.create(
            format=self.fmt, card=first_main_card, status=RiftboundBanlistEntry.BANNED, max_copies=0,
        )

        result = validate_riftbound_deck(deck)

        self.assertTrue(result["valid"], result["errors"])

    def test_deck_without_format_skips_banlist_lookup_without_crashing(self):
        deck = self.make_deck(fmt=None)
        self.fill_zone(deck, ZONE_MAIN, 40, "MN", per_card_qty=2)
        self.fill_zone(deck, ZONE_RUNE, 12, "RN")
        self.fill_zone(deck, ZONE_CHAMPION, 1, "CH")
        self.fill_zone(deck, ZONE_BATTLEFIELD, 3, "BG")

        result = validate_riftbound_deck(deck)

        self.assertTrue(result["valid"], result["errors"])


class DeckApiHardLimitTests(RiftboundValidationBaseTestCase):
    """La API rechaza limites duros que el builder nunca permite (QA 2026-09-16, tarea 2.3)."""

    def setUp(self):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        self.client = APIClient()
        token = RefreshToken.for_user(self.owner).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.url = "/api/riftbound/decks/"

    def _post(self, entries):
        return self.client.post(self.url, {"name": "Mazo", "entries": entries}, format="json")

    def _cards(self, prefix, count):
        return [make_card(f"{prefix}-{i:03d}") for i in range(count)]

    def test_rejects_4_copies(self):
        card = make_card("API-001")
        resp = self._post([{"card": card.id, "quantity": 4, "zone": ZONE_MAIN}])
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(RiftboundDeck.objects.exists())

    def test_rejects_99_copies(self):
        card = make_card("API-002")
        resp = self._post([{"card": card.id, "quantity": 99, "zone": ZONE_MAIN}])
        self.assertEqual(resp.status_code, 400)

    def test_rejects_41_in_main(self):
        cards = self._cards("M41", 14)
        entries = [{"card": c.id, "quantity": 3, "zone": ZONE_MAIN} for c in cards[:13]]  # 39
        entries.append({"card": cards[13].id, "quantity": 2, "zone": ZONE_MAIN})  # 41
        resp = self._post(entries)
        self.assertEqual(resp.status_code, 400)

    def test_rejects_zero_quantity(self):
        card = make_card("API-003")
        resp = self._post([{"card": card.id, "quantity": 0, "zone": ZONE_MAIN}])
        self.assertEqual(resp.status_code, 400)

    def test_incomplete_deck_with_20_in_main_is_accepted(self):
        cards = self._cards("M20", 10)
        resp = self._post([{"card": c.id, "quantity": 2, "zone": ZONE_MAIN} for c in cards])
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_runes_can_repeat_up_to_zone_size(self):
        rune = make_card("RUNE-1", card_type="rune")
        resp = self._post([{"card": rune.id, "quantity": 12, "zone": ZONE_RUNE}])
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_spiderling_is_exempt_from_copy_limit(self):
        spider = make_card("SPD-1", name="Spiderling")
        resp = self._post([{"card": spider.id, "quantity": 10, "zone": ZONE_MAIN}])
        self.assertEqual(resp.status_code, 201, resp.data)


class CollectionInvalidInputTests(RiftboundValidationBaseTestCase):
    """Ids de carta no numéricos o bodies mal formados responden 4xx, nunca 500."""

    def setUp(self):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        self.client = APIClient()
        token = RefreshToken.for_user(self.owner).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_non_numeric_card_ids(self):
        for url, body in (
            ("/api/riftbound/collection/upsert/", {"card": "xyz"}),
            ("/api/riftbound/wishlist/toggle/", {"card": "xyz"}),
            ("/api/riftbound/wishlist/set-quantity/", {"card": "xyz", "desired_quantity": 2}),
        ):
            resp = self.client.post(url, body, format="json")
            self.assertEqual(resp.status_code, 404, url)

    def test_malformed_bodies(self):
        resp = self.client.post("/api/riftbound/collection/batch-upsert/", [1, 2], format="json")
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post("/api/riftbound/collection/bulk-import/", {"text": 123}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_out_of_range_values_never_500(self):
        card = make_card("RNG-001")
        huge = 99999999999999999999
        resp = self.client.post(
            "/api/riftbound/collection/upsert/", {"card": card.id, "quantity": huge, "price": huge}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["quantity"], 9999)
        self.assertEqual(resp.json()["price"], 99_999_999)
        resp = self.client.post(
            "/api/riftbound/wishlist/set-quantity/", {"card": huge, "desired_quantity": huge}, format="json",
        )
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get("/api/riftbound/collection/", {"store_profile_id": huge})
        self.assertIn(resp.status_code, (400, 403))

    def test_binder_avatar_rejects_foreign_urls(self):
        resp = self.client.post("/api/riftbound/profile/avatar/", {"avatar_url": "https://evil.test/x.png"}, format="json")
        self.assertEqual(resp.status_code, 400)


class ZoneLabelMessageTests(RiftboundValidationBaseTestCase):
    def test_errors_use_readable_zone_names(self):
        deck = self.make_deck()
        errors = validate_riftbound_deck(deck)["errors"]
        self.assertTrue(any(e.startswith("Mazo principal (main)") for e in errors), errors)
        self.assertFalse(any("Zona '" in e for e in errors), errors)
