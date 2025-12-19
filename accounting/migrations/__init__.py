import datetime
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("invoices", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountingEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "entry_type",
                    models.CharField(
                        choices=[("income", "💰 Einnahme"), ("expense", "💸 Ausgabe")],
                        max_length=10,
                        verbose_name="Typ",
                    ),
                ),
                (
                    "description",
                    models.CharField(max_length=200, verbose_name="Beschreibung"),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                        verbose_name="Betrag",
                    ),
                ),
                (
                    "date",
                    models.DateField(default=datetime.date.today, verbose_name="Datum"),
                ),
                ("notes", models.TextField(blank=True, verbose_name="Notizen")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am"),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="accounting_entries",
                        to="invoices.invoice",
                        verbose_name="Rechnung",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ein-/Ausgabe",
                "verbose_name_plural": "Ein-/Ausgaben",
                "ordering": ["-date"],
            },
        ),
    ]
