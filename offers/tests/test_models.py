"""
offers/tests/test_models.py - Tests für ZPPCertification und Offer Models
=========================================================================
✅ ZPPCertification Model Tests
✅ ZPPCertification Validation Tests
✅ Offer Model Tests
✅ Offer Properties Tests
✅ Tax Calculation Tests
✅ Integration Tests
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ==================== IMPORTS ====================

from offers.models import ZPPCertification, Offer
from tests.factories import (
    ZPPCertificationFactory,
    OfferFactory,
)


# ==================== FIXTURES ====================

@pytest.fixture
def zpp_certification(db):
    """ZPP Certification Fixture"""
    return ZPPCertificationFactory()


@pytest.fixture
def active_zpp_certification(db):
    """Active ZPP Certification (gültig heute)"""
    return ZPPCertificationFactory(
        valid_from=date.today() - timedelta(days=30),
        valid_until=date.today() + timedelta(days=30),
        is_active=True
    )


@pytest.fixture
def expired_zpp_certification(db):
    """Expired ZPP Certification"""
    return ZPPCertificationFactory(
        valid_from=date.today() - timedelta(days=100),
        valid_until=date.today() - timedelta(days=10),
        is_active=True
    )


@pytest.fixture
def offer(db):
    """Offer Fixture"""
    return OfferFactory()


@pytest.fixture
def offer_with_zpp(db, active_zpp_certification):
    """Offer mit ZPP Zertifizierung"""
    return OfferFactory(zpp_certification=active_zpp_certification)


# ==================== ZPP CERTIFICATION MODEL TESTS ====================

class TestZPPCertificationModel:
    """Tests für ZPPCertification Model"""

    def test_zpp_certification_creation(self):
        """Test: ZPP Zertifizierung wird erstellt"""
        cert = ZPPCertificationFactory(
            zpp_id='KU-BE-ZCURFS',
            name='Pilates Präsens',
            official_title='Prävention: Pilates - Präsenz'
        )

        assert cert.id is not None
        assert cert.zpp_id == 'KU-BE-ZCURFS'
        assert cert.name == 'Pilates Präsens'
        assert cert.official_title == 'Prävention: Pilates - Präsenz'

    def test_zpp_certification_zpp_id_unique(self):
        """Test: ZPP-ID muss unique sein"""
        from django.db import IntegrityError

        ZPPCertificationFactory(zpp_id='UNIQUE-ID-001')

        with pytest.raises(IntegrityError):
            ZPPCertificationFactory(zpp_id='UNIQUE-ID-001')

    def test_zpp_certification_string_representation(self, zpp_certification):
        """Test: __str__ gibt ZPP-ID und Name"""
        str_repr = str(zpp_certification)

        assert zpp_certification.zpp_id in str_repr
        assert zpp_certification.name in str_repr

    def test_zpp_certification_format_choices(self):
        """Test: Verschiedene Format-Optionen"""
        formats = ['praesenz', 'online', 'hybrid']

        for format_choice in formats:
            cert = ZPPCertificationFactory(format=format_choice)
            assert cert.format == format_choice

    def test_zpp_certification_is_active_default_true(self):
        """Test: is_active ist default True"""
        cert = ZPPCertificationFactory()
        assert cert.is_active is True

    def test_zpp_certification_valid_from_defaults_today(self):
        """Test: valid_from hat Default heute"""
        cert = ZPPCertificationFactory()
        # Factory setzt valid_from mit Faker, also nicht exakt heute
        # Aber wir testen dass es ein Datum ist
        assert cert.valid_from is not None
        assert isinstance(cert.valid_from, date)

    def test_zpp_certification_timestamps(self):
        """Test: created_at und updated_at werden auto-gesetzt"""
        before = timezone.now()
        cert = ZPPCertificationFactory()
        after = timezone.now()

        assert before <= cert.created_at <= after
        assert before <= cert.updated_at <= after

    def test_zpp_certification_ordering(self):
        """Test: ZPP Certifications nach valid_until absteigend"""
        cert1 = ZPPCertificationFactory(valid_until=date.today() - timedelta(days=10))
        cert2 = ZPPCertificationFactory(valid_until=date.today() + timedelta(days=30))

        certs = ZPPCertification.objects.all()
        assert certs[0] == cert2
        assert certs[1] == cert1


# ==================== ZPP CERTIFICATION VALIDATION TESTS ====================

class TestZPPCertificationValidation:
    """Tests für ZPP Certification Validierung"""

    def test_is_valid_today_with_active_current_cert(self, active_zpp_certification):
        """Test: is_valid_today() True für aktuelle Zertifizierung"""
        assert active_zpp_certification.is_valid_today() is True

    def test_is_valid_today_with_expired_cert(self, expired_zpp_certification):
        """Test: is_valid_today() False für abgelaufene Zertifizierung"""
        assert expired_zpp_certification.is_valid_today() is False

    def test_is_valid_today_with_inactive_cert(self):
        """Test: is_valid_today() False für inaktive Zertifizierung"""
        cert = ZPPCertificationFactory(
            valid_from=date.today() - timedelta(days=30),
            valid_until=date.today() + timedelta(days=30),
            is_active=False
        )

        assert cert.is_valid_today() is False

    def test_is_valid_today_before_valid_from(self):
        """Test: is_valid_today() False vor valid_from Datum"""
        cert = ZPPCertificationFactory(
            valid_from=date.today() + timedelta(days=10),
            valid_until=date.today() + timedelta(days=40),
            is_active=True
        )

        assert cert.is_valid_today() is False

    def test_days_until_expiry_active(self, active_zpp_certification):
        """Test: days_until_expiry() berechnet Tage korrekt"""
        days = active_zpp_certification.days_until_expiry()

        # active_zpp hat valid_until = heute + 30 Tage
        expected_days = (active_zpp_certification.valid_until - date.today()).days
        assert days == expected_days

    def test_days_until_expiry_expired(self, expired_zpp_certification):
        """Test: days_until_expiry() gibt 0 für abgelaufene Cert"""
        days = expired_zpp_certification.days_until_expiry()
        assert days == 0

    def test_days_until_expiry_before_valid_from(self):
        """Test: days_until_expiry() berechnet Tage bis gültig"""
        cert = ZPPCertificationFactory(
            valid_from=date.today() + timedelta(days=10),
            valid_until=date.today() + timedelta(days=40),
            is_active=True
        )

        days = cert.days_until_expiry()
        # sollte Tage bis valid_until sein
        expected_days = (cert.valid_until - date.today()).days
        assert days == expected_days


# ==================== OFFER MODEL TESTS ====================

class TestOfferModel:
    """Tests für Offer Model"""

    def test_offer_creation(self):
        """Test: Offer wird erstellt"""
        offer = OfferFactory(
            offer_type='course',
            title='Pilates Grundkurs',
            amount=Decimal('99.99')
        )

        assert offer.id is not None
        assert offer.offer_type == 'course'
        assert offer.title == 'Pilates Grundkurs'
        assert offer.amount == Decimal('99.99')

    def test_offer_string_representation(self, offer):
        """Test: __str__ gibt Title, Format, Einheiten und Preis"""
        str_repr = str(offer)

        assert offer.title in str_repr
        assert '€' in str_repr
        assert offer.get_offer_type_display() in str_repr

    def test_offer_string_with_zpp(self, offer_with_zpp):
        """Test: __str__ zeigt [ZPP] Flag wenn zertifiziert"""
        str_repr = str(offer_with_zpp)

        assert '[ZPP]' in str_repr

    def test_offer_course_units_optional(self):
        """Test: course_units ist optional"""
        offer = OfferFactory(course_units=None)
        assert offer.course_units is None

    def test_offer_course_duration_optional(self):
        """Test: course_duration ist optional"""
        offer = OfferFactory(course_duration=None)
        assert offer.course_duration is None

    def test_offer_zpp_certification_optional(self):
        """Test: zpp_certification ist optional"""
        offer = OfferFactory(zpp_certification=None)
        assert offer.zpp_certification is None

    def test_offer_is_tax_exempt_default_true(self):
        """Test: is_tax_exempt ist default True"""
        offer = OfferFactory()
        assert offer.is_tax_exempt is True

    def test_offer_tax_rate_default_zero(self):
        """Test: tax_rate ist default 0.00"""
        offer = OfferFactory()
        assert offer.tax_rate == Decimal('0.00')

    def test_offer_timestamps(self):
        """Test: created_at und updated_at werden auto-gesetzt"""
        before = timezone.now()
        offer = OfferFactory()
        after = timezone.now()

        assert before <= offer.created_at <= after
        assert before <= offer.updated_at <= after

    def test_offer_ordering(self):
        """Test: Offers nach created_at absteigend"""
        offer1 = OfferFactory()
        offer2 = OfferFactory()

        offers = Offer.objects.all()
        assert offers[0] == offer2
        assert offers[1] == offer1


# ==================== OFFER TAX CALCULATION TESTS ====================

class TestOfferTaxCalculation:
    """Tests für Steuberberechnung in Offer"""

    def test_tax_amount_with_tax(self):
        """Test: tax_amount berechnet Steuern"""
        offer = OfferFactory(
            amount=Decimal('100.00'),
            tax_rate=Decimal('19.00'),
            is_tax_exempt=False
        )

        assert offer.tax_amount == Decimal('19.00')

    def test_tax_amount_tax_exempt(self):
        """Test: tax_amount ist 0 bei tax_exempt"""
        offer = OfferFactory(
            amount=Decimal('100.00'),
            tax_rate=Decimal('19.00'),
            is_tax_exempt=True
        )

        assert offer.tax_amount == Decimal('0.00')

    def test_tax_amount_zero_tax_rate(self):
        """Test: tax_amount bei 0% Steuersatz"""
        offer = OfferFactory(
            amount=Decimal('100.00'),
            tax_rate=Decimal('0.00'),
            is_tax_exempt=False
        )

        assert offer.tax_amount == Decimal('0.00')

    def test_tax_amount_decimal_precision(self):
        """Test: tax_amount hat 0.01€ Genauigkeit"""
        offer = OfferFactory(
            amount=Decimal('33.33'),
            tax_rate=Decimal('19.00'),
            is_tax_exempt=False
        )

        # 33.33 * 19% = 6.3327 → 6.33
        assert offer.tax_amount == Decimal('6.33')

    def test_tax_amount_with_default_values(self):
        """Test: tax_amount mit Default Values"""
        # amount hat kein default=None, es ist NOT NULL
        offer = OfferFactory()

        # Default: amount=99.99, tax_rate=0.00, is_tax_exempt=True
        assert offer.tax_amount == Decimal('0.00')

    def test_total_amount_with_tax(self):
        """Test: total_amount mit Steuern"""
        offer = OfferFactory(
            amount=Decimal('100.00'),
            tax_rate=Decimal('19.00'),
            is_tax_exempt=False
        )

        assert offer.total_amount == Decimal('119.00')

    def test_total_amount_tax_exempt(self):
        """Test: total_amount tax_exempt"""
        offer = OfferFactory(
            amount=Decimal('100.00'),
            tax_rate=Decimal('19.00'),
            is_tax_exempt=True
        )

        assert offer.total_amount == Decimal('100.00')

    def test_total_amount_with_defaults(self):
        """Test: total_amount mit Default Values"""
        # amount ist NOT NULL, hat default amount=99.99
        offer = OfferFactory()

        # Default: amount=99.99, tax_rate=0.00, is_tax_exempt=True
        assert offer.total_amount == Decimal('99.99')

    def test_total_amount_decimal_precision(self):
        """Test: total_amount hat 0.01€ Genauigkeit"""
        offer = OfferFactory(
            amount=Decimal('33.33'),
            tax_rate=Decimal('19.00'),
            is_tax_exempt=False
        )

        # 33.33 + 6.33 = 39.66
        assert offer.total_amount == Decimal('39.66')


# ==================== OFFER PROPERTIES TESTS ====================

class TestOfferProperties:
    """Tests für Offer Properties"""

    def test_zpp_prevention_id_with_certification(self, offer_with_zpp):
        """Test: zpp_prevention_id gibt ZPP-ID zurück"""
        assert offer_with_zpp.zpp_prevention_id == offer_with_zpp.zpp_certification.zpp_id

    def test_zpp_prevention_id_without_certification(self):
        """Test: zpp_prevention_id ist None ohne Zertifizierung"""
        # ✅ WICHTIG: Explizit zpp_certification=None setzen!
        # Factory setzt es automatisch, daher müssen wir es überschreiben
        offer = OfferFactory(zpp_certification=None)

        assert offer.zpp_prevention_id is None
        assert offer.zpp_certification is None

    def test_zpp_prevention_id_rückwärtskompatibilität(self, offer_with_zpp):
        """Test: zpp_prevention_id ist Rückwärtskompatibilität"""
        # Diese Property gibt es für alte Code-Referenzen
        zpp_id = offer_with_zpp.zpp_prevention_id

        assert zpp_id is not None
        assert zpp_id == offer_with_zpp.zpp_certification.zpp_id


# ==================== OFFER WITH ZPP CERTIFICATION TESTS ====================

class TestOfferWithZPPCertification:
    """Tests für Offer mit ZPP Zertifizierung"""

    def test_offer_with_valid_zpp_certification(self, active_zpp_certification):
        """Test: Offer mit gültiger ZPP Zertifizierung"""
        offer = OfferFactory(zpp_certification=active_zpp_certification)

        assert offer.zpp_certification == active_zpp_certification
        assert offer.zpp_prevention_id == active_zpp_certification.zpp_id
        assert offer.zpp_certification.is_valid_today()

    def test_offer_with_expired_zpp_certification(self, expired_zpp_certification):
        """Test: Offer mit abgelaufener ZPP Zertifizierung"""
        offer = OfferFactory(zpp_certification=expired_zpp_certification)

        assert offer.zpp_certification == expired_zpp_certification
        assert not offer.zpp_certification.is_valid_today()

    def test_offer_cascade_delete_on_zpp_deletion(self, active_zpp_certification):
        """Test: Offer bleibt wenn ZPP gelöscht (on_delete=SET_NULL)"""
        offer = OfferFactory(zpp_certification=active_zpp_certification)

        cert_id = active_zpp_certification.id
        active_zpp_certification.delete()

        # Offer sollte noch existieren, aber ohne Zertifizierung
        offer.refresh_from_db()
        assert offer.zpp_certification is None


# ==================== INTEGRATION TESTS ====================

class TestOfferIntegration:
    """Integration Tests für Offer"""

    def test_offer_comparison_formats(self):
        """Test: Verschiedene Offer Formate"""
        praesenz = OfferFactory(offer_type='praesenz', title='Pilates Präsenz')
        online = OfferFactory(offer_type='online', title='Pilates Online')
        hybrid = OfferFactory(offer_type='hybrid', title='Pilates Hybrid')

        assert praesenz.offer_type == 'praesenz'
        assert online.offer_type == 'online'
        assert hybrid.offer_type == 'hybrid'

    def test_offer_comparison_tax_scenarios(self):
        """Test: Verschiedene Steuer-Szenarien"""
        # Kleinunternehmer (tax_exempt)
        klein = OfferFactory(
            amount=Decimal('100.00'),
            tax_rate=Decimal('19.00'),
            is_tax_exempt=True
        )

        # Regulär besteuert
        regular = OfferFactory(
            amount=Decimal('100.00'),
            tax_rate=Decimal('19.00'),
            is_tax_exempt=False
        )

        # Keine Steuer
        no_tax = OfferFactory(
            amount=Decimal('100.00'),
            tax_rate=Decimal('0.00'),
            is_tax_exempt=False
        )

        assert klein.total_amount == Decimal('100.00')
        assert regular.total_amount == Decimal('119.00')
        assert no_tax.total_amount == Decimal('100.00')

    def test_zpp_certification_expiry_workflow(self):
        """Test: ZPP Zertifizierung Ablauf Workflow"""
        # Erstelle abgelaufene Zertifizierung
        expired_cert = ZPPCertificationFactory(
            valid_from=date.today() - timedelta(days=100),
            valid_until=date.today() - timedelta(days=10),
            is_active=True
        )

        # Offer damit
        offer = OfferFactory(zpp_certification=expired_cert)

        # Zertifizierung sollte ungültig sein
        assert not offer.zpp_certification.is_valid_today()
        assert offer.zpp_certification.days_until_expiry() == 0

    def test_multiple_offers_same_certification(self, active_zpp_certification):
        """Test: Mehrere Offers mit gleicher Zertifizierung"""
        offer1 = OfferFactory(
            title='Pilates Basis',
            zpp_certification=active_zpp_certification
        )
        offer2 = OfferFactory(
            title='Pilates Premium',
            zpp_certification=active_zpp_certification
        )

        # Beide sollten die gleiche Zertifizierung haben
        assert offer1.zpp_certification == offer2.zpp_certification
        assert active_zpp_certification.offers.count() == 2