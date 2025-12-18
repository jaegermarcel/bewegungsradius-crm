from django.utils import timezone
from decimal import Decimal

from customers.models import CustomerDiscountCode
from .models import Invoice
import logging

logger = logging.getLogger(__name__)


class DiscountCodeQuerySetManager:
    """Service für QuerySet-Verwaltung von Rabattcodes"""

    def get_available_codes(self, post_data=None, instance=None):
        """Gibt verfügbare Rabattcodes basierend auf Kontext zurück"""
        # Fall 1: Neuer Datensatz mit POST-Daten (Customer ausgewählt)
        if post_data and 'customer' in post_data:
            return self._get_codes_for_customer_id(post_data.get('customer'))

        # Fall 2: Bestehender Datensatz
        if instance and instance.pk:
            return self._get_codes_for_existing_invoice(instance)

        # Fall 3: Noch kein Kontext - leere QuerySet
        return CustomerDiscountCode.objects.none()

    def _get_codes_for_customer_id(self, customer_id):
        """Gibt gültige Codes für eine Customer-ID zurück"""
        try:
            customer_id = int(customer_id)
            return self._get_valid_codes_queryset().filter(customer_id=customer_id)
        except (ValueError, TypeError):
            return CustomerDiscountCode.objects.none()

    def _get_codes_for_existing_invoice(self, invoice):
        """Gibt Codes für bestehende Invoice zurück"""
        # Wenn Code bereits verwendet: zeige nur diesen
        if invoice.discount_code:
            return CustomerDiscountCode.objects.filter(pk=invoice.discount_code.pk)

        # Sonst: zeige verfügbare Codes des Kunden
        if invoice.customer:
            return self._get_valid_codes_queryset().filter(customer=invoice.customer)

        return CustomerDiscountCode.objects.none()

    def _get_valid_codes_queryset(self):
        """Basis-QuerySet für gültige Codes"""
        today = timezone.now().date()
        return CustomerDiscountCode.objects.filter(
            status__in=['planned', 'sent'],
            valid_from__lte=today,
            valid_until__gte=today
        )


class DiscountCodeProcessor:
    """Service für Rabattcode-Verarbeitung in Invoice"""

    def process_discount_code(self, instance):
        """Verarbeitet Rabattcode-Änderungen für Invoice"""
        if not instance.pk:
            # Neuer Datensatz
            self._handle_new_discount_code(instance)
        else:
            # Bestehender Datensatz
            self._handle_discount_code_change(instance)

    def _handle_new_discount_code(self, instance):
        """Verarbeitet neu hinzugefügten Rabattcode"""
        if instance.discount_code and not instance.original_amount:
            self._apply_discount(instance)

    def _handle_discount_code_change(self, instance):
        """Verarbeitet Änderungen an existierendem Rabattcode"""
        try:
            original = Invoice.objects.get(pk=instance.pk)
            original_had_code = original.discount_code is not None
            now_has_code = instance.discount_code is not None

            # Code wurde entfernt
            if original_had_code and not now_has_code:
                self._remove_discount(instance, original)

            # Code wurde geändert
            elif original_had_code and now_has_code and original.discount_code != instance.discount_code:
                self._change_discount(instance, original)

        except Invoice.DoesNotExist:
            # Neue Invoice - behandle wie neu
            self._handle_new_discount_code(instance)

    def _apply_discount(self, instance):
        """Wendet Rabatt auf Invoice an"""
        instance.original_amount = instance.amount
        instance.discount_amount = instance.discount_code.calculate_discount(instance.amount)
        instance.amount = instance.amount - instance.discount_amount

        logger.info(f"Rabattcode {instance.discount_code.code} auf Invoice angewendet")

    def _remove_discount(self, instance, original):
        """Entfernt Rabatt von Invoice"""
        if instance.original_amount:
            instance.amount = instance.original_amount
            instance.original_amount = None
            instance.discount_amount = Decimal('0.00')

        # Gib alten Code frei
        self._release_discount_code(original.discount_code)

        logger.info(f"Rabattcode von Invoice entfernt")

    def _change_discount(self, instance, original):
        """Wechselt Rabattcode aus"""
        # Stelle Originalbetrag wieder her
        if instance.original_amount:
            instance.amount = instance.original_amount
        else:
            instance.amount = original.amount

        # Wende neuen Rabatt an
        self._apply_discount(instance)

        # Gib alten Code frei
        self._release_discount_code(original.discount_code)

        logger.info(f"Rabattcode gewechselt von {original.discount_code.code} zu {instance.discount_code.code}")

    def _release_discount_code(self, discount_code):
        """Markiert Rabattcode als nicht verwendet"""
        if discount_code and discount_code.status == 'used':
            discount_code.status = 'sent'
            discount_code.used_at = None
            discount_code.save()


class DiscountCodeValidator:
    """Service für Rabattcode-Validierung in Form"""

    @staticmethod
    def is_code_available_for_customer(code, customer):
        """Prüft ob Rabattcode für Customer verfügbar ist"""
        if not code or not customer:
            return False

        today = timezone.now().date()

        return CustomerDiscountCode.objects.filter(
            pk=code.pk,
            customer=customer,
            status__in=['planned', 'sent'],
            valid_from__lte=today,
            valid_until__gte=today
        ).exists()

    @staticmethod
    def can_apply_discount(code):
        """Prüft ob Rabattcode angewendet werden kann"""
        if not code:
            return False

        today = timezone.now().date()

        return (
                code.status in ['planned', 'sent'] and
                code.valid_from <= today <= code.valid_until
        )


class DiscountDisplay:
    """Service für Rabattcode-Anzeige in Form"""

    @staticmethod
    def format_discount_info(invoice):
        """Formatiert Rabattinformationen für Anzeige"""
        if not invoice.discount_code or not invoice.discount_amount:
            return None

        return {
            'code': invoice.discount_code.code,
            'original_amount': invoice.original_amount,
            'discount_amount': invoice.discount_amount,
            'final_amount': invoice.amount,
            'discount_type': invoice.discount_code.get_discount_display()
        }

    @staticmethod
    def get_discount_summary(invoice):
        """Gibt Zusammenfassung des Rabatts zurück"""
        if not invoice.discount_code:
            return "Kein Rabatt angewendet"

        if not invoice.discount_amount:
            return f"Rabattcode {invoice.discount_code.code} vorhanden, aber kein Rabatt berechnet"

        return (
            f"Rabatt: {invoice.discount_code.code} "
            f"(-{invoice.discount_amount:.2f}€, {invoice.discount_code.get_discount_display()})"
        )