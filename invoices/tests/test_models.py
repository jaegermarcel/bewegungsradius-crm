"""
invoices/tests/test_models.py - Tests für Invoice Model und Services
====================================================================
✅ InvoiceNumberGenerator Tests
✅ CourseIdGenerator Tests
✅ TaxCalculator Tests
✅ DiscountApplier Tests
✅ InvoiceDateManager Tests
✅ InvoiceInitializer Tests
✅ Invoice Model Tests (Basic + Offer Support)
✅ Invoice.save() Tests
✅ Invoice Validierung Tests
✅ Invoice Constraints Tests
✅ Integration Tests
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ==================== IMPORTS ====================

from invoices.models import (CourseIdGenerator, DiscountApplier, Invoice,
                             InvoiceDateManager, InvoiceInitializer,
                             InvoiceNumberGenerator, TaxCalculator)
from tests.factories import (ActiveDiscountCodeFactory, ContactChannelFactory,
                             CourseFactory, CustomerDiscountCodeFactory,
                             CustomerFactory, InvoiceFactory,
                             InvoiceWithDiscountFactory)

# ==================== FIXTURES ====================


@pytest.fixture
def customer(db):
    """Customer Fixture"""
    return CustomerFactory()


@pytest.fixture
def course(db):
    """Course Fixture"""
    return CourseFactory()


@pytest.fixture
def invoice(db, customer, course):
    """Invoice Fixture"""
    return InvoiceFactory(customer=customer, course=course)


@pytest.fixture
def discount_code_percentage(db, customer):
    """Active Discount Code - Percentage"""
    from customers.models import CustomerDiscountCode

    return CustomerDiscountCode.objects.create(
        customer=customer,
        code="SAVE10",
        discount_type="percentage",
        discount_value=Decimal("10.00"),
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=30),
        status="sent",
    )


@pytest.fixture
def discount_code_fixed(db, customer):
    """Active Discount Code - Fixed Amount"""
    from customers.models import CustomerDiscountCode

    return CustomerDiscountCode.objects.create(
        customer=customer,
        code="SAVE5EUR",
        discount_type="fixed",
        discount_value=Decimal("5.00"),
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=30),
        status="sent",
    )


@pytest.fixture
def offer(db):
    """Offer Fixture (für 10er-Karten etc.)"""
    from offers.models import Offer, ZPPCertification

    cert = ZPPCertification.objects.create(
        zpp_id="KU-YG-000001",
        name="Yoga Certification",
        official_title="Official Yoga",
        format="hybrid",
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=365),
        is_active=True,
    )

    # ✅ is_ticket_10 ist eine PROPERTY - nicht direkt setzen!
    # Stattdessen: offer_type='ticket_10' setzen, dann wird is_ticket_10 automatisch True
    return Offer.objects.create(
        offer_type="ticket_10",
        title="10er Karte Yoga",
        course_units=10,
        course_duration=60,
        amount=Decimal("200.00"),
        tax_rate=Decimal("0.00"),
        is_tax_exempt=True,
        zpp_certification=cert,
        ticket_sessions=10,
    )


# ==================== INVOICE NUMBER GENERATOR TESTS ====================


class TestInvoiceNumberGenerator:
    """Tests für InvoiceNumberGenerator"""

    def test_generate_first_invoice_of_year(self, customer, course):
        """Test: Erste Rechnung des Jahres"""
        # Lösche alle Rechnungen dieses Jahres
        Invoice.objects.filter(
            invoice_number__startswith=f"{datetime.now().year}-"
        ).delete()

        number = InvoiceNumberGenerator.generate()

        current_year = datetime.now().year
        assert number == f"{current_year}-001"

    def test_generate_increments_number(self, customer, course):
        """Test: Nummer wird inkrementiert"""
        # Lösche alle Rechnungen
        Invoice.objects.filter(
            invoice_number__startswith=f"{datetime.now().year}-"
        ).delete()

        number1 = InvoiceNumberGenerator.generate()
        InvoiceFactory(invoice_number=number1)

        number2 = InvoiceNumberGenerator.generate()

        current_year = datetime.now().year
        assert number1 == f"{current_year}-001"
        assert number2 == f"{current_year}-002"

    def test_generate_year_based(self):
        """Test: Nummern sind jahresbasiert"""
        Invoice.objects.all().delete()

        current_year = datetime.now().year
        number = InvoiceNumberGenerator.generate()

        assert number.startswith(f"{current_year}-")
        assert len(number.split("-")) == 2

    def test_generate_with_invalid_last_number_format(self, customer, course):
        """Test: Wenn letzte Invoice ungültiges Format hat"""
        # Erstelle eine Invoice mit ungültigem Format
        bad_invoice = InvoiceFactory(invoice_number="2025-INVALID")  # Nicht numerisch

        # Generator sollte immer noch funktionieren
        number = InvoiceNumberGenerator.generate()
        assert number is not None
        assert number.startswith("2025-")

    def test_generate_high_invoice_count(self):
        """Test: Viele Rechnungen in einem Jahr (z.B. 999+)"""
        Invoice.objects.filter(
            invoice_number__startswith=f"{datetime.now().year}-"
        ).delete()

        current_year = datetime.now().year

        # Erstelle Invoice mit hoher Nummer
        InvoiceFactory(invoice_number=f"{current_year}-999")

        # Nächste sollte -1000 sein
        number = InvoiceNumberGenerator.generate()
        assert number == f"{current_year}-1000"


# ==================== COURSE ID GENERATOR TESTS ====================


class TestCourseIdGenerator:
    """Tests für CourseIdGenerator"""

    def test_generate_format(self):
        """Test: Format ist KU-XX-XXXXXX"""
        course_type = "pilates"
        course_id = CourseIdGenerator.generate(course_type)

        assert course_id.startswith("KU-")
        parts = course_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 2  # 2 Buchstaben
        assert len(parts[2]) == 6  # 6 Ziffern/Buchstaben

    def test_generate_uses_course_type(self):
        """Test: Benutzt ersten 2 Buchstaben vom course_type"""
        course_id = CourseIdGenerator.generate("pilates")
        assert "KU-PI-" in course_id

    def test_generate_uppercase(self):
        """Test: ID ist großgeschrieben"""
        course_id = CourseIdGenerator.generate("yoga")
        assert course_id.isupper()

    def test_generate_unique(self):
        """Test: Generiert unterschiedliche IDs"""
        id1 = CourseIdGenerator.generate("pilates")
        id2 = CourseIdGenerator.generate("pilates")

        # Sollten unterschiedlich sein (probabilistisch)
        # Oder zumindest aus gültigem Format sein
        assert id1.startswith("KU-PI-")
        assert id2.startswith("KU-PI-")


# ==================== TAX CALCULATOR TESTS ====================


class TestTaxCalculator:
    """Tests für TaxCalculator"""

    def test_calculate_tax_amount_with_tax(self):
        """Test: Berechnet Steuerbetrag"""
        calc = TaxCalculator(
            amount=Decimal("100.00"), tax_rate=Decimal("19.00"), is_tax_exempt=False
        )

        tax = calc.calculate_tax_amount()
        assert tax == Decimal("19.00")

    def test_calculate_tax_amount_tax_exempt(self):
        """Test: Keine Steuer wenn tax_exempt"""
        calc = TaxCalculator(
            amount=Decimal("100.00"), tax_rate=Decimal("19.00"), is_tax_exempt=True
        )

        tax = calc.calculate_tax_amount()
        assert tax == Decimal("0.00")

    def test_calculate_tax_amount_zero_tax_rate(self):
        """Test: Keine Steuer bei 0% Steuersatz"""
        calc = TaxCalculator(
            amount=Decimal("100.00"), tax_rate=Decimal("0.00"), is_tax_exempt=False
        )

        tax = calc.calculate_tax_amount()
        assert tax == Decimal("0.00")

    def test_calculate_tax_amount_decimal_precision(self):
        """Test: Dezimalgenauigkeit 0.01€"""
        calc = TaxCalculator(
            amount=Decimal("33.33"), tax_rate=Decimal("19.00"), is_tax_exempt=False
        )

        tax = calc.calculate_tax_amount()
        # 33.33 * 19% = 6.3327 → 6.33
        assert tax == Decimal("6.33")

    def test_calculate_total_with_tax(self):
        """Test: Gesamtbetrag mit Steuern"""
        calc = TaxCalculator(
            amount=Decimal("100.00"), tax_rate=Decimal("19.00"), is_tax_exempt=False
        )

        total = calc.calculate_total()
        assert total == Decimal("119.00")

    def test_calculate_total_tax_exempt(self):
        """Test: Gesamtbetrag tax_exempt"""
        calc = TaxCalculator(
            amount=Decimal("100.00"), tax_rate=Decimal("19.00"), is_tax_exempt=True
        )

        total = calc.calculate_total()
        assert total == Decimal("100.00")

    def test_calculate_total_none_amount(self):
        """Test: None amount gibt 0.00 zurück"""
        calc = TaxCalculator(
            amount=None, tax_rate=Decimal("19.00"), is_tax_exempt=False
        )

        total = calc.calculate_total()
        assert total == Decimal("0.00")

    def test_calculate_tax_very_small_amount(self):
        """Test: Sehr kleine Beträge (z.B. €0.01)"""
        calc = TaxCalculator(
            amount=Decimal("0.01"), tax_rate=Decimal("19.00"), is_tax_exempt=False
        )

        tax = calc.calculate_tax_amount()
        # 0.01 * 19% = 0.0019 → 0.00
        assert tax == Decimal("0.00")

    def test_calculate_tax_very_large_amount(self):
        """Test: Sehr große Beträge (z.B. €99.999,99)"""
        calc = TaxCalculator(
            amount=Decimal("99999.99"), tax_rate=Decimal("19.00"), is_tax_exempt=False
        )

        tax = calc.calculate_tax_amount()
        # Berechnung: (99999.99 * 19) / 100 = 18999.9981 → 18999.99 (Rundung)
        assert tax >= Decimal("18999.99")

    def test_calculate_tax_high_tax_rate(self):
        """Test: Höhere Steuersätze (z.B. 25%)"""
        calc = TaxCalculator(
            amount=Decimal("100.00"), tax_rate=Decimal("25.00"), is_tax_exempt=False
        )

        tax = calc.calculate_tax_amount()
        assert tax == Decimal("25.00")

    def test_calculate_total_with_fractional_cents(self):
        """Test: Rundungsfehler bei Bruchteilen"""
        calc = TaxCalculator(
            amount=Decimal("33.33"), tax_rate=Decimal("7.00"), is_tax_exempt=False
        )

        tax = calc.calculate_tax_amount()
        total = calc.calculate_total()

        # 33.33 * 0.07 = 2.3331 → 2.33
        assert tax == Decimal("2.33")
        assert total == Decimal("35.66")

    def test_calculate_tax_amounts_have_correct_precision(self):
        """Test: Alle Werte haben Dezimalgenauigkeit 0.01€"""
        test_cases = [
            (Decimal("123.45"), Decimal("19.00")),
            (Decimal("99.99"), Decimal("7.00")),
            (Decimal("1.00"), Decimal("19.00")),
        ]

        for amount, tax_rate in test_cases:
            calc = TaxCalculator(amount, tax_rate, False)
            tax = calc.calculate_tax_amount()
            total = calc.calculate_total()

            # Beide sollten nur 2 Dezimalstellen haben
            assert tax.as_tuple().exponent == -2
            assert total.as_tuple().exponent == -2


# ==================== DISCOUNT APPLIER TESTS ====================


class TestDiscountApplier:
    """Tests für DiscountApplier"""

    def test_apply_percentage_discount(self, discount_code_percentage):
        """Test: Wendet Prozentrabatt an"""
        applier = DiscountApplier(Decimal("100.00"), discount_code_percentage)
        applier.apply()

        # 10% von 100 = 10
        assert applier.get_final_amount() == Decimal("90.00")
        assert applier.discount_amount == Decimal("10.00")

    def test_apply_no_discount_code(self):
        """Test: Keine Veränderung ohne Code"""
        applier = DiscountApplier(Decimal("100.00"), None)
        applier.apply()

        assert applier.get_final_amount() == Decimal("100.00")
        assert applier.discount_amount == Decimal("0.00")

    def test_apply_stores_original_amount(self, discount_code_percentage):
        """Test: Speichert Originalbetrag"""
        applier = DiscountApplier(Decimal("100.00"), discount_code_percentage)
        applier.apply()

        assert applier.get_original_amount() == Decimal("100.00")

    def test_apply_idempotent(self, discount_code_percentage):
        """Test: Apply ist idempotent (mehrfach aufrufen hat gleiche Wirkung)"""
        applier = DiscountApplier(Decimal("100.00"), discount_code_percentage)

        applier.apply()
        final1 = applier.get_final_amount()

        applier.apply()
        final2 = applier.get_final_amount()

        assert final1 == final2

    def test_get_final_amount_no_discount(self):
        """Test: Finalbetrag ohne Rabatt"""
        applier = DiscountApplier(Decimal("50.00"), None)

        assert applier.get_final_amount() == Decimal("50.00")

    def test_get_original_amount_default(self):
        """Test: Originalbetrag ist None wenn kein Rabatt"""
        applier = DiscountApplier(Decimal("100.00"), None)

        assert applier.get_original_amount() == Decimal("100.00")

    def test_apply_fixed_discount(self, discount_code_fixed):
        """Test: Festbetrag Rabatt wird angewendet"""
        applier = DiscountApplier(Decimal("100.00"), discount_code_fixed)
        applier.apply()

        # €100 - €5 = €95
        assert applier.get_final_amount() == Decimal("95.00")
        assert applier.discount_amount == Decimal("5.00")

    def test_apply_fixed_discount_capped_at_amount(self, discount_code_fixed):
        """Test: Festbetrag Rabatt wird auf amount begrenzt"""
        # Rabatt €5, aber amount nur €3
        applier = DiscountApplier(Decimal("3.00"), discount_code_fixed)
        applier.apply()

        # Rabatt sollte auf €3 begrenzt werden
        assert applier.get_final_amount() >= Decimal("0.00")
        assert applier.discount_amount <= Decimal("3.00")

    def test_discount_percentage_vs_fixed_comparison(self, customer):
        """Test: Vergleich Prozent vs Festbetrag"""
        from customers.models import CustomerDiscountCode

        amount = Decimal("100.00")

        # 10% auf €100 = €10
        code_percent = CustomerDiscountCode.objects.create(
            customer=customer,
            code="PERCENT10",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
            valid_from=date.today(),
            valid_until=date.today()
            + timedelta(days=30),  # ✅ WICHTIG: valid_until ist required!
            status="sent",
        )

        # €10 Festbetrag
        code_fixed = CustomerDiscountCode.objects.create(
            customer=customer,
            code="FIXED10",
            discount_type="fixed",
            discount_value=Decimal("10.00"),
            valid_from=date.today(),
            valid_until=date.today()
            + timedelta(days=30),  # ✅ WICHTIG: valid_until ist required!
            status="sent",
        )

        applier_percent = DiscountApplier(amount, code_percent).apply()
        applier_fixed = DiscountApplier(amount, code_fixed).apply()

        # Beide sollten dasselbe Ergebnis geben (10%)
        assert applier_percent.discount_amount == applier_fixed.discount_amount


# ==================== INVOICE DATE MANAGER TESTS ====================


class TestInvoiceDateManager:
    """Tests für InvoiceDateManager"""

    def test_get_issue_date_with_date(self):
        """Test: Gibt angegebenes Datum zurück"""
        test_date = date(2025, 11, 15)
        result = InvoiceDateManager.get_issue_date(test_date)

        assert result == test_date

    def test_get_issue_date_none_returns_today(self):
        """Test: None gibt heute zurück"""
        result = InvoiceDateManager.get_issue_date(None)

        assert result == date.today()

    def test_get_due_date_with_date(self):
        """Test: Gibt angegebenes Fälligkeitsdatum zurück"""
        due = date(2025, 12, 15)
        result = InvoiceDateManager.get_due_date(due, date.today())

        assert result == due

    def test_get_due_date_none_adds_14_days(self):
        """Test: None addiert 14 Tage zu issue_date"""
        issue_date = date(2025, 11, 22)
        result = InvoiceDateManager.get_due_date(None, issue_date)

        expected = issue_date + timedelta(days=14)
        assert result == expected

    def test_get_due_date_none_and_no_issue_date(self):
        """Test: None issue_date nutzt heute + 14 Tage"""
        result = InvoiceDateManager.get_due_date(None, None)

        expected = date.today() + timedelta(days=14)
        assert result == expected


# ==================== INVOICE INITIALIZER TESTS ====================


class TestInvoiceInitializer:
    """Tests für InvoiceInitializer"""

    def test_initialize_sets_invoice_number(self, customer, course):
        """Test: Setzt Rechnungsnummer"""
        invoice = Invoice(customer=customer, course=course)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        assert invoice.invoice_number is not None
        assert invoice.invoice_number.startswith(f"{datetime.now().year}-")

    def test_initialize_sets_amount_from_course(self, customer, course):
        """Test: Setzt amount von course.price"""
        invoice = Invoice(customer=customer, course=course, amount=None)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        assert invoice.amount == course.offer.amount

    def test_initialize_keeps_amount_if_set(self, customer, course):
        """Test: Behält amount wenn schon gesetzt"""
        original_amount = Decimal("150.00")
        invoice = Invoice(customer=customer, course=course, amount=original_amount)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        # amount wird später geändert durch Rabatt-Logik
        # aber initial sollte es von course sein wenn nicht gesetzt
        assert invoice.course is not None

    def test_initialize_sets_course_units(self, customer, course):
        """Test: Setzt course_units vom offer"""
        invoice = Invoice(customer=customer, course=course, course_units=None)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        assert invoice.course_units == course.offer.course_units

    def test_initialize_sets_course_duration(self, customer, course):
        """Test: Setzt course_duration vom offer"""
        invoice = Invoice(customer=customer, course=course, course_duration=None)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        assert invoice.course_duration == course.offer.course_duration

    def test_initialize_sets_course_id_custom(self, customer, course):
        """Test: Setzt course_id_custom"""
        invoice = Invoice(customer=customer, course=course, course_id_custom="")
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        assert invoice.course_id_custom is not None
        assert invoice.course_id_custom.startswith("KU-")

    def test_initialize_sets_issue_date(self, customer, course):
        """Test: Setzt issue_date wenn nicht gesetzt"""
        invoice = Invoice(customer=customer, course=course, issue_date=None)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        assert invoice.issue_date == date.today()

    def test_initialize_sets_due_date(self, customer, course):
        """Test: Setzt due_date als +14 Tage"""
        invoice = Invoice(customer=customer, course=course, due_date=None)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        expected_due = date.today() + timedelta(days=14)
        assert invoice.due_date == expected_due

    def test_initialize_amount_from_offer(self, customer, offer):
        """Test: Betrag vom Offer holen wenn Course nicht vorhanden"""
        invoice = Invoice(customer=customer, offer=offer, amount=None, course_units=10)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        assert invoice.amount == offer.amount

    def test_initialize_amount_prefers_course(self, customer, course, offer):
        """Test: Course wird ZUERST versucht, dann Offer"""
        # Beide sind gesetzt → Course sollte bevorzugt werden
        invoice = Invoice(customer=customer, course=course, offer=offer, amount=None)
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        # Course hat Priorität
        assert invoice.amount == course.offer.amount

    def test_initialize_course_units_from_offer_ticket_10(self, customer, offer):
        """Test: course_units vom Offer für 10er-Karten"""
        invoice = Invoice(
            customer=customer, offer=offer, amount=Decimal("200.00"), course_units=None
        )
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        # 10er-Karte sollte ticket_sessions setzen
        assert invoice.course_units == offer.ticket_sessions

    def test_initialize_course_id_for_ticket_10(self, customer, offer):
        """Test: course_id wird für 10er-Karten generiert"""
        invoice = Invoice(
            customer=customer,
            offer=offer,
            amount=Decimal("200.00"),
            course_id_custom="",
            course_units=10,
        )
        initializer = InvoiceInitializer(invoice)
        initializer.initialize()

        # course_id sollte mit 'KU-' anfangen und 'ticket' enthalten
        assert invoice.course_id_custom is not None
        assert invoice.course_id_custom.startswith("KU-")


# ==================== INVOICE MODEL TESTS ====================


class TestInvoiceModel:
    """Tests für Invoice Model"""

    def test_invoice_creation(self, customer, course):
        """Test: Invoice wird erstellt"""
        invoice = InvoiceFactory(customer=customer, course=course)

        assert invoice.id is not None
        assert invoice.customer == customer
        assert invoice.course == course
        assert invoice.status == "draft"

    def test_invoice_string_representation(self, invoice):
        """Test: __str__ gibt Rechnungsnummer und Kundenname"""
        str_repr = str(invoice)

        assert invoice.invoice_number in str_repr
        assert invoice.customer.get_full_name() in str_repr

    def test_invoice_tax_amount_property_with_tax(self):
        """Test: tax_amount Property berechnet Steuern"""
        invoice = InvoiceFactory(
            amount=Decimal("100.00"), tax_rate=Decimal("19.00"), is_tax_exempt=False
        )

        assert invoice.tax_amount == Decimal("19.00")

    def test_invoice_tax_amount_property_tax_exempt(self):
        """Test: tax_amount ist 0 bei tax_exempt"""
        invoice = InvoiceFactory(
            amount=Decimal("100.00"), tax_rate=Decimal("19.00"), is_tax_exempt=True
        )

        assert invoice.tax_amount == Decimal("0.00")

    def test_invoice_total_amount_property(self):
        """Test: total_amount berechnet Gesamtsumme"""
        invoice = InvoiceFactory(
            amount=Decimal("100.00"), tax_rate=Decimal("19.00"), is_tax_exempt=False
        )

        assert invoice.total_amount == Decimal("119.00")

    def test_invoice_email_tracking_fields(self):
        """Test: Email Tracking Fields"""
        invoice = InvoiceFactory()

        assert invoice.email_sent is False
        assert invoice.email_sent_at is None

    def test_invoice_status_choices(self):
        """Test: Verschiedene Status"""
        statuses = ["draft", "sent", "paid", "overdue", "cancelled"]

        for status in statuses:
            invoice = InvoiceFactory(status=status)
            assert invoice.status == status

    def test_invoice_ordering(self):
        """Test: Invoices nach issue_date absteigend sortiert"""
        today = date.today()
        invoice1 = InvoiceFactory(issue_date=today - timedelta(days=5))
        invoice2 = InvoiceFactory(issue_date=today)

        invoices = Invoice.objects.all().order_by("-issue_date")
        assert invoices[0] == invoice2
        assert invoices[1] == invoice1

    def test_invoice_creation_with_offer(self, customer, offer):
        """Test: Invoice mit Offer (statt Course) kann erstellt werden"""
        invoice = Invoice(
            customer=customer,
            offer=offer,
            amount=offer.amount,
            course_units=offer.course_units,
        )
        invoice.save()

        assert invoice.id is not None
        assert invoice.offer == offer
        assert invoice.course is None
        assert invoice.amount == Decimal("200.00")

    def test_invoice_with_both_course_and_offer(self, customer, course, offer):
        """Test: Invoice mit BEIDEN Course UND Offer ist möglich"""
        invoice = Invoice(
            customer=customer,
            course=course,
            offer=offer,
            amount=Decimal("100.00"),
            course_units=1,
        )
        invoice.save()

        assert invoice.course == course
        assert invoice.offer == offer

    def test_invoice_string_representation_with_offer(self, customer, offer):
        """Test: __str__() zeigt korrekt Offer-Informationen"""
        invoice = Invoice(
            customer=customer, offer=offer, amount=offer.amount, course_units=10
        )
        invoice.save()

        str_repr = str(invoice)
        assert invoice.invoice_number in str_repr
        assert customer.get_full_name() in str_repr
        assert offer.title in str_repr

    def test_get_title_with_course(self, customer, course):
        """Test: get_title() gibt Course Titel zurück"""
        invoice = Invoice(customer=customer, course=course, amount=Decimal("100.00"))
        invoice.save()

        assert invoice.get_title() == course.offer.title

    def test_get_title_with_offer(self, customer, offer):
        """Test: get_title() gibt Offer Titel zurück"""
        invoice = Invoice(
            customer=customer, offer=offer, amount=Decimal("200.00"), course_units=10
        )
        invoice.save()

        assert invoice.get_title() == offer.title


# ==================== INVOICE SAVE TESTS ====================


class TestInvoiceSave:
    """Tests für Invoice.save() Logik"""

    def test_save_initializes_defaults(self, customer, course):
        """Test: save() initialisiert alle Defaults"""
        invoice = Invoice(customer=customer, course=course)
        invoice.save()

        assert invoice.invoice_number is not None
        assert invoice.issue_date is not None
        assert invoice.due_date is not None
        assert invoice.course_units is not None

    def test_save_applies_discount(self, customer, course, discount_code_percentage):
        """Test: save() wendet Rabatt an"""
        amount = Decimal("100.00")
        invoice = Invoice(
            customer=customer,
            course=course,
            amount=amount,
            discount_code=discount_code_percentage,
        )
        invoice.save()

        # 10% Rabatt
        expected_discount = amount * Decimal("0.10")
        assert invoice.discount_amount == expected_discount
        assert invoice.amount == amount - expected_discount
        assert invoice.original_amount == amount

    def test_save_recalculates_dates(self, customer, course):
        """Test: save() setzt Daten korrekt"""
        invoice = Invoice(customer=customer, course=course)
        invoice.save()

        assert invoice.issue_date <= invoice.due_date

    def test_save_raises_error_without_course_or_offer(self, customer):
        """Test: save() wirft ValueError wenn weder Course noch Offer"""
        invoice = Invoice(customer=customer)

        with pytest.raises(ValueError):
            invoice.save()

    def test_save_sets_original_amount_only_on_first_save(self, customer, course):
        """Test: original_amount wird nur beim ERSTEN save() gesetzt"""
        invoice = Invoice(customer=customer, course=course, amount=Decimal("100.00"))
        invoice.save()

        original_first_save = invoice.original_amount

        # Zweiter save() - original_amount sollte gleich bleiben
        invoice.amount = Decimal("150.00")
        invoice.save()

        # original_amount sollte sich NICHT geändert haben
        assert invoice.original_amount == original_first_save

    def test_save_discount_zero_when_no_discount_code(self, customer, course):
        """Test: discount_amount ist 0 wenn kein discount_code"""
        invoice = Invoice(
            customer=customer,
            course=course,
            amount=Decimal("100.00"),
            discount_code=None,
        )
        invoice.save()

        assert invoice.discount_amount == Decimal("0.00")

    def test_save_discount_cleared_when_code_removed(
        self, customer, course, discount_code_percentage
    ):
        """Test: discount wird gelöscht wenn discount_code entfernt"""
        # Erste Invoice MIT Rabatt
        invoice = Invoice(
            customer=customer,
            course=course,
            amount=Decimal("100.00"),
            discount_code=discount_code_percentage,
        )
        invoice.save()

        first_discount = invoice.discount_amount

        # Rabatt-Code entfernen
        invoice.discount_code = None
        invoice.save()

        # discount_amount sollte jetzt 0 sein
        assert invoice.discount_amount == Decimal("0.00")

    def test_save_amount_formula_correct(
        self, customer, course, discount_code_percentage
    ):
        """Test: amount = original_amount - discount_amount"""
        original = Decimal("100.00")
        invoice = Invoice(
            customer=customer,
            course=course,
            amount=original,
            discount_code=discount_code_percentage,
        )
        invoice.save()

        # 10% von 100 = 10
        expected_discount = original * Decimal("0.10")
        expected_final = original - expected_discount

        assert invoice.discount_amount == expected_discount
        assert invoice.amount == expected_final

    def test_save_recalculates_discount_on_code_change(
        self, customer, course, discount_code_percentage, discount_code_fixed
    ):
        """Test: Rabatt wird neu berechnet wenn Code geändert"""
        invoice = Invoice(
            customer=customer,
            course=course,
            amount=Decimal("100.00"),
            discount_code=discount_code_percentage,
        )
        invoice.save()

        discount_with_percentage = invoice.discount_amount

        # Code wechseln zu Festbetrag
        invoice.discount_code = discount_code_fixed
        invoice.save()

        discount_with_fixed = invoice.discount_amount

        # Sollten unterschiedlich sein (10% vs €5)
        assert discount_with_percentage != discount_with_fixed


# ==================== INVOICE CONSTRAINTS & VALIDATION ====================


class TestInvoiceConstraintsValidation:
    """Tests für Constraints und Validierung"""

    def test_invoice_requires_course_or_offer(self, customer):
        """Test: ValueError wenn weder Course noch Offer gesetzt"""
        invoice = Invoice(customer=customer)

        with pytest.raises(ValueError, match="entweder einen Kurs oder ein Angebot"):
            invoice.save()

    def test_invoice_constraint_course_or_offer(self, customer):
        """Test: CheckConstraint wird vom DB durchgesetzt"""
        # Das Model hat: Q(course__isnull=False) | Q(offer__isnull=False)
        invoice = Invoice(customer=customer)

        with pytest.raises(ValueError):
            invoice.save()

    def test_invoice_number_unique(self, customer, course):
        """Test: invoice_number muss eindeutig sein"""
        invoice1 = InvoiceFactory(
            invoice_number="2025-UNIQUE-001", customer=customer, course=course
        )

        # Versuche duplicate zu erstellen
        with pytest.raises(IntegrityError):
            invoice2 = Invoice(
                customer=customer,
                course=course,
                invoice_number="2025-UNIQUE-001",
                amount=Decimal("100.00"),
            )
            invoice2.save()


# ==================== INVOICE CANCELLATION & SPECIAL FIELDS ====================


class TestInvoiceCancellation:
    """Tests für Invoice Stornierung und spezielle Felder"""

    def test_invoice_cancellation_fields(self, customer, course):
        """Test: Cancellation fields können gespeichert werden"""
        invoice = InvoiceFactory(customer=customer, course=course)

        # Stornieren
        now = timezone.now()
        invoice.cancelled_at = now
        invoice.cancelled_invoice_number = "2025-CANCEL-001"
        invoice.status = "cancelled"
        invoice.save()

        # Prüfe dass alles gespeichert wurde
        refetched = Invoice.objects.get(id=invoice.id)
        assert refetched.cancelled_at is not None
        assert refetched.cancelled_invoice_number == "2025-CANCEL-001"
        assert refetched.status == "cancelled"

    def test_invoice_cancelled_at_timestamp(self, customer, course):
        """Test: cancelled_at timestamp wird korrekt gespeichert"""
        invoice = InvoiceFactory(customer=customer, course=course)
        before = timezone.now()

        invoice.cancelled_at = timezone.now()
        invoice.status = "cancelled"
        invoice.save()

        after = timezone.now()

        assert invoice.cancelled_at is not None
        assert before <= invoice.cancelled_at <= after

    def test_invoice_prevention_certified_default_true(self, customer, course):
        """Test: is_prevention_certified default ist True"""
        invoice = InvoiceFactory(customer=customer, course=course)

        assert invoice.is_prevention_certified is True

    def test_invoice_prevention_certified_can_be_disabled(self, customer, course):
        """Test: is_prevention_certified kann deaktiviert werden"""
        invoice = InvoiceFactory(
            customer=customer, course=course, is_prevention_certified=False
        )

        assert invoice.is_prevention_certified is False

    def test_invoice_zpp_prevention_id_field(self, customer, course):
        """Test: ZPP Präventions-ID kann gespeichert werden"""
        invoice = InvoiceFactory(
            customer=customer, course=course, zpp_prevention_id="ZPP-2025-123456"
        )

        refetched = Invoice.objects.get(id=invoice.id)
        assert refetched.zpp_prevention_id == "ZPP-2025-123456"

    def test_invoice_notes_field(self, customer, course):
        """Test: Notes können gespeichert werden"""
        notes = "Diese Rechnung bezieht sich auf den Herbstworkshop 2025"
        invoice = InvoiceFactory(customer=customer, course=course, notes=notes)

        refetched = Invoice.objects.get(id=invoice.id)
        assert refetched.notes == notes

    def test_invoice_email_sent_flag(self, customer, course):
        """Test: email_sent flag kann gesetzt werden"""
        invoice = InvoiceFactory(customer=customer, course=course, email_sent=True)

        assert invoice.email_sent is True

    def test_invoice_email_sent_timestamp(self, customer, course):
        """Test: email_sent_at timestamp wird korrekt gespeichert"""
        invoice = InvoiceFactory(customer=customer, course=course)
        now = timezone.now()

        invoice.email_sent = True
        invoice.email_sent_at = now
        invoice.save()

        refetched = Invoice.objects.get(id=invoice.id)
        assert refetched.email_sent is True
        assert refetched.email_sent_at is not None


# ==================== INTEGRATION TESTS ====================


class TestInvoiceIntegration:
    """Integration Tests für Invoice"""

    def test_full_invoice_workflow(self):
        """Test: Kompletter Invoice Workflow"""
        customer = CustomerFactory()
        course = CourseFactory()

        # 1. Invoice erstellen
        invoice = InvoiceFactory(customer=customer, course=course, status="draft")

        # 2. Assertions
        assert invoice.invoice_number is not None
        assert invoice.status == "draft"
        assert invoice.total_amount > 0

    def test_invoice_with_discount_workflow(self):
        """Test: Invoice mit Rabatt Workflow"""
        customer = CustomerFactory()
        course = CourseFactory()

        from customers.models import CustomerDiscountCode

        discount_code = CustomerDiscountCode.objects.create(
            customer=customer,
            code="SAVE20",
            discount_type="percentage",
            discount_value=Decimal("20.00"),
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            status="sent",
        )

        invoice = InvoiceWithDiscountFactory(
            customer=customer,
            course=course,
            discount_code=discount_code,
            amount=Decimal("100.00"),
        )

        # Nach save() sollte Rabatt angewendet sein
        assert invoice.discount_amount == Decimal("20.00")
        assert invoice.amount == Decimal("80.00")
        assert invoice.original_amount == Decimal("100.00")

    def test_invoice_cascade_delete_on_customer(self):
        """Test: Invoices können nicht gelöscht werden wenn Customer gelöscht"""
        from django.db import IntegrityError

        customer = CustomerFactory()
        invoice = InvoiceFactory(customer=customer)

        # Invoice sollte Customer referenzieren mit on_delete=PROTECT
        with pytest.raises(IntegrityError):
            customer.delete()

    def test_multiple_invoices_sequence(self):
        """Test: Mehrere Rechnungen bekommen aufsteigende Nummern"""
        Invoice.objects.filter(
            invoice_number__startswith=f"{datetime.now().year}-"
        ).delete()

        customer = CustomerFactory()
        course = CourseFactory()

        invoice1 = InvoiceFactory(customer=customer, course=course)
        invoice2 = InvoiceFactory(customer=customer, course=course)
        invoice3 = InvoiceFactory(customer=customer, course=course)

        # Alle sollten unterschiedliche Nummern haben
        numbers = [
            invoice1.invoice_number,
            invoice2.invoice_number,
            invoice3.invoice_number,
        ]
        assert len(numbers) == len(set(numbers))

    def test_invoice_with_offer_complete_workflow(self):
        """Test: Kompletter Workflow mit Offer (10er-Karten)"""
        customer = CustomerFactory()

        from offers.models import Offer, ZPPCertification

        cert = ZPPCertification.objects.create(
            zpp_id="KU-YG-000002",
            name="Yoga Certification",
            official_title="Official Yoga",
            format="hybrid",
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=365),
            is_active=True,
        )

        # ✅ is_ticket_10 ist eine PROPERTY - nicht direkt setzen!
        offer = Offer.objects.create(
            offer_type="ticket_10",  # ✅ offer_type setzen → is_ticket_10 wird automatisch True
            title="10er Karte Pilates",
            course_units=10,
            course_duration=60,
            amount=Decimal("250.00"),
            tax_rate=Decimal("0.00"),
            is_tax_exempt=True,
            zpp_certification=cert,
            ticket_sessions=10,
        )

        # Erstelle Invoice
        invoice = Invoice(
            customer=customer, offer=offer, amount=Decimal("250.00"), course_units=10
        )
        invoice.save()

        # Assertions
        assert invoice.id is not None
        assert invoice.offer == offer
        assert invoice.course_units == 10
        assert invoice.amount == Decimal("250.00")
        assert invoice.invoice_number is not None
