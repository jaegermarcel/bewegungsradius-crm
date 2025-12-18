

import logging
from datetime import date
from typing import Optional

from django.db.models.signals import m2m_changed, pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from customers.models import Customer
from courses.models import Course
from .models import Invoice

# ✅ KORREKT: Relativer Import oder try-except
try:
    from .pdf_service import PdfServiceFactory, PdfGenerationError
except ImportError:
    # Falls in separatem Modul
    try:
        from pdf_service import PdfServiceFactory, PdfGenerationError
    except ImportError:
        # Fallback wenn Module nicht vorhanden
        PdfServiceFactory = None
        PdfGenerationError = Exception

logger = logging.getLogger(__name__)


# ==================== Exception Classes ====================

class InvoiceSignalError(Exception):
    """Fehler bei Invoice Signal-Handling"""
    pass


class InvoiceCreationError(InvoiceSignalError):
    """Fehler beim Erstellen einer Rechnung"""
    pass


class InvoiceCancellationError(InvoiceSignalError):
    """Fehler beim Stornieren einer Rechnung"""
    pass


# ==================== Invoice Creation Service ====================

class InvoiceCreator:
    """Erstellt automatisch Rechnungen für Teilnehmer"""

    def __init__(self):
        self.logger = logger

    def create_for_participant(
            self,
            customer: Customer,
            course: Course,
            course_type: str = 'in-person'
    ) -> Optional[Invoice]:
        """
        Erstellt Rechnung für Teilnehmer

        Args:
            customer: Customer-Instanz
            course: Course-Instanz
            course_type: 'in-person' oder 'online'

        Returns:
            Erstellte Invoice oder None wenn bereits existiert

        Raises:
            InvoiceCreationError: Wenn Erstellung fehlschlägt
        """
        try:
            # Validierung
            self._validate_inputs(customer, course)

            # Prüfe ob bereits existiert
            if self._invoice_exists(customer, course):
                self.logger.info(
                    f"Invoice existiert bereits für {customer.id} / {course.id}"
                )
                return None

            # Prüfe ob Preis vorhanden
            if not course.price:
                self.logger.warning(
                    f"Kein Preis für Kurs {course.id}, Invoice nicht erstellt"
                )
                return None

            # Erstelle Invoice
            invoice = self._create_invoice(customer, course, course_type)

            self.logger.info(
                f"Invoice erstellt: {invoice.invoice_number} für {customer.get_full_name()}"
            )

            return invoice

        except Exception as e:
            self.logger.error(f"Fehler beim Invoice erstellen: {e}")
            raise InvoiceCreationError(f"Invoice-Erstellung fehlgeschlagen: {e}")

    def _validate_inputs(self, customer: Customer, course: Course) -> None:
        """Validiert Input-Parameter"""
        if not customer or not customer.pk:
            raise InvoiceCreationError("Customer ungültig")

        if not course or not course.pk:
            raise InvoiceCreationError("Course ungültig")

    def _invoice_exists(self, customer: Customer, course: Course) -> bool:
        """Prüft ob Invoice bereits existiert"""
        return Invoice.objects.filter(
            customer=customer,
            course=course
        ).exists()

    def _create_invoice(
            self,
            customer: Customer,
            course: Course,
            course_type: str
    ) -> Invoice:
        """Erstellt neue Invoice"""
        invoice = Invoice.objects.create(
            customer=customer,
            course=course,
            amount=course.price,
            issue_date=date.today(),
            is_prevention_certified=course.is_zpp_certified,
            zpp_prevention_id=(
                course.zpp_prevention_id if course.is_zpp_certified else ''
            ),
            notes=self._generate_notes(course, course_type)
        )

        return invoice

    @staticmethod
    def _generate_notes(course: Course, course_type: str) -> str:
        """Generiert Notizen für Invoice"""
        type_label = 'Präsenz' if course_type == 'in-person' else 'Online'
        return f"Rechnung für Kurs: {course.title} ({type_label})"


# ==================== Invoice Cancellation Service ====================

class InvoiceCancellationHandler:
    """Handhabt Stornierung von Rechnungen"""

    def __init__(self):
        self.logger = logger

    def handle_cancellation(self, invoice: Invoice) -> None:
        """
        Handhabt komplette Stornierung einer Rechnung

        Args:
            invoice: Zu stornierende Invoice

        Raises:
            InvoiceCancellationError: Bei Fehler
        """
        try:
            # Schritt 1: Setze Stornierung-Metadaten
            self._set_cancellation_metadata(invoice)

            # Schritt 2: Entferne Teilnehmer aus Kurs
            self._remove_participant_from_course(invoice)

            # Schritt 3: Gebe Rabattcode frei
            self._release_discount_code(invoice)

            # Schritt 4: Generiere Storno-PDF
            self._generate_cancellation_pdf(invoice)

            self.logger.info(
                f"Stornierung abgeschlossen: {invoice.invoice_number}"
            )

        except Exception as e:
            self.logger.error(f"Fehler bei Stornierung: {e}")
            raise InvoiceCancellationError(f"Stornierung fehlgeschlagen: {e}")

    def _set_cancellation_metadata(self, invoice: Invoice) -> None:
        """Setzt Stornierungsmetadaten"""
        if not invoice.cancelled_at:
            invoice.cancelled_at = timezone.now()

        if not invoice.cancelled_invoice_number:
            invoice.cancelled_invoice_number = invoice.invoice_number

        self.logger.info(f"Stornierungsmetadaten gesetzt: {invoice.invoice_number}")

    def _remove_participant_from_course(self, invoice: Invoice) -> None:
        """Entfernt Teilnehmer aus Kurs"""
        customer = invoice.customer
        course = invoice.course

        removed_count = 0

        # Aus Präsenz-Liste entfernen
        if customer in course.participants_inperson.all():
            course.participants_inperson.remove(customer)
            removed_count += 1
            self.logger.info(
                f"Teilnehmer {customer.get_full_name()} aus Präsenz entfernt"
            )

        # Aus Online-Liste entfernen
        if customer in course.participants_online.all():
            course.participants_online.remove(customer)
            removed_count += 1
            self.logger.info(
                f"Teilnehmer {customer.get_full_name()} aus Online entfernt"
            )

        if removed_count == 0:
            self.logger.warning(
                f"Teilnehmer war in keiner Liste: {customer.get_full_name()}"
            )

    def _release_discount_code(self, invoice: Invoice) -> None:
        """Gibt Rabattcode frei"""
        if not invoice.discount_code:
            return

        try:
            discount_code = invoice.discount_code
            discount_code.is_used = False
            discount_code.used_at = None
            discount_code.save()

            self.logger.info(
                f"Rabattcode freigegeben: {discount_code.code}"
            )

        except Exception as e:
            self.logger.error(f"Fehler beim Rabattcode freigeben: {e}")
            raise

    def _generate_cancellation_pdf(self, invoice: Invoice) -> None:
        """Generiert Storno-PDF"""
        if not PdfServiceFactory:
            self.logger.warning("PdfServiceFactory nicht verfügbar, überspringe PDF-Generierung")
            return

        try:
            service = PdfServiceFactory.create()
            pdf_bytes, results = service.generate_and_save_cancellation(invoice)

            self.logger.info(
                f"Storno-PDF generiert: {invoice.invoice_number} ({len(pdf_bytes)} bytes)"
            )

        except Exception as e:
            self.logger.error(f"Fehler bei Storno-PDF-Generierung: {e}")
            # Stornierung sollte auch ohne PDF fortgesetzt werden


# ==================== Participant Tracker ====================

class ParticipantChangeTracker:
    """Trackt Änderungen an Teilnehmerlisten"""

    VALID_ACTIONS = ['post_add', 'post_remove', 'post_clear']

    def __init__(self):
        self.logger = logger

    def is_valid_action(self, action: str) -> bool:
        """Prüft ob Action relevant ist"""
        return action in self.VALID_ACTIONS

    def get_affected_customer_ids(self, pk_set, action: str) -> set:
        """Gibt betroffene Customer-IDs zurück"""
        if action == 'post_add':
            return pk_set

        # post_remove und post_clear werden nicht behandelt
        return set()


# ==================== Signal Handlers ====================

@receiver(m2m_changed, sender=Course.participants_inperson.through)
def handle_inperson_participants_changed(sender, instance, action, pk_set, **kwargs):
    """Signal: Teilnehmer zu Präsenz-Kurs hinzugefügt"""
    try:
        tracker = ParticipantChangeTracker()

        if not tracker.is_valid_action(action):
            return

        customer_ids = tracker.get_affected_customer_ids(pk_set, action)

        if not customer_ids:
            return

        creator = InvoiceCreator()

        for customer_id in customer_ids:
            try:
                customer = Customer.objects.get(pk=customer_id)
                creator.create_for_participant(
                    customer=customer,
                    course=instance,
                    course_type='in-person'
                )

            except Customer.DoesNotExist:
                logger.error(f"Customer nicht gefunden: {customer_id}")
                continue

            except InvoiceCreationError as e:
                logger.error(f"Invoice-Fehler für {customer_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Kritischer Fehler in Präsenz-Signal: {e}", exc_info=True)


@receiver(m2m_changed, sender=Course.participants_online.through)
def handle_online_participants_changed(sender, instance, action, pk_set, **kwargs):
    """Signal: Teilnehmer zu Online-Kurs hinzugefügt"""
    try:
        tracker = ParticipantChangeTracker()

        if not tracker.is_valid_action(action):
            return

        customer_ids = tracker.get_affected_customer_ids(pk_set, action)

        if not customer_ids:
            return

        creator = InvoiceCreator()

        for customer_id in customer_ids:
            try:
                customer = Customer.objects.get(pk=customer_id)
                creator.create_for_participant(
                    customer=customer,
                    course=instance,
                    course_type='online'
                )

            except Customer.DoesNotExist:
                logger.error(f"Customer nicht gefunden: {customer_id}")
                continue

            except InvoiceCreationError as e:
                logger.error(f"Invoice-Fehler für {customer_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Kritischer Fehler in Online-Signal: {e}", exc_info=True)


@receiver(pre_save, sender=Invoice)
def handle_invoice_status_change(sender, instance, **kwargs):
    """Signal: Invoice wird vor dem Speichern validiert"""
    try:
        # Nur bei Änderungen relevant
        if not instance.pk:
            return

        old_invoice = Invoice.objects.get(pk=instance.pk)

        # Prüfe auf Statuswechsel zu 'cancelled'
        is_being_cancelled = (
                old_invoice.status != 'cancelled' and
                instance.status == 'cancelled'
        )

        if is_being_cancelled:
            handler = InvoiceCancellationHandler()
            handler._set_cancellation_metadata(instance)

            logger.info(f"Invoice wird storniert: {instance.invoice_number}")

    except Invoice.DoesNotExist:
        # Neue Invoice, nichts zu tun
        pass

    except Exception as e:
        logger.error(f"Fehler in pre_save Signal: {e}", exc_info=True)


@receiver(post_save, sender=Invoice)
def handle_invoice_cancellation_complete(sender, instance, created, **kwargs):
    """Signal: Nach Speicherung - Stornierung abgeschlossen"""
    try:
        # Nur bei Änderungen relevant
        if created:
            return

        # Prüfe ob gerade storniert wurde
        if instance.status != 'cancelled':
            return

        # Nur einmal verarbeiten
        if not instance.cancelled_at:
            return

        # Führe Stornierungslogik aus
        handler = InvoiceCancellationHandler()

        # Überspringe _set_cancellation_metadata (bereits in pre_save gemacht)
        handler._remove_participant_from_course(instance)
        handler._release_discount_code(instance)
        handler._generate_cancellation_pdf(instance)

        logger.info(f"Post-Save Stornierung abgeschlossen: {instance.invoice_number}")

    except InvoiceCancellationError as e:
        logger.error(f"Stornierungsfehler: {e}")

    except Exception as e:
        logger.error(f"Kritischer Fehler in post_save Signal: {e}", exc_info=True)