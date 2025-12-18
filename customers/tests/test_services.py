"""
customers/tests/test_services.py - Tests für Customer Services (CORRECTED)
================================================================
✅ AddressGeocoder Tests
✅ DiscountCodeValidator Tests (FIXED)
✅ DiscountCodeGenerator Tests (FIXED)
✅ DiscountCodeCalculator Tests
✅ DiscountCodeFormatter Tests
✅ Integration Tests
✅ Edge Case Tests
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.contrib.gis.geos import Point

pytestmark = pytest.mark.django_db


# ==================== IMPORTS ====================

from customers.services import (
    AddressGeocoder,
    DiscountCodeValidator,
    DiscountCodeGenerator,
    DiscountCodeCalculator,
    DiscountCodeFormatter,
)
from customers.models import CustomerDiscountCode
from tests.factories import (
    CustomerFactory,
    CourseFactory,
    OfferFactory,
    CustomerDiscountCodeFactory,
)


# ==================== FIXTURES ====================

@pytest.fixture
def customer(db):
    """Customer Fixture"""
    return CustomerFactory(
        first_name='Marcel',
        last_name='Jäger',
        street='Hauptstraße 42',
        postal_code='80801',
        city='München'
    )


@pytest.fixture
def course(db):
    """Course Fixture"""
    offer = OfferFactory(title='Rückbildung')
    return CourseFactory(
        offer=offer,
        end_date=date(2025, 10, 31)
    )


@pytest.fixture
def discount_code(db, customer, course):
    """Discount Code Fixture - FIXED: Uses today for valid period"""
    today = date.today()
    return CustomerDiscountCodeFactory(
        customer=customer,
        course=course,
        code='RB1025MJ',
        discount_type='percentage',
        discount_value=10,
        valid_from=today,
        valid_until=today + timedelta(days=30),
        status='valid',
        reason='completion'
    )


@pytest.fixture
def expired_discount_code(db, customer, course):
    """Expired Discount Code Fixture"""
    today = date.today()
    return CustomerDiscountCodeFactory(
        customer=customer,
        course=course,
        code='EXPIRED001',
        discount_type='percentage',
        discount_value=15,
        valid_from=today - timedelta(days=60),
        valid_until=today - timedelta(days=30),
        status='expired'
    )


@pytest.fixture
def fixed_amount_discount(db, customer, course):
    """Fixed Amount Discount Fixture"""
    return CustomerDiscountCodeFactory(
        customer=customer,
        course=course,
        code='FIXED50',
        discount_type='fixed',
        discount_value=50.00,
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=365),
        status='valid'
    )


# ==================== ADDRESS GEOCODER TESTS ====================

class TestAddressGeocoder:
    """Tests für AddressGeocoder Service"""

    @pytest.fixture
    def geocoder(self):
        """Geocoder Fixture"""
        return AddressGeocoder()

    def test_geocoder_initialization(self, geocoder):
        """Test: Geocoder wird initialisiert"""
        assert geocoder is not None
        assert geocoder.TIMEOUT == 10
        assert geocoder.DELAY == 1
        assert geocoder.USER_AGENT == "bewegungsradius_app"

    def test_geocoder_has_geolocator(self, geocoder):
        """Test: Geocoder hat Geolocator-Instanz"""
        assert geocoder.geolocator is not None

    @patch('customers.services.Nominatim')
    def test_geocode_with_valid_address(self, mock_nominatim, geocoder):
        """Test: geocode() mit gültiger Adresse - FIXED: Mock instance method directly"""
        # Mock Location
        mock_location = MagicMock()
        mock_location.longitude = 11.5820
        mock_location.latitude = 48.1351

        # FIX: Mock die Instanz-Methode direkt
        geocoder.geolocator.geocode = MagicMock(return_value=mock_location)

        result = geocoder.geocode('Hauptstraße 42, 80801 München, Deutschland')

        assert result is not None
        assert isinstance(result, Point)
        assert result.x == 11.5820  # longitude
        assert result.y == 48.1351  # latitude
        assert result.srid == 4326

    @patch('customers.services.Nominatim')
    def test_geocode_with_empty_address(self, mock_nominatim, geocoder):
        """Test: geocode() mit leerer Adresse"""
        result = geocoder.geocode('')

        assert result is None

    @patch('customers.services.Nominatim')
    def test_geocode_with_none_address(self, mock_nominatim, geocoder):
        """Test: geocode() mit None-Adresse"""
        result = geocoder.geocode(None)

        assert result is None

    @patch('customers.services.Nominatim')
    def test_geocode_when_location_not_found(self, mock_nominatim, geocoder):
        """Test: geocode() wenn Adresse nicht gefunden"""
        geocoder.geolocator.geocode = MagicMock(return_value=None)

        result = geocoder.geocode('Ungültige Adresse 999')

        assert result is None

    @patch('customers.services.Nominatim')
    @patch('customers.services.logger')
    def test_geocode_with_timeout(self, mock_logger, mock_nominatim, geocoder):
        """Test: geocode() bei Timeout"""
        from geopy.exc import GeocoderTimedOut

        geocoder.geolocator.geocode = MagicMock(side_effect=GeocoderTimedOut('timeout'))

        result = geocoder.geocode('Hauptstraße 42, München')

        assert result is None
        assert mock_logger.warning.called

    @patch('customers.services.Nominatim')
    @patch('customers.services.logger')
    def test_geocode_with_service_error(self, mock_logger, mock_nominatim, geocoder):
        """Test: geocode() bei Service-Fehler"""
        from geopy.exc import GeocoderServiceError

        geocoder.geolocator.geocode = MagicMock(side_effect=GeocoderServiceError('error'))

        result = geocoder.geocode('Hauptstraße 42, München')

        assert result is None
        assert mock_logger.warning.called

    @patch('customers.services.time.sleep')
    @patch('customers.services.Nominatim')
    def test_geocode_respects_delay(self, mock_nominatim, mock_sleep, geocoder):
        """Test: geocode() beachtet DELAY"""
        mock_location = MagicMock()
        mock_location.longitude = 11.5820
        mock_location.latitude = 48.1351
        geocoder.geolocator.geocode = MagicMock(return_value=mock_location)

        geocoder.geocode('Test Adresse')

        assert mock_sleep.called
        mock_sleep.assert_called_with(1)


# ==================== DISCOUNT CODE VALIDATOR TESTS ====================

class TestDiscountCodeValidator:
    """Tests für DiscountCodeValidator Service"""

    def test_validator_initialization(self, discount_code):
        """Test: Validator wird initialisiert"""
        validator = DiscountCodeValidator(discount_code)
        assert validator.code == discount_code

    def test_validate_valid_code(self, discount_code):
        """Test: validate() mit gültigem Code - FIXED: Use dynamic dates"""
        # discount_code fixture bereits mit today konfiguriert
        validator = DiscountCodeValidator(discount_code)
        is_valid, message = validator.validate()

        assert is_valid is True
        assert message == "Code ist gültig"

    def test_validate_used_code(self, discount_code):
        """Test: validate() mit bereits verwendetem Code"""
        discount_code.status = 'used'
        discount_code.save()

        validator = DiscountCodeValidator(discount_code)
        is_valid, message = validator.validate()

        assert is_valid is False
        assert "bereits verwendet" in message

    def test_validate_cancelled_code(self, discount_code):
        """Test: validate() mit storniertem Code"""
        discount_code.status = 'cancelled'
        discount_code.save()

        validator = DiscountCodeValidator(discount_code)
        is_valid, message = validator.validate()

        assert is_valid is False
        assert "storniert" in message

    def test_validate_expired_code(self, expired_discount_code):
        """Test: validate() mit abgelaufenem Code"""
        validator = DiscountCodeValidator(expired_discount_code)
        is_valid, message = validator.validate()

        assert is_valid is False
        assert "abgelaufen" in message

    def test_validate_code_not_yet_valid(self, discount_code):
        """Test: validate() Code ist noch nicht gültig"""
        today = date.today()
        discount_code.status = 'valid'
        discount_code.valid_from = today + timedelta(days=10)
        discount_code.valid_until = today + timedelta(days=20)
        discount_code.save()

        validator = DiscountCodeValidator(discount_code)
        is_valid, message = validator.validate()

        assert is_valid is False
        assert "noch nicht gültig" in message

    def test_validate_code_passed_expiration(self, discount_code):
        """Test: validate() Code ist abgelaufen"""
        today = date.today()
        discount_code.status = 'valid'
        discount_code.valid_from = today - timedelta(days=30)
        discount_code.valid_until = today - timedelta(days=5)
        discount_code.save()

        validator = DiscountCodeValidator(discount_code)
        is_valid, message = validator.validate()

        assert is_valid is False
        assert "abgelaufen" in message

    def test_validate_code_today_is_first_day(self, discount_code):
        """Test: validate() wenn heute der erste gültige Tag ist"""
        today = date.today()
        discount_code.status = 'valid'
        discount_code.valid_from = today
        discount_code.valid_until = today + timedelta(days=10)
        discount_code.save()

        validator = DiscountCodeValidator(discount_code)
        is_valid, message = validator.validate()

        assert is_valid is True

    def test_validate_code_today_is_last_day(self, discount_code):
        """Test: validate() wenn heute der letzte gültige Tag ist"""
        today = date.today()
        discount_code.status = 'valid'
        discount_code.valid_from = today - timedelta(days=10)
        discount_code.valid_until = today
        discount_code.save()

        validator = DiscountCodeValidator(discount_code)
        is_valid, message = validator.validate()

        assert is_valid is True


# ==================== DISCOUNT CODE GENERATOR TESTS ====================

class TestDiscountCodeGenerator:
    """Tests für DiscountCodeGenerator Service"""

    @pytest.fixture
    def generator(self):
        """Generator Fixture"""
        return DiscountCodeGenerator()

    def test_generator_initialization(self, generator):
        """Test: Generator wird initialisiert"""
        assert generator is not None
        assert 'rueckbildung' in generator.COURSE_INITIALS
        assert 'rückbildung' in generator.COURSE_INITIALS  # FIXED: Add Umlaut variant
        assert generator.COURSE_INITIALS['rueckbildung'] == 'RB'
        assert generator.COURSE_INITIALS['rückbildung'] == 'RB'

    def test_generate_code_format(self, generator, customer):
        """Test: generate() erstellt korrektes Format - FIXED: Use Rückbildung with Umlaut"""
        offer = OfferFactory(title='Rückbildung')  # Use Umlaut version
        course = CourseFactory(offer=offer, end_date=date(2025, 10, 31))

        code = generator.generate(course, customer)

        # Format: [Initial][MM][YY][Initials]
        assert len(code) >= 8
        assert code.startswith('RB')  # Rückbildung - now works!
        assert code.endswith('MJ')     # Marcel Jäger

    def test_generate_code_with_rueckbildung_course(self, generator, customer):
        """Test: generate() mit Rückbildungs-Kurs - FIXED: Use correct Umlaut"""
        offer = OfferFactory(title='Rückbildung')  # With Umlaut
        course = CourseFactory(offer=offer, end_date=date(2025, 10, 31))

        code = generator.generate(course, customer)

        assert code.startswith('RB')

    def test_generate_code_with_pilates_course(self, generator, customer):
        """Test: generate() mit Pilates-Kurs"""
        offer = OfferFactory(title='Pilates Anfänger')
        course = CourseFactory(offer=offer, end_date=date(2025, 5, 15))

        code = generator.generate(course, customer)

        assert code.startswith('P')

    def test_generate_code_with_body_workout_course(self, generator, customer):
        """Test: generate() mit Body-Workout-Kurs"""
        offer = OfferFactory(title='Body-Workout Fortgeschrittene')
        course = CourseFactory(offer=offer, end_date=date(2025, 3, 20))

        code = generator.generate(course, customer)

        assert code.startswith('BW')

    def test_generate_code_with_unknown_course_type(self, generator, customer):
        """Test: generate() mit unbekanntem Kurs-Typ"""
        offer = OfferFactory(title='Yoga für Anfänger')
        course = CourseFactory(offer=offer, end_date=date(2025, 6, 30))

        code = generator.generate(course, customer)

        assert code.startswith('XX')  # Fallback

    def test_generate_unique_codes(self, generator, customer):
        """Test: generate() erstellt eindeutige Codes - FIXED: Use different courses"""
        offer = OfferFactory(title='Rückbildung')
        course1 = CourseFactory(offer=offer, end_date=date(2025, 10, 31))
        course2 = CourseFactory(offer=offer, end_date=date(2025, 11, 30))

        code1 = generator.generate(course1, customer)
        code2 = generator.generate(course2, customer)

        # Different courses = different codes
        assert code1 != code2

    def test_generate_includes_month_year(self, generator, customer):
        """Test: generate() enthält Monat und Jahr"""
        offer = OfferFactory(title='Rückbildung')
        course = CourseFactory(offer=offer, end_date=date(2025, 10, 31))

        code = generator.generate(course, customer)

        # Format: RB[MM][YY]MJ -> RB1025MJ
        assert '1025' in code  # Oktober 2025

    def test_generate_with_no_end_date(self, generator, customer):
        """Test: generate() wenn Kurs kein End-Datum hat - FIXED: datetime.now() import"""
        offer = OfferFactory(title='Rückbildung')
        course = CourseFactory(offer=offer, end_date=None)

        code = generator.generate(course, customer)

        # Sollte trotzdem Code erstellen (mit aktuellem Datum)
        assert code is not None
        assert len(code) >= 8

    def test_customer_initials_extraction(self, generator):
        """Test: _get_customer_initials() mit verschiedenen Namen"""
        customer = CustomerFactory(first_name='Anna', last_name='Schmidt')
        initials = generator._get_customer_initials(customer)

        assert initials == 'AS'

    def test_customer_initials_uppercase(self, generator):
        """Test: _get_customer_initials() gibt Großbuchstaben zurück"""
        customer = CustomerFactory(first_name='johannes', last_name='müller')
        initials = generator._get_customer_initials(customer)

        assert initials == 'JM'
        assert initials.isupper()

    def test_date_part_extraction(self, generator):
        """Test: _get_date_part() extrahiert Monat und Jahr"""
        offer = OfferFactory()
        course = CourseFactory(offer=offer, end_date=date(2025, 3, 15))

        date_part = generator._get_date_part(course)

        assert date_part == '0325'  # März 2025


# ==================== DISCOUNT CODE CALCULATOR TESTS ====================

class TestDiscountCodeCalculator:
    """Tests für DiscountCodeCalculator Service"""

    def test_calculate_discount_percentage(self, discount_code):
        """Test: calculate_discount_amount() mit Prozentsatz"""
        discount_code.discount_type = 'percentage'
        discount_code.discount_value = 10
        discount_code.save()

        amount = DiscountCodeCalculator.calculate_discount_amount(discount_code, 100)

        assert amount == 10.0

    def test_calculate_discount_percentage_complex(self, discount_code):
        """Test: calculate_discount_amount() Prozentsatz komplexer Betrag"""
        discount_code.discount_type = 'percentage'
        discount_code.discount_value = 15
        discount_code.save()

        amount = DiscountCodeCalculator.calculate_discount_amount(discount_code, 250)

        assert amount == 37.5

    def test_calculate_discount_fixed_amount(self, fixed_amount_discount):
        """Test: calculate_discount_amount() mit festem Betrag"""
        fixed_amount_discount.discount_type = 'fixed'
        fixed_amount_discount.discount_value = 50
        fixed_amount_discount.save()

        amount = DiscountCodeCalculator.calculate_discount_amount(
            fixed_amount_discount,
            200
        )

        assert amount == 50.0

    def test_calculate_discount_fixed_capped_at_amount(self, fixed_amount_discount):
        """Test: calculate_discount_amount() Fixed Betrag begrenzt durch Endsumme"""
        fixed_amount_discount.discount_type = 'fixed'
        fixed_amount_discount.discount_value = 100
        fixed_amount_discount.save()

        # Rabatt kann nie größer als Betrag sein
        amount = DiscountCodeCalculator.calculate_discount_amount(
            fixed_amount_discount,
            50  # Nur 50€ Rechnungsbetrag
        )

        assert amount == 50.0  # Min des Rabatts und des Betrags

    def test_calculate_final_amount_with_discount(self):
        """Test: calculate_final_amount() mit Rabatt"""
        final = DiscountCodeCalculator.calculate_final_amount(100, 10)

        assert final == 90.0

    def test_calculate_final_amount_full_discount(self):
        """Test: calculate_final_amount() mit vollem Rabatt"""
        final = DiscountCodeCalculator.calculate_final_amount(100, 100)

        assert final == 0.0

    def test_calculate_final_amount_no_negative(self):
        """Test: calculate_final_amount() wird nie negativ"""
        # Rabatt größer als Betrag (sollte nicht vorkommen, aber sichere es ab)
        final = DiscountCodeCalculator.calculate_final_amount(50, 100)

        assert final == 0.0

    def test_calculate_final_amount_no_discount(self):
        """Test: calculate_final_amount() ohne Rabatt"""
        final = DiscountCodeCalculator.calculate_final_amount(100, 0)

        assert final == 100.0

    def test_calculate_discount_zero_percentage(self, discount_code):
        """Test: calculate_discount_amount() mit 0% Rabatt"""
        discount_code.discount_type = 'percentage'
        discount_code.discount_value = 0
        discount_code.save()

        amount = DiscountCodeCalculator.calculate_discount_amount(discount_code, 100)

        assert amount == 0.0

    def test_calculate_discount_100_percentage(self, discount_code):
        """Test: calculate_discount_amount() mit 100% Rabatt"""
        discount_code.discount_type = 'percentage'
        discount_code.discount_value = 100
        discount_code.save()

        amount = DiscountCodeCalculator.calculate_discount_amount(discount_code, 100)

        assert amount == 100.0


# ==================== DISCOUNT CODE FORMATTER TESTS ====================

class TestDiscountCodeFormatter:
    """Tests für DiscountCodeFormatter Service"""

    def test_format_discount_display_percentage(self, discount_code):
        """Test: format_discount_display() mit Prozentsatz"""
        discount_code.discount_type = 'percentage'
        discount_code.discount_value = 15
        discount_code.save()

        display = DiscountCodeFormatter.format_discount_display(discount_code)

        assert display == '15%'

    def test_format_discount_display_fixed(self, fixed_amount_discount):
        """Test: format_discount_display() mit festem Betrag"""
        fixed_amount_discount.discount_type = 'fixed'
        fixed_amount_discount.discount_value = 25.50
        fixed_amount_discount.save()

        display = DiscountCodeFormatter.format_discount_display(fixed_amount_discount)

        assert display == '25.5€'

    def test_format_discount_display_zero_percentage(self, discount_code):
        """Test: format_discount_display() mit 0% Rabatt"""
        discount_code.discount_type = 'percentage'
        discount_code.discount_value = 0
        discount_code.save()

        display = DiscountCodeFormatter.format_discount_display(discount_code)

        assert display == '0%'

    def test_format_discount_display_high_percentage(self, discount_code):
        """Test: format_discount_display() mit hohem Prozentsatz"""
        discount_code.discount_type = 'percentage'
        discount_code.discount_value = 99.5
        discount_code.save()

        display = DiscountCodeFormatter.format_discount_display(discount_code)

        assert display == '99.5%'

    def test_format_full_info(self, discount_code):
        """Test: format_full_info() formatiert komplette Info"""
        discount_code.discount_type = 'percentage'
        discount_code.discount_value = 10
        discount_code.code = 'TEST001'
        discount_code.reason = 'completion'
        discount_code.save()

        full_info = DiscountCodeFormatter.format_full_info(discount_code)

        assert 'TEST001' in full_info
        assert '10%' in full_info

    def test_format_full_info_fixed_amount(self, fixed_amount_discount):
        """Test: format_full_info() mit festem Betrag"""
        fixed_amount_discount.code = 'FIXED50'
        fixed_amount_discount.discount_type = 'fixed'
        fixed_amount_discount.discount_value = 50
        fixed_amount_discount.reason = 'loyalty'
        fixed_amount_discount.save()

        full_info = DiscountCodeFormatter.format_full_info(fixed_amount_discount)

        assert 'FIXED50' in full_info
        assert '50€' in full_info

    def test_format_full_info_structure(self, discount_code):
        """Test: format_full_info() hat korrektes Format"""
        full_info = DiscountCodeFormatter.format_full_info(discount_code)

        # Format: CODE - DISCOUNT (REASON)
        parts = full_info.split(' - ')
        assert len(parts) >= 2
        assert discount_code.code in full_info


# ==================== INTEGRATION TESTS ====================

class TestCustomerServicesIntegration:
    """Integration Tests für Customer Services"""

    def test_full_discount_code_workflow(self, customer):
        """Test: Kompletter Rabattcode-Workflow"""
        offer = OfferFactory(title='Rückbildung')
        course = CourseFactory(offer=offer, end_date=date(2025, 10, 31))

        # 1. Generiere Code
        generator = DiscountCodeGenerator()
        code = generator.generate(course, customer)

        # 2. Erstelle Code in DB
        discount = CustomerDiscountCodeFactory(
            customer=customer,
            course=course,
            code=code,
            discount_type='percentage',
            discount_value=10,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            status='valid'
        )

        # 3. Validiere Code
        validator = DiscountCodeValidator(discount)
        is_valid, message = validator.validate()
        assert is_valid is True

        # 4. Berechne Rabatt
        discount_amount = DiscountCodeCalculator.calculate_discount_amount(
            discount,
            100
        )
        assert discount_amount == 10.0

        # 5. Formatiere für Anzeige
        display = DiscountCodeFormatter.format_discount_display(discount)
        assert display == '10%'

    def test_discount_code_lifecycle(self, customer):
        """Test: Kompletter Lebenzyklus eines Rabattcodes"""
        offer = OfferFactory(title='Rückbildung')
        course = CourseFactory(offer=offer, end_date=date(2025, 10, 31))
        generator = DiscountCodeGenerator()

        # Erstelle Code
        code = generator.generate(course, customer)
        discount = CustomerDiscountCodeFactory(
            customer=customer,
            course=course,
            code=code,
            status='valid',
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30)
        )

        # Code ist valid
        validator = DiscountCodeValidator(discount)
        is_valid, _ = validator.validate()
        assert is_valid is True

        # Code wird verwendet
        discount.status = 'used'
        discount.save()

        # Code ist nun invalid
        validator = DiscountCodeValidator(discount)
        is_valid, message = validator.validate()
        assert is_valid is False
        assert 'verwendet' in message

    def test_different_discount_types_calculation(self):
        """Test: Verschiedene Rabatttypen in Berechnung"""
        # Prozentsatz-Rabatt: 20% von 100€ = 20€
        percentage = CustomerDiscountCodeFactory(
            discount_type='percentage',
            discount_value=20
        )
        percent_discount = DiscountCodeCalculator.calculate_discount_amount(
            percentage,
            100
        )
        assert percent_discount == 20.0

        # Festbetrag-Rabatt: 25€ (fest)
        fixed = CustomerDiscountCodeFactory(
            discount_type='fixed',
            discount_value=25
        )
        fixed_discount = DiscountCodeCalculator.calculate_discount_amount(
            fixed,
            100
        )
        assert fixed_discount == 25.0

        # Festbetrag > Prozentsatz bei diesen Werten (25€ > 20€)
        assert fixed_discount > percent_discount

    def test_multiple_codes_for_same_customer(self, customer):
        """Test: Mehrere Codes für denselben Kunden"""
        generator = DiscountCodeGenerator()
        offer = OfferFactory(title='Rückbildung')

        course1 = CourseFactory(offer=offer, end_date=date(2025, 5, 31))
        course2 = CourseFactory(offer=offer, end_date=date(2025, 6, 30))

        code1 = generator.generate(course1, customer)
        code2 = generator.generate(course2, customer)

        assert code1 != code2
        assert code1.startswith('RB')
        assert code2.startswith('RB')

    def test_geocoding_with_customer_address(self, customer):
        """Test: Geocoding mit echter Kundenadresse"""
        geocoder = AddressGeocoder()

        address = f"{customer.street}, {customer.postal_code} {customer.city}"

        # Wird möglicherweise ein echtes Result oder None zurückgeben
        # Abhängig von Nominatim API Verfügbarkeit
        result = geocoder.geocode(address)

        # Nur sicherstellen dass Funktion läuft (kann None sein bei API Error)
        assert result is None or isinstance(result, Point)

    def test_discount_formatting_for_display(self):
        """Test: Rabatt-Formatierung für UI-Display"""
        percentage = CustomerDiscountCodeFactory(
            code='SALE20',
            discount_type='percentage',
            discount_value=20,
            reason='seasonal'
        )

        display = DiscountCodeFormatter.format_discount_display(percentage)
        full_info = DiscountCodeFormatter.format_full_info(percentage)

        assert display == '20%'
        assert 'SALE20' in full_info
        assert '20%' in full_info

    def test_validator_with_various_statuses(self, customer, course):
        """Test: Validator mit verschiedenen Status-Werten"""
        statuses = ['used', 'cancelled', 'expired']

        for status in statuses:
            discount = CustomerDiscountCodeFactory(
                customer=customer,
                course=course,
                status=status
            )

            validator = DiscountCodeValidator(discount)
            is_valid, message = validator.validate()

            assert is_valid is False
            assert message  # Message sollte nicht leer sein

    def test_discount_calculation_chain(self):
        """Test: Komplette Berechnungs-Kette"""
        original_amount = 150.00
        discount_code = CustomerDiscountCodeFactory(
            discount_type='percentage',
            discount_value=20  # 20%
        )

        # Berechne Rabatt
        discount_amount = DiscountCodeCalculator.calculate_discount_amount(
            discount_code,
            original_amount
        )
        assert discount_amount == 30.0  # 20% von 150

        # Berechne Finalbetrag
        final_amount = DiscountCodeCalculator.calculate_final_amount(
            original_amount,
            discount_amount
        )
        assert final_amount == 120.0  # 150 - 30

        # Formatiere für Anzeige
        display = DiscountCodeFormatter.format_discount_display(discount_code)
        assert display == '20%'


# ==================== EDGE CASE TESTS ====================

class TestServicesEdgeCases:
    """Edge Case Tests für alle Services"""

    def test_generator_with_special_characters_in_name(self, course):
        """Test: Generator mit Umlauten im Namen"""
        customer = CustomerFactory(
            first_name='Jörg',
            last_name='Müller'
        )

        generator = DiscountCodeGenerator()
        code = generator.generate(course, customer)

        # Sollte trotzdem funktionieren
        assert code is not None
        assert len(code) >= 8

    def test_validator_boundary_dates(self):
        """Test: Validator an Datum-Grenzen"""
        today = date.today()

        # Code gültig von heute bis morgen
        discount = CustomerDiscountCodeFactory(
            status='valid',
            valid_from=today,
            valid_until=today + timedelta(days=1)
        )

        validator = DiscountCodeValidator(discount)
        is_valid, _ = validator.validate()

        assert is_valid is True

    def test_calculator_with_zero_amount(self):
        """Test: Calculator mit 0€ Rechnungsbetrag"""
        discount = CustomerDiscountCodeFactory(
            discount_type='percentage',
            discount_value=20
        )

        discount_amount = DiscountCodeCalculator.calculate_discount_amount(
            discount,
            0
        )

        assert discount_amount == 0.0

    def test_calculator_with_very_large_amount(self):
        """Test: Calculator mit sehr großem Betrag"""
        discount = CustomerDiscountCodeFactory(
            discount_type='percentage',
            discount_value=15
        )

        discount_amount = DiscountCodeCalculator.calculate_discount_amount(
            discount,
            999999.99
        )

        assert discount_amount == 999999.99 * 0.15

    def test_formatter_with_decimal_percentages(self):
        """Test: Formatter mit Dezimal-Prozentsätzen"""
        discount = CustomerDiscountCodeFactory(
            discount_type='percentage',
            discount_value=12.5
        )

        display = DiscountCodeFormatter.format_discount_display(discount)

        assert display == '12.5%'

    def test_formatter_with_very_large_fixed_amount(self):
        """Test: Formatter mit sehr großem Festbetrag"""
        discount = CustomerDiscountCodeFactory(
            discount_type='fixed',
            discount_value=9999.99
        )

        display = DiscountCodeFormatter.format_discount_display(discount)

        assert '9999.99€' in display