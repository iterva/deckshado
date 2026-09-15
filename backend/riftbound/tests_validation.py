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
