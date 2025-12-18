import factory
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point

# Models
from company.models import CompanyInfo
from invoices.models import Invoice
from offers.models import Offer, ZPPCertification
from courses.models import Location, Course
from customers.models import Customer, CustomerDiscountCode, ContactChannel  # ✅ HINZUGEFÜGT


# ============================================================
# COMPANY APP (KORRIGIERT!)
# ============================================================

class CompanyInfoFactory(factory.django.DjangoModelFactory):
    """Factory für CompanyInfo Singleton - KORRIGIERT!"""
    class Meta:
        model = CompanyInfo

    name = factory.Faker('company', locale='de_DE')
    street = factory.Faker('street_address', locale='de_DE')
    house_number = factory.Faker('building_number', locale='de_DE')
    postal_code = factory.Faker('postcode', locale='de_DE')
    city = factory.Faker('city', locale='de_DE')
    phone = factory.Faker('phone_number', locale='de_DE')
    email = factory.Faker('email')
    tax_number = factory.Faker('numerify', text='###########')
    bank_name = factory.Faker('company', locale='de_DE')
    iban = 'DE89370400440532013000'  # Gültige Fake IBAN
    bic = 'COBADEDDXXX'
    # logo = None  # Optional, kann leer sein (blank=True, null=True)

    """
    WICHTIG: SingletonModel
    - get_solo() sollte verwendet werden wenn du die instanz brauchst
    - Factory wird nur genutzt zum Testen
    - In conftest.py: scope='session' verwenden!
    """


# ============================================================
# INVOICES APP (ÜBERPRÜFT - OK)
# ============================================================

class InvoiceFactory(factory.django.DjangoModelFactory):
    """Factory für Invoice - ÜBERPRÜFT"""
    class Meta:
        model = Invoice

    invoice_number = factory.Sequence(lambda n: f'2025-{n+1:03d}')
    customer = factory.SubFactory('tests.factories.CustomerFactory')
    course = factory.SubFactory('tests.factories.CourseFactory')
    discount_code = None
    issue_date = factory.Faker('date_object')
    due_date = factory.LazyAttribute(
        lambda obj: obj.issue_date + timedelta(days=14) 
        if obj.issue_date 
        else date.today() + timedelta(days=14)
    )
    course_units = factory.Faker('random_int', min=5, max=20)
    course_duration = factory.Faker('random_element', elements=[30, 45, 60, 90])
    course_id_custom = factory.Faker('bothify', letters='ABCDEFGH', text='KU-??-######')
    amount = Decimal('99.99')
    original_amount = None
    discount_amount = Decimal('0.00')
    tax_rate = Decimal('0.00')
    is_tax_exempt = True
    status = 'draft'
    cancelled_at = None
    cancelled_invoice_number = None
    is_prevention_certified = True
    zpp_prevention_id = ''
    notes = factory.Faker('sentence')


class InvoiceWithDiscountFactory(InvoiceFactory):
    """Factory für Invoice mit Rabatt - ÜBERPRÜFT"""
    discount_code = factory.SubFactory('tests.factories.CustomerDiscountCodeFactory')
    discount_amount = Decimal('10.00')
    amount = Decimal('89.99')


# ============================================================
# OFFERS APP (ÜBERPRÜFT - OK)
# ============================================================

class ZPPCertificationFactory(factory.django.DjangoModelFactory):
    """Factory für ZPP-Zertifizierung - ÜBERPRÜFT"""
    class Meta:
        model = ZPPCertification

    zpp_id = factory.Sequence(lambda n: f'KU-BE-{n:06d}')
    name = factory.Faker('sentence', locale='de_DE')
    official_title = factory.Faker('sentence', locale='de_DE')
    format = factory.Faker('random_element', elements=['praesenz', 'online', 'hybrid'])
    valid_from = factory.Faker('date_object')
    valid_until = factory.LazyAttribute(
        lambda obj: obj.valid_from + timedelta(days=365) 
        if obj.valid_from 
        else date.today() + timedelta(days=365)
    )
    is_active = True
    notes = factory.Faker('text', locale='de_DE')


class OfferFactory(factory.django.DjangoModelFactory):
    """Factory für Offer - ÜBERPRÜFT"""
    class Meta:
        model = Offer

    offer_type = factory.Faker('random_element', elements=[
        'course', 'ticket_10', 'workshop', 'seminar'
    ])
    title = factory.Faker('random_element', elements=[
        'Rückbildung', 'Pilates', 'Body-Workout', 'Personal Coach', '10er-Karte'
    ])
    course_units = factory.Faker('random_int', min=5, max=20)
    course_duration = factory.Faker('random_element', elements=[30, 45, 60, 90])
    amount = Decimal('99.99')
    tax_rate = Decimal('0.00')
    is_tax_exempt = True
    zpp_certification = factory.SubFactory(ZPPCertificationFactory)
    notes = factory.Faker('sentence', locale='de_DE')


# ============================================================
# COURSES APP (ÜBERPRÜFT - OK)
# ============================================================

class LocationFactory(factory.django.DjangoModelFactory):
    """Factory für Location/Kursort - ÜBERPRÜFT"""
    class Meta:
        model = Location
        skip_postgeneration_save = True

    name = factory.Faker('city', locale='de_DE')
    street = factory.Faker('street_address', locale='de_DE')
    house_number = factory.Faker('building_number', locale='de_DE')
    postal_code = factory.Faker('postcode', locale='de_DE')
    city = factory.Faker('city', locale='de_DE')
    max_participants = factory.Faker('random_int', min=8, max=20)
    notes = factory.Faker('sentence', locale='de_DE')
    coordinates = Point(13.405, 52.52)


class CourseFactory(factory.django.DjangoModelFactory):
    """Factory für Course - KORRIGIERT"""

    class Meta:
        model = Course
        skip_postgeneration_save = True

    offer = factory.SubFactory(OfferFactory)
    location = factory.SubFactory(LocationFactory)

    start_date = factory.Faker('future_date', end_date='+30d')
    end_date = factory.LazyAttribute(lambda obj: obj.start_date + timedelta(weeks=8))
    start_time = factory.Faker('time_object')  # ✅ HINZUFÜGEN!
    end_time = factory.Faker('time_object')  # ✅ BEHALTEN!

    is_weekly = True
    # ✅ NICHT weekday setzen - wird auto-calculated!
    is_active = True
    start_email_sent = False  # ✅ HINZUFÜGEN!
    completion_email_sent = False  # ✅ HINZUFÜGEN!

    @factory.post_generation
    def participants_inperson(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for participant in extracted:
                obj.participants_inperson.add(participant)

    @factory.post_generation
    def participants_online(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for participant in extracted:
                obj.participants_online.add(participant)


class CourseWithParticipantsFactory(CourseFactory):
    """Factory für Course mit Teilnehmern - ÜBERPRÜFT"""
    @factory.post_generation
    def setup_participants(obj, create, extracted, **kwargs):
        """Erstellt automatisch 5 Teilnehmer"""
        if not create:
            return
        participants = CustomerFactory.create_batch(5)
        for participant in participants:
            obj.participants_inperson.add(participant)


# ============================================================
# CUSTOMERS APP (ÜBERPRÜFT & KORRIGIERT!)
# ============================================================

class ContactChannelFactory(factory.django.DjangoModelFactory):
    """Factory für ContactChannel - NEU HINZUGEFÜGT! ✅"""
    class Meta:
        model = ContactChannel

    name = factory.Faker('random_element', elements=[
        'Kikudoo', 'Webseite', 'Telefon', 'E-Mail', 'WhatsApp', 'Instagram'
    ])
    slug = factory.Faker('slug')
    description = factory.Faker('sentence', locale='de_DE')
    is_active = True


class CustomerFactory(factory.django.DjangoModelFactory):
    """Factory für Customer/Teilnehmer - ÜBERPRÜFT & KORRIGIERT!"""
    class Meta:
        model = Customer

    first_name = factory.Faker('first_name', locale='de_DE')
    last_name = factory.Faker('last_name', locale='de_DE')
    email = factory.Sequence(lambda n: f'customer{n}@example.com')
    mobile = factory.Faker('phone_number', locale='de_DE')
    birthday = factory.Faker('date_of_birth', minimum_age=18, maximum_age=70)
    street = factory.Faker('street_address', locale='de_DE')
    house_number = factory.Faker('building_number', locale='de_DE')
    postal_code = factory.Faker('postcode', locale='de_DE')
    city = factory.Faker('city', locale='de_DE')
    country = 'Deutschland'
    coordinates = None
    contact_channel = factory.SubFactory(ContactChannelFactory)  # ✅ NEU HINZUGEFÜGT!
    notes = factory.Faker('sentence', locale='de_DE')
    is_active = True
    archived_at = None


class CustomerDiscountCodeFactory(factory.django.DjangoModelFactory):
    """Factory für CustomerDiscountCode - ÜBERPRÜFT"""
    class Meta:
        model = CustomerDiscountCode

    customer = factory.SubFactory(CustomerFactory)
    code = factory.Sequence(lambda n: f'DISC-{n:06d}')
    discount_type = factory.Faker('random_element', elements=['percentage', 'fixed'])
    discount_value = factory.Faker('random_element', elements=[
        Decimal('10.00'), Decimal('15.00'), Decimal('20.00'), Decimal('25.00')
    ])
    reason = factory.Faker('random_element', elements=[
        'birthday', 'course_completed', 'referral', 'loyalty', 'other'
    ])
    description = factory.Faker('sentence', locale='de_DE')
    valid_from = factory.Faker('date_object')
    valid_until = factory.LazyAttribute(lambda obj: obj.valid_from + timedelta(days=90))
    status = 'planned'
    used_at = None
    email_sent_at = None
    cancelled_at = None
    cancelled_reason = ''
    created_by = None


class ActiveDiscountCodeFactory(CustomerDiscountCodeFactory):
    """Factory für aktiven Rabattcode - ÜBERPRÜFT"""
    status = 'sent'
    valid_from = factory.LazyAttribute(lambda obj: date.today() - timedelta(days=10))
    valid_until = factory.LazyAttribute(lambda obj: date.today() + timedelta(days=80))


# ============================================================
# AUTH APP (NEU HINZUGEFÜGT)
# ============================================================

class UserFactory(factory.django.DjangoModelFactory):
    """Factory für Django User"""
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Faker('user_name', locale='de_DE')
    email = factory.Faker('email')
    first_name = factory.Faker('first_name', locale='de_DE')
    last_name = factory.Faker('last_name', locale='de_DE')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True
    is_staff = False
    is_superuser = False


class AdminUserFactory(UserFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    """Factory für Admin-User"""
    is_staff = True
    is_superuser = True