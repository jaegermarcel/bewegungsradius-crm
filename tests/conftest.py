"""
tests/conftest.py - COMPLETE VERSION (FIXED)
=============================================
ALLE Fixtures für das Projekt
Enthält: Factory-Fixtures, DB-Config, Settings
"""

from datetime import date, timedelta

import pytest

from tests.factories import (
    ActiveDiscountCodeFactory,
    CompanyInfoFactory,
    CourseFactory,
    CustomerDiscountCodeFactory,
    CustomerFactory,
    InvoiceFactory,
    LocationFactory,
    OfferFactory,
    ZPPCertificationFactory,
)

# ============================================================
# FACTORIES IMPORT
# ============================================================


# ============================================================
# DJANGO SETTINGS & CONFIG
# ============================================================


@pytest.fixture(autouse=True)
def use_email_backend(settings):
    """Nutze In-Memory Email Backend"""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def celery_config(settings):
    """Celery Tasks sofort ausführen (EAGER Mode)"""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture(autouse=True)
def clear_cache():
    """Cache leeren vor jedem Test"""
    from django.core.cache import cache

    cache.clear()
    yield


# ============================================================
# COMPANY FIXTURES
# ============================================================


@pytest.fixture
def company(db):
    """Basis CompanyInfo Fixture"""
    return CompanyInfoFactory()


# ============================================================
# CUSTOMER FIXTURES
# ============================================================


@pytest.fixture
def customer(db):
    """Einzelner Customer"""
    return CustomerFactory()


@pytest.fixture
def customers_batch(db):
    """5 Customers"""
    return CustomerFactory.create_batch(5)


@pytest.fixture
def customers_batch_large(db):
    """20 Customers für Performance Tests"""
    return CustomerFactory.create_batch(20)


@pytest.fixture
def active_customers(db):
    """5 aktive Customers"""
    return CustomerFactory.create_batch(5, is_active=True)


# ============================================================
# DISCOUNT CODE FIXTURES
# ============================================================


@pytest.fixture
def discount_code(db, customer):
    """Standard Rabattcode (planned)"""
    return CustomerDiscountCodeFactory(customer=customer)


@pytest.fixture
def active_discount_code(db, customer):
    """Aktiver Rabattcode (sent)"""
    return ActiveDiscountCodeFactory(customer=customer)


@pytest.fixture
def multiple_discount_codes(db, customer):
    """3 verschiedene Rabattcodes"""
    return CustomerDiscountCodeFactory.create_batch(3, customer=customer)


# ============================================================
# LOCATION FIXTURES
# ============================================================


@pytest.fixture
def location(db):
    """Basis Location"""
    return LocationFactory()


# ============================================================
# OFFER & ZPP FIXTURES
# ============================================================


@pytest.fixture
def zpp_certification(db):
    """Basis ZPP Certification"""
    return ZPPCertificationFactory()


@pytest.fixture
def offer(db):
    """Basis Offer"""
    return OfferFactory()


# ============================================================
# COURSE FIXTURES
# ============================================================


@pytest.fixture
def course(db, offer, location):
    """Basis Course mit Offer + Location"""
    return CourseFactory(offer=offer, location=location)


# ============================================================
# INVOICE FIXTURES
# ============================================================


@pytest.fixture
def invoice(db, customer, course):
    """Basis Invoice mit Customer + Course"""
    return InvoiceFactory(customer=customer, course=course)


# ============================================================
# CUSTOM COMBINATION FIXTURES
# ============================================================


@pytest.fixture
def customer_with_active_discount(db, customer):
    """Customer mit aktivem Rabattcode"""
    code = ActiveDiscountCodeFactory(customer=customer)
    return customer, code


@pytest.fixture
def customer_with_expired_discount(db, customer):
    """Customer mit abgelaufenem Rabattcode"""
    expired_code = CustomerDiscountCodeFactory(
        customer=customer,
        status="expired",
        valid_until=date.today() - timedelta(days=1),
    )
    return customer, expired_code


@pytest.fixture
def course_with_participants(db, offer, location, customer):
    """Course mit Teilnehmern"""
    course = CourseFactory(offer=offer, location=location)
    course.participants_inperson.add(customer)
    return course


# ============================================================
# PYTEST-DJANGO AUTO-FIXTURES (bereits vorhanden)
# ============================================================
# Folgende Fixtures sind AUTOMATISCH von pytest-django:
# - db (für @pytest.mark.django_db)
# - admin_user (superuser)
# - client (Django Test Client)
# - rf (RequestFactory)
# - settings (modifizierbare Django Settings)
# - mailbox (django-mailbox)
