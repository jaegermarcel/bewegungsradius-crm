"""
customers/tests/test_models.py - Verbesserte Tests für Customer, ContactChannel und CustomerDiscountCode Models
===============================================================================================================
✅ Customer Model Tests (erweitert)
✅ ContactChannel Model Tests (NEU)
✅ CustomerDiscountCode Model Tests (verbessert)
✅ Discount Calculation Tests (optimiert)
✅ Validation Tests
✅ Integration Tests (erweitert)
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.db import IntegrityError
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ==================== IMPORTS ====================

from customers.models import ContactChannel, Customer, CustomerDiscountCode
from tests.factories import (
    ActiveDiscountCodeFactory,
    CourseFactory,
    CustomerDiscountCodeFactory,
    CustomerFactory,
)

# ==================== FIXTURES ====================


@pytest.fixture
def customer(db):
    """Customer Fixture"""
    return CustomerFactory()


@pytest.fixture
def contact_channel(db):
    """ContactChannel Fixture"""
    return ContactChannel.objects.create(
        name="Webseite",
        slug="website",
        description="Kontakt via Webseite",
        is_active=True,
    )


@pytest.fixture
def contact_channels(db):
    """Multiple ContactChannels Fixture"""
    channels = []
    channel_data = [
        ("Kikudoo", "kikudoo"),
        ("Webseite", "website"),
        ("Telefon", "phone"),
        ("E-Mail", "email"),
        ("WhatsApp", "whatsapp"),
        ("Instagram", "instagram"),
    ]

    for name, slug in channel_data:
        channels.append(
            ContactChannel.objects.create(name=name, slug=slug, is_active=True)
        )

    return channels


@pytest.fixture
def planned_discount_code(db, customer):
    """Planned Discount Code Fixture"""
    return CustomerDiscountCode.objects.create(
        customer=customer,
        code="PLANNED_TEST",
        discount_type="percentage",
        discount_value=Decimal("10.00"),
        status="planned",
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=30),
    )


@pytest.fixture
def active_discount_code(db, customer):
    """Active Discount Code Fixture"""
    return ActiveDiscountCodeFactory(customer=customer)


@pytest.fixture
def user(db):
    """User Fixture für created_by"""
    return User.objects.create_user(
        username="testadmin", email="admin@example.com", password="test123456"
    )


@pytest.fixture
def course(db):
    """Course Fixture"""
    return CourseFactory()


# ==================== CONTACT CHANNEL MODEL TESTS ====================


class TestContactChannelModel:
    """Tests für ContactChannel Model"""

    def test_contact_channel_creation(self):
        """Test: ContactChannel wird erstellt"""
        channel = ContactChannel.objects.create(
            name="Webseite", slug="website", description="Kontakt via Webseite"
        )

        assert channel.id is not None
        assert channel.name == "Webseite"
        assert channel.slug == "website"
        assert channel.is_active is True

    def test_contact_channel_slug_unique(self):
        """Test: Slug muss unique sein"""
        ContactChannel.objects.create(name="Webseite", slug="website")

        with pytest.raises(IntegrityError):
            ContactChannel.objects.create(name="Andere Webseite", slug="website")

    def test_contact_channel_string_representation(self, contact_channel):
        """Test: __str__ gibt Namen zurück"""
        assert str(contact_channel) == "Webseite"

    def test_contact_channel_is_active_default(self):
        """Test: is_active ist default True"""
        channel = ContactChannel.objects.create(name="Telefon", slug="phone")
        assert channel.is_active is True

    def test_contact_channel_is_active_false(self):
        """Test: ContactChannel kann deaktiviert werden"""
        channel = ContactChannel.objects.create(
            name="Telefon", slug="phone", is_active=False
        )
        assert channel.is_active is False

    def test_contact_channel_description_optional(self):
        """Test: Beschreibung ist optional"""
        channel = ContactChannel.objects.create(name="Telefon", slug="phone")
        assert channel.description == ""

    def test_contact_channel_timestamps_set(self):
        """Test: Timestamps werden automatisch gesetzt"""
        before = timezone.now()
        channel = ContactChannel.objects.create(name="E-Mail", slug="email")
        after = timezone.now()

        assert before <= channel.created_at <= after
        assert before <= channel.updated_at <= after

    def test_contact_channel_ordering_by_name(self, contact_channels):
        """Test: ContactChannels sind nach Name sortiert"""
        channels = ContactChannel.objects.all()
        names = [ch.name for ch in channels]

        assert names == sorted(names)

    def test_contact_channel_update_timestamp(self, contact_channel):
        """Test: updated_at wird aktualisiert"""
        original_updated_at = contact_channel.updated_at

        contact_channel.name = "Neue Webseite"
        contact_channel.save()

        assert contact_channel.updated_at >= original_updated_at


# ==================== CUSTOMER MODEL TESTS ====================


class TestCustomerModel:
    """Tests für Customer Model"""

    def test_customer_creation(self):
        """Test: Customer wird erstellt"""
        customer = CustomerFactory(
            first_name="Max", last_name="Mustermann", email="max@example.com"
        )

        assert customer.id is not None
        assert customer.first_name == "Max"
        assert customer.last_name == "Mustermann"
        assert customer.email == "max@example.com"

    def test_customer_email_unique(self):
        """Test: Email muss unique sein"""
        CustomerFactory(email="test@example.com")

        with pytest.raises(IntegrityError):
            CustomerFactory(email="test@example.com")

    def test_customer_with_contact_channel(self, customer, contact_channel):
        """Test: Customer mit ContactChannel"""
        customer.contact_channel = contact_channel
        customer.save()

        assert customer.contact_channel == contact_channel
        assert contact_channel.customers.count() == 1

    def test_customer_contact_channel_set_null_on_delete(
        self, customer, contact_channel
    ):
        """Test: ContactChannel wird auf NULL gesetzt wenn gelöscht"""
        customer.contact_channel = contact_channel
        customer.save()

        contact_channel.delete()
        customer.refresh_from_db()

        assert customer.contact_channel is None

    def test_customer_get_full_name(self, customer):
        """Test: get_full_name() kombiniert Vor- und Nachname"""
        full_name = customer.get_full_name()
        assert full_name == f"{customer.first_name} {customer.last_name}"

    def test_customer_string_representation(self, customer):
        """Test: __str__ gibt vollständigen Namen zurück"""
        assert str(customer) == customer.get_full_name()

    def test_customer_get_full_address(self):
        """Test: get_full_address() kombiniert Adressfelder"""
        customer = CustomerFactory(
            street="Hauptstraße",
            house_number="42",
            postal_code="80801",
            city="München",
            country="Deutschland",
        )

        full_address = customer.get_full_address()
        assert "Hauptstraße 42" in full_address
        assert "80801 München" in full_address
        assert "Deutschland" in full_address

    def test_customer_get_full_address_partial(self):
        """Test: get_full_address() mit unvollständiger Adresse"""
        customer = CustomerFactory(
            street="Hauptstraße",
            house_number="",
            postal_code="80801",
            city="München",
            country="",
        )

        full_address = customer.get_full_address()
        assert "Hauptstraße" in full_address
        assert "80801 München" in full_address

    def test_customer_get_full_address_minimal(self):
        """Test: get_full_address() mit minimalen Daten"""
        customer = CustomerFactory(
            street="", house_number="", postal_code="", city="München"
        )

        full_address = customer.get_full_address()
        assert full_address == "München, Deutschland"

    def test_customer_birthday_optional(self):
        """Test: Geburtstag ist optional"""
        customer = CustomerFactory(birthday=None)
        assert customer.birthday is None

    def test_customer_mobile_optional(self):
        """Test: Mobil ist optional"""
        customer = CustomerFactory(mobile="")
        assert customer.mobile == ""

    def test_customer_is_active_default_true(self):
        """Test: is_active ist default True"""
        customer = CustomerFactory()
        assert customer.is_active is True

    def test_customer_archived_at_null_by_default(self):
        """Test: archived_at ist null wenn aktiv"""
        customer = CustomerFactory()
        assert customer.archived_at is None

    def test_customer_can_be_archived(self, customer):
        """Test: Customer kann archiviert werden"""
        assert customer.archived_at is None

        customer.is_active = False
        customer.archived_at = timezone.now()
        customer.save()

        assert customer.is_active is False
        assert customer.archived_at is not None

    def test_customer_coordinates_optional(self):
        """Test: Koordinaten sind optional"""
        customer = CustomerFactory(coordinates=None)
        assert customer.coordinates is None

    def test_customer_created_at_auto_set(self):
        """Test: created_at wird automatisch gesetzt"""
        before = timezone.now()
        customer = CustomerFactory()
        after = timezone.now()

        assert before <= customer.created_at <= after

    def test_customer_updated_at_auto_set(self):
        """Test: updated_at wird automatisch gesetzt"""
        before = timezone.now()
        customer = CustomerFactory()
        after = timezone.now()

        assert before <= customer.updated_at <= after

    def test_customer_country_default_deutschland(self):
        """Test: Land ist default Deutschland"""
        customer = CustomerFactory()
        assert customer.country == "Deutschland"

    def test_customer_notes_optional(self):
        """Test: Notizen sind optional"""
        customer = CustomerFactory(notes="")
        assert customer.notes == ""

    def test_customer_notes_with_content(self, customer):
        """Test: Customer mit Notizen"""
        notes = "Wichtiger Kunde, besondere Anforderungen"
        customer.notes = notes
        customer.save()

        assert customer.notes == notes

    @patch("customers.models.AddressGeocoder")
    def test_customer_geocoding_on_save(self, mock_geocoder_class):
        """Test: Geocoding wird aufgerufen wenn nötig"""
        mock_geocoder = MagicMock()
        mock_geocoder_class.return_value = mock_geocoder
        mock_geocoder.geocode.return_value = None

        customer = CustomerFactory(
            street="Hauptstraße", house_number="42", city="München", coordinates=None
        )

        mock_geocoder_class.assert_called()
        mock_geocoder.geocode.assert_called()

    @patch("customers.models.AddressGeocoder")
    def test_customer_no_geocoding_if_coordinates_exist(self, mock_geocoder_class):
        mock_geocoder = MagicMock()
        mock_geocoder_class.return_value = mock_geocoder
        mock_geocoder.geocode.return_value = None  # ← KEY!

        customer = CustomerFactory(
            street="Hauptstraße",
            house_number="42",
            city="München",
            coordinates=Point(13.405, 52.52),
        )
        mock_geocoder.geocode.assert_not_called()
        assert customer.coordinates.x == 13.405

    @patch("customers.models.AddressGeocoder")
    def test_customer_no_geocoding_without_address(self, mock_geocoder_class):
        """Test: Kein Geocoding ohne Straße oder Stadt"""
        mock_geocoder = MagicMock()
        mock_geocoder_class.return_value = mock_geocoder

        customer = CustomerFactory(street="", city="")

        mock_geocoder.geocode.assert_not_called()

    def test_customer_ordering_by_created_at_desc(self):
        """Test: Customers sind nach created_at absteigend sortiert"""
        customer1 = CustomerFactory()
        customer2 = CustomerFactory()

        customers = Customer.objects.all()
        assert customers[0] == customer2
        assert customers[1] == customer1

    def test_customer_related_name_discount_codes(self, customer):
        """Test: Zugriff auf discount_codes über related_name"""
        code1 = CustomerDiscountCodeFactory(customer=customer)
        code2 = CustomerDiscountCodeFactory(customer=customer)

        assert customer.discount_codes.count() == 2
        assert code1 in customer.discount_codes.all()
        assert code2 in customer.discount_codes.all()

    def test_customer_related_name_contact_channel(self, customer, contact_channel):
        """Test: Zugriff auf customers über ContactChannel"""
        customer.contact_channel = contact_channel
        customer.save()

        assert customer in contact_channel.customers.all()


# ==================== CUSTOMER DISCOUNT CODE MODEL TESTS ====================


class TestCustomerDiscountCodeModel:
    """Tests für CustomerDiscountCode Model"""

    def test_discount_code_creation(self, customer):
        """Test: Discount Code wird erstellt"""
        code = CustomerDiscountCodeFactory(
            customer=customer,
            code="SAVE10",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
        )

        assert code.id is not None
        assert code.customer == customer
        assert code.code == "SAVE10"
        assert code.discount_type == "percentage"

    def test_discount_code_code_unique(self, customer):
        """Test: Code muss unique sein"""
        CustomerDiscountCodeFactory(customer=customer, code="UNIQUE123")

        with pytest.raises(IntegrityError):
            CustomerDiscountCodeFactory(code="UNIQUE123")

    def test_discount_code_string_representation(self, customer):
        """Test: __str__ gibt Code und Kundenname"""
        code = CustomerDiscountCodeFactory(customer=customer)
        str_repr = str(code)

        assert code.code in str_repr
        assert customer.get_full_name() in str_repr

    def test_discount_code_discount_type_percentage(self, customer):
        """Test: Discount Type Percentage"""
        code = CustomerDiscountCodeFactory(
            customer=customer,
            discount_type="percentage",
            discount_value=Decimal("15.00"),
        )

        assert code.discount_type == "percentage"
        assert code.discount_value == Decimal("15.00")

    def test_discount_code_discount_type_fixed(self, customer):
        """Test: Discount Type Fixed Amount"""
        code = CustomerDiscountCodeFactory(
            customer=customer, discount_type="fixed", discount_value=Decimal("25.00")
        )

        assert code.discount_type == "fixed"
        assert code.discount_value == Decimal("25.00")

    def test_discount_code_reason_choices(self, customer):
        """Test: Verschiedene Gründe für Rabatt"""
        reasons = ["birthday", "course_completed", "referral", "loyalty", "other"]

        for reason in reasons:
            code = CustomerDiscountCodeFactory(customer=customer, reason=reason)
            assert code.reason == reason

    def test_discount_code_status_planned_default(self, customer):
        """Test: Status ist default 'planned'"""
        code = CustomerDiscountCode.objects.create(
            customer=customer,
            code="TEST123",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
            valid_until=date.today() + timedelta(days=30),
        )
        assert code.status == "planned"

    def test_discount_code_status_choices(self, customer):
        """Test: Verschiedene Statuse"""
        statuses = ["planned", "sent", "used", "expired", "cancelled"]

        for status in statuses:
            code = CustomerDiscountCodeFactory(customer=customer, status=status)
            assert code.status == status

    def test_discount_code_valid_from_defaults_today(self, customer):
        """Test: valid_from ist default heute"""
        code = CustomerDiscountCode.objects.create(
            customer=customer,
            code="TEST_VALID",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
            valid_until=date.today() + timedelta(days=30),
        )
        assert code.valid_from == date.today()

    def test_discount_code_timestamps_set(self, customer):
        """Test: Timestamps werden automatisch gesetzt"""
        before = timezone.now()
        code = CustomerDiscountCodeFactory(customer=customer)
        after = timezone.now()

        assert before <= code.created_at <= after

    def test_discount_code_created_by_optional(self, customer):
        """Test: created_by ist optional"""
        code = CustomerDiscountCodeFactory(customer=customer, created_by=None)
        assert code.created_by is None

    def test_discount_code_with_creator(self, customer, user):
        """Test: Discount Code mit Creator"""
        code = CustomerDiscountCodeFactory(customer=customer, created_by=user)
        assert code.created_by == user

    def test_discount_code_course_optional(self, customer):
        """Test: Course ist optional"""
        code = CustomerDiscountCodeFactory(customer=customer, course=None)
        assert code.course is None

    def test_discount_code_with_course(self, customer, course):
        """Test: Discount Code mit speziischem Kurs"""
        code = CustomerDiscountCodeFactory(customer=customer, course=course)
        assert code.course == course

    def test_discount_code_description_optional(self, customer):
        """Test: Beschreibung ist optional"""
        code = CustomerDiscountCodeFactory(customer=customer, description="")
        assert code.description == ""

    def test_discount_code_description_with_content(self, customer):
        """Test: Discount Code mit Beschreibung"""
        description = "Spezial Rabatt für Treuekundin"
        code = CustomerDiscountCodeFactory(customer=customer, description=description)
        assert code.description == description

    def test_discount_code_email_sent_at_optional(self, customer):
        """Test: email_sent_at ist optional"""
        code = CustomerDiscountCodeFactory(customer=customer)
        assert code.email_sent_at is None

    def test_discount_code_used_at_optional(self, customer):
        """Test: used_at ist optional"""
        code = CustomerDiscountCodeFactory(customer=customer)
        assert code.used_at is None

    def test_discount_code_cancelled_fields_optional(self, customer):
        """Test: Cancelled-Felder sind optional"""
        code = CustomerDiscountCodeFactory(customer=customer)
        assert code.cancelled_at is None
        assert code.cancelled_reason == ""


# ==================== DISCOUNT CODE CALCULATION TESTS ====================


class TestDiscountCodeCalculation:
    """Tests für Discount Berechnungen"""

    def test_calculate_discount_percentage(self, customer):
        """Test: Rabatt-Berechnung Prozent"""
        code = CustomerDiscountCodeFactory(
            customer=customer,
            discount_type="percentage",
            discount_value=Decimal("20.00"),
        )

        discount = code.calculate_discount(Decimal("100.00"))
        assert discount == Decimal("20.00")

    def test_calculate_discount_percentage_decimal(self, customer):
        """Test: Rabatt-Berechnung Prozent mit Dezimalzahlen"""
        code = CustomerDiscountCodeFactory(
            customer=customer,
            discount_type="percentage",
            discount_value=Decimal("15.50"),
        )

        discount = code.calculate_discount(Decimal("200.00"))
        assert discount == Decimal("31.00")

    def test_calculate_discount_percentage_zero(self, customer):
        """Test: Rabatt-Berechnung mit 0%"""
        code = CustomerDiscountCodeFactory(
            customer=customer,
            discount_type="percentage",
            discount_value=Decimal("0.00"),
        )

        discount = code.calculate_discount(Decimal("100.00"))
        assert discount == Decimal("0.00")

    def test_calculate_discount_percentage_hundred(self, customer):
        """Test: Rabatt-Berechnung mit 100%"""
        code = CustomerDiscountCodeFactory(
            customer=customer,
            discount_type="percentage",
            discount_value=Decimal("100.00"),
        )

        discount = code.calculate_discount(Decimal("100.00"))
        assert discount == Decimal("100.00")

    def test_calculate_discount_fixed(self, customer):
        """Test: Rabatt-Berechnung fester Betrag"""
        code = CustomerDiscountCodeFactory(
            customer=customer, discount_type="fixed", discount_value=Decimal("25.00")
        )

        discount = code.calculate_discount(Decimal("100.00"))
        assert discount == Decimal("25.00")

    def test_calculate_discount_fixed_cap_at_amount(self, customer):
        """Test: Fester Rabatt kann nicht größer als Betrag sein"""
        code = CustomerDiscountCodeFactory(
            customer=customer, discount_type="fixed", discount_value=Decimal("100.00")
        )

        discount = code.calculate_discount(Decimal("50.00"))
        assert discount == Decimal("50.00")

    def test_calculate_discount_fixed_zero(self, customer):
        """Test: Rabatt-Berechnung mit 0€"""
        code = CustomerDiscountCodeFactory(
            customer=customer, discount_type="fixed", discount_value=Decimal("0.00")
        )

        discount = code.calculate_discount(Decimal("100.00"))
        assert discount == Decimal("0.00")

    def test_get_discount_display_percentage(self, customer):
        """Test: Formatierte Rabattanzeige Prozent"""
        code = CustomerDiscountCodeFactory(
            customer=customer,
            discount_type="percentage",
            discount_value=Decimal("15.00"),
        )

        assert code.get_discount_display() == "15.00%"

    def test_get_discount_display_fixed(self, customer):
        """Test: Formatierte Rabattanzeige fester Betrag"""
        code = CustomerDiscountCodeFactory(
            customer=customer, discount_type="fixed", discount_value=Decimal("25.00")
        )

        assert code.get_discount_display() == "25.00€"

    def test_get_discount_display_decimal_percentage(self, customer):
        """Test: Formatierte Rabattanzeige mit Dezimalzahlen"""
        code = CustomerDiscountCodeFactory(
            customer=customer,
            discount_type="percentage",
            discount_value=Decimal("7.50"),
        )

        assert code.get_discount_display() == "7.50%"


# ==================== DISCOUNT CODE STATUS TESTS ====================


class TestDiscountCodeStatus:
    """Tests für Discount Code Status Management"""

    def test_get_status(self, planned_discount_code):
        """Test: get_status() gibt aktuellen Status"""
        assert planned_discount_code.get_status() == "planned"

    def test_use_code_marks_as_used(self, planned_discount_code):
        """Test: use_code() markiert als verwendet"""
        assert planned_discount_code.status == "planned"
        assert planned_discount_code.used_at is None

        planned_discount_code.use_code()

        assert planned_discount_code.status == "used"
        assert planned_discount_code.used_at is not None

    def test_use_code_sets_timestamp(self, planned_discount_code):
        """Test: use_code() setzt korrekten Zeitstempel"""
        before = timezone.now()
        planned_discount_code.use_code()
        after = timezone.now()

        assert before <= planned_discount_code.used_at <= after

    def test_use_code_persists_to_database(self, planned_discount_code):
        """Test: use_code() speichert in Datenbank"""
        code_id = planned_discount_code.id
        planned_discount_code.use_code()

        # Neue Instanz abrufen
        refreshed_code = CustomerDiscountCode.objects.get(id=code_id)
        assert refreshed_code.status == "used"
        assert refreshed_code.used_at is not None


# ==================== DISCOUNT CODE VALIDATION TESTS ====================


class TestDiscountCodeValidation:
    """Tests für Discount Code Validierung"""

    @patch("customers.models.DiscountCodeValidator")
    def test_is_valid_calls_validator(
        self, mock_validator_class, planned_discount_code
    ):
        """Test: is_valid() ruft Validator auf"""
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = True

        result = planned_discount_code.is_valid()

        mock_validator_class.assert_called_once_with(planned_discount_code)
        mock_validator.validate.assert_called_once()
        assert result is True

    @patch("customers.models.DiscountCodeValidator")
    def test_is_valid_expired_code(self, mock_validator_class, customer):
        """Test: is_valid() für abgelaufenen Code"""
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = False

        code = CustomerDiscountCodeFactory(
            customer=customer,
            status="expired",
            valid_until=date.today() - timedelta(days=1),
        )

        result = code.is_valid()
        assert result is False

    @patch("customers.models.DiscountCodeValidator")
    def test_is_valid_active_code(self, mock_validator_class, active_discount_code):
        """Test: is_valid() für aktiven Code"""
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = True

        result = active_discount_code.is_valid()
        assert result is True


# ==================== DISCOUNT CODE GENERATION TESTS ====================


class TestDiscountCodeGeneration:
    """Tests für Discount Code Generierung"""

    @patch("customers.models.DiscountCodeGenerator")
    def test_generate_course_code(self, mock_generator_class, customer, course):
        """Test: generate_course_code() ruft Generator auf"""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = "COURSE123"

        result = CustomerDiscountCode.generate_course_code(course, customer)

        mock_generator.generate.assert_called_once_with(course, customer)
        assert result == "COURSE123"


# ==================== INTEGRATION TESTS ====================


class TestCustomerIntegration:
    """Integration Tests für Customer"""

    def test_customer_with_discount_codes(self):
        """Test: Customer mit mehreren Rabattcodes"""
        customer = CustomerFactory()

        code1 = CustomerDiscountCodeFactory(customer=customer)
        code2 = CustomerDiscountCodeFactory(customer=customer)
        code3 = CustomerDiscountCodeFactory(customer=customer)

        assert customer.discount_codes.count() == 3
        assert code1 in customer.discount_codes.all()

    def test_customer_discount_code_cascade_delete(self):
        """Test: Rabattcodes werden gelöscht wenn Kunde gelöscht"""
        customer = CustomerFactory()
        code = CustomerDiscountCodeFactory(customer=customer)

        code_id = code.id
        customer.delete()

        assert not CustomerDiscountCode.objects.filter(id=code_id).exists()

    def test_customer_with_all_fields_populated(self):
        """Test: Customer mit allen Feldern ausgefüllt"""
        channel = ContactChannel.objects.create(name="Webseite", slug="website")

        customer = CustomerFactory(
            first_name="Max",
            last_name="Mustermann",
            email="max@example.com",
            mobile="+49123456789",
            birthday=date(1990, 5, 15),
            street="Hauptstraße",
            house_number="42",
            postal_code="80801",
            city="München",
            country="Deutschland",
            contact_channel=channel,
            notes="VIP Kunde",
        )

        assert customer.first_name == "Max"
        assert customer.mobile == "+49123456789"
        assert customer.contact_channel == channel
        assert customer.notes == "VIP Kunde"
        assert (
            customer.get_full_address() == "Hauptstraße 42, 80801 München, Deutschland"
        )


class TestContactChannelIntegration:
    """Integration Tests für ContactChannel"""

    def test_multiple_customers_same_channel(self, contact_channel):
        """Test: Mehrere Kunden über gleichen Kanal"""
        customer1 = CustomerFactory(contact_channel=contact_channel)
        customer2 = CustomerFactory(contact_channel=contact_channel)
        customer3 = CustomerFactory(contact_channel=contact_channel)

        assert contact_channel.customers.count() == 3

    def test_customers_by_different_channels(self, contact_channels):
        """Test: Kunden über verschiedene Kanäle"""
        customer1 = CustomerFactory(contact_channel=contact_channels[0])  # Kikudoo
        customer2 = CustomerFactory(contact_channel=contact_channels[1])  # Website
        customer3 = CustomerFactory(contact_channel=contact_channels[2])  # Telefon

        assert contact_channels[0].customers.count() == 1
        assert contact_channels[1].customers.count() == 1
        assert contact_channels[2].customers.count() == 1

    def test_customer_without_channel(self):
        """Test: Customer ohne Kontaktkanal"""
        customer = CustomerFactory(contact_channel=None)
        assert customer.contact_channel is None


class TestDiscountCodeIntegration:
    """Integration Tests für Discount Codes"""

    def test_full_discount_code_workflow(self):
        """Test: Kompletter Discount Code Workflow"""
        customer = CustomerFactory()

        # 1. Code erstellen
        code = CustomerDiscountCodeFactory(
            customer=customer,
            status="planned",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
        )

        # 2. Code ist geplant
        assert code.status == "planned"

        # 3. Code berechnen
        discount = code.calculate_discount(Decimal("100.00"))
        assert discount == Decimal("10.00")

        # 4. Code verwenden
        code.use_code()
        assert code.status == "used"
        assert code.used_at is not None

    def test_percentage_vs_fixed_discount_comparison(self, customer):
        """Test: Vergleich Prozent vs. fester Betrag"""
        amount = Decimal("200.00")

        percentage_code = CustomerDiscountCodeFactory(
            customer=customer,
            discount_type="percentage",
            discount_value=Decimal("20.00"),
        )

        fixed_code = CustomerDiscountCodeFactory(
            customer=customer, discount_type="fixed", discount_value=Decimal("30.00")
        )

        percentage_discount = percentage_code.calculate_discount(amount)
        fixed_discount = fixed_code.calculate_discount(amount)

        assert percentage_discount == Decimal("40.00")
        assert fixed_discount == Decimal("30.00")
        assert percentage_discount > fixed_discount

    def test_multiple_discount_codes_for_same_customer(self):
        """Test: Mehrere Codes für gleichen Kunden"""
        customer = CustomerFactory()
        course1 = CourseFactory()
        course2 = CourseFactory()

        general_code = CustomerDiscountCodeFactory(
            customer=customer, code="SAVE10", course=None
        )

        course1_code = CustomerDiscountCodeFactory(
            customer=customer, code="COURSE1_SAVE", course=course1
        )

        course2_code = CustomerDiscountCodeFactory(
            customer=customer, code="COURSE2_SAVE", course=course2
        )

        assert customer.discount_codes.count() == 3
        assert customer.discount_codes.filter(course=None).exists()
        assert customer.discount_codes.filter(course=course1).exists()
        assert customer.discount_codes.filter(course=course2).exists()

    def test_discount_code_with_creator_and_course(self, user, course):
        """Test: Discount Code mit Creator und Course"""
        customer = CustomerFactory()

        code = CustomerDiscountCodeFactory(
            customer=customer, course=course, created_by=user, reason="course_completed"
        )

        assert code.created_by == user
        assert code.course == course
        assert code.reason == "course_completed"


class TestComplexScenarios:
    """Tests für komplexe Szenarien"""

    def test_customer_migration_between_channels(self, contact_channels):
        """Test: Kunde wechselt Kontaktkanal"""
        customer = CustomerFactory(contact_channel=contact_channels[0])

        assert customer.contact_channel == contact_channels[0]

        customer.contact_channel = contact_channels[1]
        customer.save()

        assert customer.contact_channel == contact_channels[1]

    def test_discount_code_lifecycle_full(self, user, customer):
        """Test: Vollständiger Lebenszeyklus eines Discount Codes"""
        # 1. Erstellt
        code = CustomerDiscountCodeFactory(
            customer=customer, created_by=user, status="planned"
        )
        assert code.status == "planned"
        assert code.email_sent_at is None
        assert code.used_at is None

        # 2. Versendet
        code.status = "sent"
        code.email_sent_at = timezone.now()
        code.save()
        assert code.status == "sent"

        # 3. Verwendet
        code.use_code()
        assert code.status == "used"
        assert code.used_at is not None

    def test_bulk_customer_creation_with_channels(self, contact_channels):
        """Test: Mehrere Kunden mit Kanälen erstellen"""
        customers_data = [
            {"first_name": "Max", "contact_channel": contact_channels[0]},
            {"first_name": "Anna", "contact_channel": contact_channels[1]},
            {"first_name": "Peter", "contact_channel": contact_channels[2]},
        ]

        customers = [
            CustomerFactory(**{**data, "last_name": f"Mustermann{i}"})
            for i, data in enumerate(customers_data)
        ]

        assert len(customers) == 3
        assert customers[0].contact_channel == contact_channels[0]
        assert customers[1].contact_channel == contact_channels[1]
        assert customers[2].contact_channel == contact_channels[2]
