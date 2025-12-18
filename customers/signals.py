from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from courses.models import Course
from customers.models import Customer, CustomerDiscountCode


class DiscountCodeDateCalculator:
    """Berechnet Gültigkeit von Rabattcodes basierend auf Kursdaten"""

    VALIDITY_DAYS = 365

    @staticmethod
    def calculate_validity(course):
        """Rückgabe: (valid_from, valid_until) als Tupel"""
        if course.end_date:
            valid_from = course.end_date
            valid_until = course.end_date + timedelta(days=DiscountCodeDateCalculator.VALIDITY_DAYS)
        else:
            today = timezone.now().date()
            valid_from = today
            valid_until = today + timedelta(days=DiscountCodeDateCalculator.VALIDITY_DAYS)

        return valid_from, valid_until


class DiscountCodeFactory:
    """Erstellt neue Rabattcodes mit standardisierten Parametern"""

    DEFAULT_DISCOUNT_VALUE = 10  # Prozent

    @classmethod
    def create_for_course_participant(cls, customer, course):
        """Erstellt Rabattcode für Kursteilnehmer"""
        code = CustomerDiscountCode.generate_course_code(course, customer)
        valid_from, valid_until = DiscountCodeDateCalculator.calculate_validity(course)

        return CustomerDiscountCode.objects.create(
            customer=customer,
            code=code,
            course=course,
            discount_type='percentage',
            discount_value=cls.DEFAULT_DISCOUNT_VALUE,
            reason='course_completed',
            description=cls._build_description(course),
            valid_from=valid_from,
            valid_until=valid_until
        )

    @staticmethod
    def _build_description(course):
        """Erstellt aussagekräftige Beschreibung für Rabattcode"""
        return f"Rabatt für Kursteilnahme: {course.offer.title} (Kurs {course.id})"


class DiscountCodeRepository:
    """Verwaltet Zugriff auf Rabattcode-Datenbankoperationen"""

    @staticmethod
    def find_existing_for_course(customer, course):
        """Sucht nach existierendem Code für Kurs"""
        return CustomerDiscountCode.objects.filter(
            customer=customer,
            description__icontains=f"Kurs {course.id}"
        ).first()

    @staticmethod
    def find_active_for_course(customer, course):
        """Sucht nach aktiven Codes für Kurs"""
        return CustomerDiscountCode.objects.filter(
            customer=customer,
            description__icontains=f"Kurs {course.id}",
            status__in=['planned', 'sent']
        )

    @staticmethod
    def cancel_codes(discount_codes, course):
        """Storniert alle übergebenen Codes"""
        for code in discount_codes:
            code.status = 'cancelled'
            code.cancelled_at = timezone.now()
            code.cancelled_reason = f"Kunde aus Kurs {course.id} entfernt"
            code.save()


class ParticipantDiscountCodeHandler:
    """Behandelt Rabattcode-Logik für Kursteilnehmer"""

    def __init__(self, repository=None, factory=None):
        self.repository = repository or DiscountCodeRepository()
        self.factory = factory or DiscountCodeFactory()

    def handle_participant_added(self, course, customer_ids):
        """Erstellt Rabattcodes für hinzugefügte Teilnehmer"""
        for customer_id in customer_ids:
            customer = Customer.objects.get(pk=customer_id)

            if not self.repository.find_existing_for_course(customer, course):
                self.factory.create_for_course_participant(customer, course)

    def handle_participant_removed(self, course, customer_ids):
        """Storniert Rabattcodes für entfernte Teilnehmer"""
        for customer_id in customer_ids:
            customer = Customer.objects.get(pk=customer_id)
            codes = self.repository.find_active_for_course(customer, course)
            self.repository.cancel_codes(codes, course)


# Globale Instanz für Signal-Handler
_discount_handler = ParticipantDiscountCodeHandler()


@receiver(m2m_changed, sender=Course.participants_inperson.through)
@receiver(m2m_changed, sender=Course.participants_online.through)
def handle_course_participant_change(sender, instance, action, pk_set, **kwargs):
    """Signal-Handler für M2M-Änderungen bei Kursteilnehmern"""
    course = instance

    if action == "post_add":
        _discount_handler.handle_participant_added(course, pk_set)
    elif action == "post_remove":
        _discount_handler.handle_participant_removed(course, pk_set)