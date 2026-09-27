"""QA #2 A4: los comandos de nombres prefieren la forma con tildes y mayúsculas."""
import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from cards.models import Card, Edition, Format


class FixCardNamesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fmt = Format.objects.create(code="imp", name="Imperio")
        ed = Edition.objects.create(myl_id="ed-n", slug="ed-n", title="Ed N", format=fmt, active=True)
        cls.good = Card.objects.create(myl_id="n1", edid="001", slug="n1", name="Transformación", edition=ed)
        cls.bad = Card.objects.create(myl_id="n2", edid="002", slug="n2", name="transformacion", edition=ed)
        cls.orphan = Card.objects.create(myl_id="n3", edid="003", slug="n3", name="aku aku", edition=ed)

    def _run(self, *args):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            call_command("fix_card_names", "--csv", path, *args, stdout=StringIO())
        finally:
            os.remove(path)

    def test_dry_run_changes_nothing(self):
        self._run("--dry-run")
        self.bad.refresh_from_db()
        self.assertEqual(self.bad.name, "transformacion")

    def test_uses_existing_well_written_variant(self):
        self._run()
        self.bad.refresh_from_db()
        self.orphan.refresh_from_db()
        self.assertEqual(self.bad.name, "Transformación")
        self.assertEqual(self.orphan.name, "aku aku")

    def test_capitalize_orphans(self):
        self._run("--capitalize")
        self.orphan.refresh_from_db()
        self.assertEqual(self.orphan.name, "Aku aku")

    def test_normalize_card_names_prefers_accented_form(self):
        call_command("normalize_card_names", stdout=StringIO())
        self.bad.refresh_from_db()
        self.good.refresh_from_db()
        self.assertEqual(self.bad.name, "Transformación")
        self.assertEqual(self.good.name, "Transformación")
