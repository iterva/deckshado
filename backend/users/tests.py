from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from backend.cdn_image_upload import is_allowed_avatar_url

User = get_user_model()


class AvatarUrlTests(APITestCase):
    """El avatar se muestra a otros usuarios: solo se aceptan URLs de nuestras CDN o de Google (QA 2026-09-26, M5)."""

    def setUp(self):
        self.user = User.objects.create_user(username="avatar-user", password="x")
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_allowed_hosts(self):
        for ok in (
            "https://res.cloudinary.com/demo/image/upload/a.png",
            "https://ik.imagekit.io/demo/a.png",
            "https://lh3.googleusercontent.com/a/abc=s96-c",
        ):
            self.assertTrue(is_allowed_avatar_url(ok), ok)

    def test_rejects_foreign_or_unsafe_urls(self):
        for bad in (
            "https://evil.test/x.png",
            "javascript:alert(1)",
            "http://127.0.0.1:8000/admin/",
            "data:image/svg+xml;base64,PHN2Zy8+",
            "http://res.cloudinary.com/a.png",
            "https://res.cloudinary.com.evil.test/a.png",
        ):
            resp = self.client.post(reverse("upload-avatar"), {"avatar_url": bad}, format="json")
            self.assertEqual(resp.status_code, 400, bad)

    def test_accepts_cdn_url(self):
        resp = self.client.post(
            reverse("upload-avatar"), {"avatar_url": "https://res.cloudinary.com/demo/a.png"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["avatar_url"], "https://res.cloudinary.com/demo/a.png")
