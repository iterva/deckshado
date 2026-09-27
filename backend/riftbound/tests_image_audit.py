"""audit_riftbound_images: solo vacía cdn_image_url con 404/410 real y respaldo funcional,
sin importar el host (ImageKit de otra cuenta, Cloudinary, etc.)."""
import os
import tempfile
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from riftbound.management.commands.audit_riftbound_images import check_url
from riftbound.models import RiftboundCard, RiftboundSet
from riftbound.serializers import _preferred_riftbound_image

STATUS_BY_URL = {
    "https://ik.imagekit.io/cuenta-a/rota.png": 404,
    "https://ik.imagekit.io/cuenta-b/bien.png": 200,
    "https://res.cloudinary.com/demo/image/upload/bien.png": 200,
    "https://res.cloudinary.com/demo/image/upload/privada.png": 401,
    "https://cmsassets.rgpub.io/oficial.png": 200,
}


def fake_request(url, **kwargs):
    return mock.Mock(status_code=STATUS_BY_URL.get(url, 500), close=lambda: None)


class ImageAuditCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rb_set = RiftboundSet.objects.create(code="OGN", name="Origins")

        def card(number, cdn, image_url):
            return RiftboundCard.objects.create(
                card_number=number, name=number, slug=number.lower(), set=rb_set,
                cdn_image_url=cdn, image_url=image_url,
            )

        cls.broken = card("OGN-001", "https://ik.imagekit.io/cuenta-a/rota.png", "https://cmsassets.rgpub.io/oficial.png")
        cls.other_imagekit = card("OGN-002", "https://ik.imagekit.io/cuenta-b/bien.png", "https://cmsassets.rgpub.io/oficial.png")
        cls.cloudinary = card("OGN-003", "https://res.cloudinary.com/demo/image/upload/bien.png", "https://cmsassets.rgpub.io/oficial.png")
        cls.private = card("OGN-004", "https://res.cloudinary.com/demo/image/upload/privada.png", "https://cmsassets.rgpub.io/oficial.png")
        cls.no_fallback = card("OGN-005", "https://ik.imagekit.io/cuenta-a/rota.png", "")

    def _run(self, *args):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            with mock.patch("requests.Session.head", side_effect=fake_request), \
                 mock.patch("requests.Session.get", side_effect=fake_request):
                call_command("audit_riftbound_images", "--csv", path, "--workers", "1", *args, stdout=StringIO())
        finally:
            os.remove(path)

    def _cdn(self, card):
        card.refresh_from_db()
        return card.cdn_image_url

    def test_audit_without_fix_changes_nothing(self):
        self._run()
        self.assertTrue(self._cdn(self.broken))

    def test_fix_only_clears_missing_urls_with_working_fallback(self):
        self._run("--fix")
        self.assertEqual(self._cdn(self.broken), "")
        self.assertTrue(self._cdn(self.other_imagekit))
        self.assertTrue(self._cdn(self.cloudinary))
        self.assertTrue(self._cdn(self.private))  # 401 no es "no existe"
        self.assertTrue(self._cdn(self.no_fallback))  # sin respaldo: no se borra


class ImageHelpersTests(SimpleTestCase):
    def test_check_url_classification(self):
        session = mock.Mock(head=fake_request, get=fake_request)
        self.assertEqual(check_url(session, "https://ik.imagekit.io/cuenta-a/rota.png", 5), "missing")
        self.assertEqual(check_url(session, "https://res.cloudinary.com/demo/image/upload/bien.png", 5), "ok")
        self.assertEqual(check_url(session, "https://res.cloudinary.com/demo/image/upload/privada.png", 5), "unknown:401")

    def test_cloudinary_cdn_preferred_over_upstream(self):
        self.assertEqual(
            _preferred_riftbound_image("https://res.cloudinary.com/demo/x.png", "https://cmsassets.rgpub.io/x.png"),
            "https://res.cloudinary.com/demo/x.png",
        )
        self.assertEqual(
            _preferred_riftbound_image("", "https://cmsassets.rgpub.io/x.png"),
            "https://cmsassets.rgpub.io/x.png",
        )
