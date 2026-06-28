from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("riftbound", "0012_riftboundopsrun"),
    ]

    operations = [
        migrations.CreateModel(
            name="RiftboundStoreOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("buyer_name", models.CharField(blank=True, default="", max_length=100)),
                ("buyer_whatsapp", models.CharField(blank=True, default="", max_length=30)),
                ("buyer_note", models.TextField(blank=True, default="", max_length=800)),
                ("seller_note", models.TextField(blank=True, default="", max_length=800)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pendiente"), ("accepted", "Aceptado"), ("cancelled", "Cancelado")],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "total_estimated",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Total estimado en moneda local (sumatoria de line_total con precio conocido).",
                        null=True,
                    ),
                ),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "buyer_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="riftbound_store_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "store_profile",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="orders", to="riftbound.riftboundbinderprofile"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RiftboundStoreOrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price", models.PositiveIntegerField(blank=True, null=True)),
                ("line_total", models.PositiveIntegerField(blank=True, null=True)),
                ("card_name", models.CharField(blank=True, default="", max_length=200)),
                ("card_number", models.CharField(blank=True, default="", max_length=20)),
                (
                    "language",
                    models.CharField(
                        choices=[("EN", "English"), ("ZH", "中文")],
                        default="EN",
                        max_length=4,
                    ),
                ),
                ("is_foil", models.BooleanField(default=False)),
                (
                    "card",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="store_order_items", to="riftbound.riftboundcard"),
                ),
                (
                    "collection_entry",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="order_items",
                        to="riftbound.riftboundcollectionentry",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="items", to="riftbound.riftboundstoreorder"),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
