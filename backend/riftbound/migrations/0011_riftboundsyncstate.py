from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("riftbound", "0010_collectionentry_photos"),
    ]

    operations = [
        migrations.CreateModel(
            name="RiftboundSyncState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(db_index=True, max_length=50, unique=True)),
                ("provider", models.CharField(db_index=True, default="riftcodex", max_length=30)),
                ("last_cursor", models.DateTimeField(blank=True, null=True)),
                ("last_started_at", models.DateTimeField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_stats", models.JSONField(blank=True, default=dict)),
                ("last_error", models.TextField(blank=True, default="")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["provider", "key"],
            },
        ),
    ]
