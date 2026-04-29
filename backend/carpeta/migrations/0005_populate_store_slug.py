from django.db import migrations


def populate_slugs(apps, schema_editor):
    BinderProfile = apps.get_model("carpeta", "BinderProfile")
    import re, uuid

    def slugify(value):
        value = (value or "").strip().lower()
        value = re.sub(r"[^a-z0-9_-]+", "-", value)
        value = re.sub(r"-+", "-", value).strip("-")
        return value[:60] or str(uuid.uuid4())[:8]

    used = set()
    for p in BinderProfile.objects.all().select_related("user"):
        base = slugify(p.user.username)
        slug = base
        i = 2
        while slug in used or BinderProfile.objects.filter(store_slug=slug).exclude(pk=p.pk).exists():
            slug = f"{base}-{i}"
            i += 1
        used.add(slug)
        p.store_slug = slug
        p.save(update_fields=["store_slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("carpeta", "0004_binderprofile_accepts_trades_binderprofile_bio_and_more"),
    ]
    operations = [migrations.RunPython(populate_slugs, migrations.RunPython.noop)]
