from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("riftbound", "0011_riftboundsyncstate"),
    ]

    operations = [
        migrations.CreateModel(
            name="RiftboundOpsRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(db_index=True, default="riftcodex", max_length=30)),
                ("kind", models.CharField(choices=[("sync", "Sync"), ("audit", "Audit")], db_index=True, max_length=20)),
                ("command", models.CharField(max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[("running", "Running"), ("success", "Success"), ("error", "Error")],
                        db_index=True,
                        default="running",
                        max_length=20,
                    ),
                ),
                ("args", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("duration_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("output", models.TextField(blank=True, default="")),
                ("error", models.TextField(blank=True, default="")),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="riftbound_ops_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at"],
            },
        ),
    ]
