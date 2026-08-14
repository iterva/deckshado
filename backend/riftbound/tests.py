from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import RiftboundCard, RiftboundCollectionEntry, RiftboundSet


class RiftboundCollectionUpsertTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(
			username="riftbound-tester",
			email="riftbound@test.local",
			password="test-pass-123",
		)
		self.client.force_authenticate(user=self.user)

		self.rb_set = RiftboundSet.objects.create(code="TST", name="Test Set")
		self.card = RiftboundCard.objects.create(
			card_number="TST-001",
			name="Carta Test",
			slug="carta-test",
			set=self.rb_set,
			card_type="unit",
			rarity="common",
		)

		self.upsert_url = reverse("riftbound-collection-upsert")
		self.batch_upsert_url = reverse("riftbound-collection-batch-upsert")

	def test_upsert_with_entry_id_toggles_foil_without_duplicate(self):
		entry = RiftboundCollectionEntry.objects.create(
			user=self.user,
			card=self.card,
			quantity=2,
			is_foil=False,
		)

		resp = self.client.post(
			self.upsert_url,
			{"id": entry.id, "card": self.card.id, "is_foil": True, "quantity": 2},
			format="json",
		)

		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		entry.refresh_from_db()
		self.assertTrue(entry.is_foil)
		self.assertEqual(resp.data["id"], entry.id)
		self.assertEqual(
			RiftboundCollectionEntry.objects.filter(user=self.user, card=self.card).count(),
			1,
		)

	def test_batch_upsert_with_entry_id_toggles_foil_without_duplicate(self):
		entry = RiftboundCollectionEntry.objects.create(
			user=self.user,
			card=self.card,
			quantity=1,
			is_foil=False,
		)

		resp = self.client.post(
			self.batch_upsert_url,
			[{"id": entry.id, "card": self.card.id, "is_foil": True, "quantity": 3}],
			format="json",
		)

		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertEqual(resp.data.get("updated"), 1)
		entry.refresh_from_db()
		self.assertTrue(entry.is_foil)
		self.assertEqual(entry.quantity, 3)
		self.assertEqual(
			RiftboundCollectionEntry.objects.filter(user=self.user, card=self.card).count(),
			1,
		)

	def test_batch_upsert_accepts_more_than_200_changes(self):
		changes = [{"card": self.card.id, "quantity": 1} for _ in range(201)]

		resp = self.client.post(self.batch_upsert_url, changes, format="json")

		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertEqual(resp.data.get("updated"), 201)
