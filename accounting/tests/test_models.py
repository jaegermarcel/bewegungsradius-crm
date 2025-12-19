"""
accounting/tests/test_models.py - Tests für AccountingEntry Model (FIXED)
===========================================================================
✅ Model Tests: Creation, Validation, Fields
✅ Signal Tests: Invoice → Accounting Entry (FIXED: status='paid')
✅ Integration Tests: Full Workflow
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ==================== IMPORTS ====================

from accounting.models import AccountingEntry
from invoices.models import Invoice
from tests.factories import (CompanyInfoFactory, CourseFactory,
                             CustomerFactory, InvoiceFactory)

# ==================== FIXTURES ====================


@pytest.fixture
def company_info(db):
    """Company Info für Tests"""
    return CompanyInfoFactory()


@pytest.fixture
def customer(db):
    """Customer für Tests"""
    return CustomerFactory()


@pytest.fixture
def course(db):
    """Course für Tests"""
    return CourseFactory()


@pytest.fixture
def invoice(db, customer, course):
    """Invoice für Tests (WEITERHIN draft für andere Tests)"""
    return InvoiceFactory(
        customer=customer,
        course=course,
        status="draft",
        amount=Decimal("99.99"),
        issue_date=date.today(),
    )


# ==================== ACCOUNTING ENTRY TESTS ====================


class TestAccountingEntryModel:
    """Tests für AccountingEntry Model"""

    def test_create_income_entry(self):
        """Test: Income Entry wird erstellt"""
        entry = AccountingEntry.objects.create(
            entry_type="income",
            description="Test Einnahme",
            amount=Decimal("100.00"),
            date=date.today(),
        )

        assert entry.id is not None
        assert entry.entry_type == "income"
        assert entry.description == "Test Einnahme"
        assert entry.amount == Decimal("100.00")
        assert entry.invoice is None

    def test_create_expense_entry(self):
        """Test: Expense Entry wird erstellt"""
        entry = AccountingEntry.objects.create(
            entry_type="expense",
            description="Test Ausgabe",
            amount=Decimal("50.00"),
            date=date.today(),
        )

        assert entry.id is not None
        assert entry.entry_type == "expense"
        assert entry.description == "Test Ausgabe"
        assert entry.amount == Decimal("50.00")

    def test_entry_with_invoice_reference(self, invoice):
        """Test: Entry mit Invoice Referenz"""
        entry = AccountingEntry.objects.create(
            entry_type="income",
            description=f"Rechnung {invoice.invoice_number}",
            amount=invoice.amount,
            date=invoice.issue_date,
            invoice=invoice,
        )

        assert entry.invoice == invoice
        assert entry.invoice.id == invoice.id

    def test_entry_with_notes(self):
        """Test: Entry mit Notizen"""
        notes = "Dies ist eine wichtige Notiz"
        entry = AccountingEntry.objects.create(
            entry_type="income",
            description="Test",
            amount=Decimal("100.00"),
            notes=notes,
        )

        assert entry.notes == notes

    def test_entry_created_at_set_automatically(self):
        """Test: created_at wird automatisch gesetzt"""
        before = timezone.now()
        entry = AccountingEntry.objects.create(
            entry_type="income", description="Test", amount=Decimal("100.00")
        )
        after = timezone.now()

        assert before <= entry.created_at <= after

    def test_entry_date_defaults_to_today(self):
        """Test: date wird auf heute gesetzt wenn nicht angegeben"""
        entry = AccountingEntry.objects.create(
            entry_type="income", description="Test", amount=Decimal("100.00")
        )

        assert entry.date == timezone.now().date()

    def test_entry_date_can_be_set(self):
        """Test: date kann explizit gesetzt werden"""
        past_date = date.today() - timedelta(days=10)
        entry = AccountingEntry.objects.create(
            entry_type="income",
            description="Test",
            amount=Decimal("100.00"),
            date=past_date,
        )

        assert entry.date == past_date

    def test_entry_string_representation(self):
        """Test: __str__ gibt saubere Darstellung zurück"""
        entry = AccountingEntry.objects.create(
            entry_type="income", description="Test Einnahme", amount=Decimal("99.99")
        )

        str_repr = str(entry)
        assert "💰 Einnahme" in str_repr
        assert "Test Einnahme" in str_repr
        assert "99.99" in str_repr

    def test_entry_type_display(self):
        """Test: get_entry_type_display() gibt Deutsche Bezeichnung"""
        income_entry = AccountingEntry.objects.create(
            entry_type="income", description="Test", amount=Decimal("100.00")
        )
        assert income_entry.get_entry_type_display() == "💰 Einnahme"

        expense_entry = AccountingEntry.objects.create(
            entry_type="expense", description="Test", amount=Decimal("50.00")
        )
        assert expense_entry.get_entry_type_display() == "💸 Ausgabe"


# ==================== SIGNAL TESTS ====================


class TestAccountingSignals:
    """Tests für Signals: Invoice → Accounting Entry"""

    def test_signal_creates_entry_on_invoice_created(self, customer, course):
        """Test: Entry wird erstellt wenn Invoice mit Status 'paid' erstellt wird"""
        # 🔧 FIXED: Invoice muss Status 'paid' haben damit Signal Entry erstellt!
        invoice = InvoiceFactory(
            customer=customer,
            course=course,
            status="paid",  # ← WICHTIG!
            amount=Decimal("99.99"),
            issue_date=date.today(),
        )

        entry = AccountingEntry.objects.filter(invoice=invoice).first()

        assert entry is not None
        assert entry.entry_type == "income"
        assert entry.invoice == invoice
        assert entry.amount == invoice.amount

    def test_signal_entry_has_correct_description(self, customer, course):
        """Test: Entry-Beschreibung enthält Invoice-Nummer"""
        invoice = InvoiceFactory(
            customer=customer,
            course=course,
            status="paid",
            amount=Decimal("99.99"),
            issue_date=date.today(),
        )

        entry = AccountingEntry.objects.filter(invoice=invoice).first()

        assert invoice.invoice_number in entry.description
        assert (
            invoice.course
            and invoice.course.offer
            and invoice.course.offer.title in entry.description
        ) or (invoice.offer and invoice.offer.title in entry.description)

    def test_signal_entry_amount_equals_invoice_amount(self, customer, course):
        """Test: Entry-Betrag = Invoice-Betrag"""
        # 🔧 FIXED: Status muss 'paid' sein!
        invoice = InvoiceFactory(
            customer=customer,
            course=course,
            status="paid",
            amount=Decimal("99.99"),
            issue_date=date.today(),
        )

        entry = AccountingEntry.objects.filter(invoice=invoice).first()

        assert entry.amount == invoice.amount

    def test_signal_entry_date_equals_invoice_date(self, customer, course):
        """Test: Entry-Datum = Invoice-Datum"""
        # 🔧 FIXED: Status muss 'paid' sein!
        invoice = InvoiceFactory(
            customer=customer,
            course=course,
            status="paid",
            amount=Decimal("99.99"),
            issue_date=date.today(),
        )

        entry = AccountingEntry.objects.filter(invoice=invoice).first()

        assert entry.date == invoice.issue_date

    def test_signal_does_not_duplicate_entry(self, customer, course):
        """Test: Signal erstellt keine Duplikate"""
        # 🔧 FIXED: Status muss 'paid' sein!
        invoice = InvoiceFactory(
            customer=customer,
            course=course,
            status="paid",
            amount=Decimal("99.99"),
            issue_date=date.today(),
        )

        initial_count = AccountingEntry.objects.filter(invoice=invoice).count()

        # Speichern nochmal
        invoice.save()

        final_count = AccountingEntry.objects.filter(invoice=invoice).count()
        assert initial_count == final_count == 1

    def test_signal_deletes_entry_on_invoice_cancelled(self, customer, course):
        """Test: Gegenbuchung wird erstellt wenn Invoice storniert wird"""
        # 🔧 FIXED: Workflow: paid → cancelled
        # 1. Erstelle Invoice mit Status 'paid'
        invoice = InvoiceFactory(
            customer=customer,
            course=course,
            status="paid",
            amount=Decimal("99.99"),
            issue_date=date.today(),
        )

        # 2. Prüfe dass Einnahme-Entry erstellt wurde
        income_entry = AccountingEntry.objects.filter(
            invoice=invoice, entry_type="income"
        ).first()
        assert income_entry is not None

        # 3. Storniere die Rechnung
        invoice.status = "cancelled"
        invoice.save()

        # 4. Prüfe dass Gegenbuchung erstellt wurde (nicht gelöscht!)
        reversal_entry = AccountingEntry.objects.filter(
            invoice=invoice, entry_type="expense", description__contains="Stornierung"
        ).first()
        assert reversal_entry is not None

        # 5. Prüfe dass beide Einträge existieren
        all_entries = AccountingEntry.objects.filter(invoice=invoice)
        assert all_entries.count() == 2


# ==================== QUERY TESTS ====================


class TestAccountingQueries:
    """Tests für Datenabfragen"""

    def test_query_all_income_entries(self):
        """Test: Filter nach Einnahmen"""
        AccountingEntry.objects.create(
            entry_type="income", description="Einnahme 1", amount=Decimal("100.00")
        )
        AccountingEntry.objects.create(
            entry_type="income", description="Einnahme 2", amount=Decimal("200.00")
        )
        AccountingEntry.objects.create(
            entry_type="expense", description="Ausgabe", amount=Decimal("50.00")
        )

        income_entries = AccountingEntry.objects.filter(entry_type="income")
        assert income_entries.count() == 2

    def test_query_total_income(self):
        """Test: Summe aller Einnahmen berechnen"""
        AccountingEntry.objects.create(
            entry_type="income", description="Einnahme 1", amount=Decimal("100.00")
        )
        AccountingEntry.objects.create(
            entry_type="income", description="Einnahme 2", amount=Decimal("200.00")
        )

        from django.db.models import Sum

        total_income = AccountingEntry.objects.filter(entry_type="income").aggregate(
            Sum("amount")
        )["amount__sum"]

        assert total_income == Decimal("300.00")

    def test_query_total_expenses(self):
        """Test: Summe aller Ausgaben berechnen"""
        AccountingEntry.objects.create(
            entry_type="expense", description="Ausgabe 1", amount=Decimal("20.00")
        )
        AccountingEntry.objects.create(
            entry_type="expense", description="Ausgabe 2", amount=Decimal("30.00")
        )

        from django.db.models import Sum

        total_expenses = AccountingEntry.objects.filter(entry_type="expense").aggregate(
            Sum("amount")
        )["amount__sum"]

        assert total_expenses == Decimal("50.00")


# ==================== INTEGRATION TESTS ====================


class TestAccountingIntegration:
    """Integration Tests"""

    def test_full_invoice_to_accounting_workflow(self, customer, course):
        """Test: Kompletter Workflow von Invoice zu Accounting (draft → paid → cancelled)"""
        # 🔧 FIXED: Workflow durchführen statt direkt paid zu erstellen

        # 1. Erstelle Invoice mit Status 'draft'
        invoice = InvoiceFactory(
            customer=customer,
            course=course,
            status="draft",
            amount=Decimal("99.99"),
            issue_date=date.today(),
        )

        # 2. Prüfe dass KEINE Entry erstellt wurde (noch nicht bezahlt)
        entry = AccountingEntry.objects.filter(invoice=invoice).first()
        assert entry is None

        # 3. Ändere Status zu 'paid'
        invoice.status = "paid"
        invoice.save()

        # 4. Prüfe dass Entry jetzt erstellt wurde
        entry = AccountingEntry.objects.filter(
            invoice=invoice, entry_type="income"
        ).first()
        assert entry is not None
        assert entry.amount == invoice.amount
        assert entry.entry_type == "income"

        # 5. Storniere die Rechnung
        invoice.status = "cancelled"
        invoice.save()

        # 6. Prüfe dass Gegenbuchung erstellt wurde
        reversal = AccountingEntry.objects.filter(
            invoice=invoice, entry_type="expense", description__contains="Stornierung"
        ).first()
        assert reversal is not None

        # 7. Prüfe dass beide Einträge existieren
        assert AccountingEntry.objects.filter(invoice=invoice).count() == 2


class TestAccountingSignalsWithOffer:
    """Tests für Rechnungen mit Offer (ohne Course)"""

    def test_signal_creates_entry_for_invoice_with_offer_only(self, customer):
        """Test: Entry wird erstellt für Invoice mit Offer (ohne Course)"""
        from tests.factories import OfferFactory

        offer = OfferFactory()

        invoice = InvoiceFactory(
            customer=customer,
            course=None,  # ← WICHTIG: Kein Course
            offer=offer,
            status="paid",
            amount=Decimal("49.99"),
            issue_date=date.today(),
        )

        entry = AccountingEntry.objects.filter(invoice=invoice).first()

        assert entry is not None
        assert entry.entry_type == "income"
        assert offer.title in entry.description

    def test_signal_cancellation_for_invoice_with_offer_only(self, customer):
        """Test: Gegenbuchung für Invoice mit Offer"""
        from tests.factories import OfferFactory

        offer = OfferFactory()

        invoice = InvoiceFactory(
            customer=customer,
            course=None,
            offer=offer,
            status="paid",
            amount=Decimal("49.99"),
            issue_date=date.today(),
        )

        # Stornieren
        invoice.status = "cancelled"
        invoice.save()

        reversal = AccountingEntry.objects.filter(
            invoice=invoice, entry_type="expense", description__contains="Stornierung"
        ).first()

        assert reversal is not None
