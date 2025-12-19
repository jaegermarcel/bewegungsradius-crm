# accounting/models.py - MINIMAL: Nur Einnahmen & Ausgaben

from datetime import date
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class AccountingEntry(models.Model):
    """Einnahmen oder Ausgaben"""

    ENTRY_TYPE_CHOICES = [
        ("income", "💰 Einnahme"),
        ("expense", "💸 Ausgabe"),
    ]

    entry_type = models.CharField(
        max_length=10, choices=ENTRY_TYPE_CHOICES, verbose_name="Typ"
    )

    description = models.CharField(max_length=200, verbose_name="Beschreibung")

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Betrag",
    )

    date = models.DateField(default=date.today, verbose_name="Datum")

    # Verknüpfung zu Invoice (OPTIONAL)
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="accounting_entries",
        verbose_name="Rechnung",
    )

    notes = models.TextField(blank=True, verbose_name="Notizen")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")

    class Meta:
        verbose_name = "Ein-/Ausgabe"
        verbose_name_plural = "Ein-/Ausgaben"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_entry_type_display()} - {self.description} ({self.amount}€)"


# ==================== SIGNALS: Invoice → Accounting ====================


def _get_invoice_title_safe(invoice):
    """
    ✅ SICHER: Gibt Rechnungstitel zurück
    Prüft Course → Offer, fallback auf Offer direkt
    """
    if invoice.course:
        return (
            invoice.course.offer.title if invoice.course.offer else invoice.course.title
        )
    elif invoice.offer:
        return invoice.offer.title
    return "Rechnung ohne Titel"


@receiver(post_save, sender="invoices.Invoice")
def create_accounting_entry_from_invoice(sender, instance, created, **kwargs):
    """
    🔧 FIXED: Accounting Entries mit Gegenbuchung bei Stornierung
    ✅ Sichere Behandlung von Course UND Offer

    Logik:
    - Status 'draft' oder 'sent' → Kein Eintrag (noch nicht bezahlt)
    - Status 'paid' → Eintrag erstellen (Umsatz zählt!)
    - Status 'cancelled' → Gegenbuchung erstellen (Stornierung)
    """
    invoice = instance

    # ❌ Noch nicht bezahlt → Nichts tun (oder löschen falls vorhanden)
    if invoice.status in ["draft", "sent", "overdue"]:
        AccountingEntry.objects.filter(invoice=invoice).delete()
        return

    # ✅ Bezahlt → Eintrag erstellen
    if invoice.status == "paid":
        existing = AccountingEntry.objects.filter(invoice=invoice).first()

        if existing:
            # Bereits vorhanden - nicht nochmal erstellen!
            return

        # Neuer Eintrag erstellen - NUR für bezahlte Rechnungen!
        AccountingEntry.objects.create(
            entry_type="income",
            description=f"Rechnung {invoice.invoice_number} - {_get_invoice_title_safe(invoice)}",
            amount=invoice.total_amount,
            date=invoice.issue_date,
            invoice=invoice,
            notes=f"Automatisch von Rechnung {invoice.invoice_number}",
        )
        return

    # 🔧 STORNIERT → Gegenbuchung NUR wenn Einnahme-Eintrag existiert!
    if invoice.status == "cancelled":
        # Prüfe ob Einnahme-Eintrag existiert
        income_entry = AccountingEntry.objects.filter(
            invoice=invoice, entry_type="income"
        ).first()

        if not income_entry:
            # Kein Einnahme-Eintrag → Keine Gegenbuchung nötig
            return

        # Prüfe ob Gegenbuchung schon existiert
        reversal_exists = AccountingEntry.objects.filter(
            invoice=invoice, entry_type="expense", description__contains="Stornierung"
        ).exists()

        if reversal_exists:
            # Gegenbuchung existiert schon
            return

        # 🔧 Erstelle Gegenbuchung nur wenn Einnahme-Eintrag existiert!
        AccountingEntry.objects.create(
            entry_type="expense",  # 💸 Ausgabe = Gegenbuchung
            description=f"Stornierung: Rechnung {invoice.invoice_number} - {_get_invoice_title_safe(invoice)}",
            amount=income_entry.amount,  # Gleicher Betrag wie Original!
            date=invoice.cancelled_at.date() if invoice.cancelled_at else date.today(),
            invoice=invoice,
            notes=f"Storno-Nummer: {invoice.cancelled_invoice_number or 'N/A'} - Gegenbuchung zu Einnahme-Eintrag",
        )
