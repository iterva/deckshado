from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0001_initial"),
        ("decks", "0010_deckcomment_decksnapshot_decklike"),
    ]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="cover_card",
            field=models.ForeignKey(
                blank=True,
                help_text="Carta destacada como portada del mazo (opcional).",
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="+",
                to="cards.card",
            ),
        ),
    ]
