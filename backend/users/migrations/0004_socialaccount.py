from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_avatar_to_urlfield"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("provider", models.CharField(default="google", max_length=20)),
                ("provider_uid", models.CharField(max_length=255)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("linked_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="social_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("provider", "provider_uid"),
                        name="users_socialaccount_provider_uid_unique",
                    ),
                ],
            },
        ),
    ]
