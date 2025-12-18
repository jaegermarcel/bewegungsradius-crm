"""
courses/tasks.py - Celery Tasks für Kurs-Emails
===============================================
Tasks sind dünne Wrapper um Email Services
Alle Geschäftslogik ist in email_services/ (wartbar + testbar)
"""

from celery import shared_task
from django.utils import timezone
import logging

from .email_services.course_emails import CourseStartEmailService, CourseCompletionEmailService
from .models import Course
from company.models import CompanyInfo

logger = logging.getLogger(__name__)


# ============================================================================
# CELERY TASKS
# ============================================================================

@shared_task
def send_course_start_email(course_id):
    """
    Celery Task: Versendet Kurs-Start-Emails
    Wird automatisch 2 Tage vor Kursbeginn geplant

    Prüft ob E-Mail bereits versendet wurde (Tracking)
    """
    try:
        # Lade Kurs
        course = Course.objects.get(id=course_id)

        # Prüfe ob E-Mail bereits versendet wurde
        if course.start_email_sent:
            logger.info(
                f"Start-E-Mail für Kurs {course_id} wurde bereits am "
                f"{course.start_email_sent_at.strftime('%d.%m.%Y %H:%M')} versendet. Überspringe."
            )
            return {
                'sent': 0,
                'errors': 0,
                'course': course.title,
                'skipped': True,
                'reason': f'Bereits versendet am {course.start_email_sent_at.strftime("%d.%m.%Y %H:%M")}'
            }

        # Hole alle Teilnehmer (Präsenz + Online)
        participants = list(course.participants_inperson.all()) + list(course.participants_online.all())

        if not participants:
            logger.warning(f"Keine Teilnehmer für Kurs {course_id} gefunden")
            return {
                'sent': 0,
                'errors': 0,
                'course': course.title,
                'skipped': True,
                'reason': 'Keine Teilnehmer'
            }

        # Versende E-Mails via Service
        service = CourseStartEmailService(CompanyInfo.get_solo())
        result = service.send_course_start_email(course)

        # Markiere E-Mail als versendet wenn erfolgreich
        if result.get('sent', 0) > 0:
            course.start_email_sent = True
            course.start_email_sent_at = timezone.now()
            course.save()
            logger.info(f"✓ Start-E-Mail für Kurs {course_id} erfolgreich versendet und markiert")

        return result

    except Course.DoesNotExist:
        logger.error(f"Kurs {course_id} nicht gefunden")
        return {
            'sent': 0,
            'errors': 1,
            'error': f'Kurs {course_id} nicht gefunden'
        }
    except Exception as e:
        logger.error(f"❌ Kritischer Fehler beim Versand von Start-Email: {e}")
        return {
            'sent': 0,
            'errors': 1,
            'error': str(e)
        }


@shared_task
def send_course_completion_email(course_id):
    """
    ✅ Celery Task: Versendet Kurs-Abschluss-Emails
    Wird automatisch am Enddatum + Endzeit geplant

    Prüft ob E-Mail bereits versendet wurde (Tracking)
    """
    try:
        # Lade Kurs
        course = Course.objects.get(id=course_id)

        # Prüfe ob E-Mail bereits versendet wurde
        if course.completion_email_sent:
            logger.info(
                f"Abschluss-E-Mail für Kurs {course_id} wurde bereits am "
                f"{course.completion_email_sent_at.strftime('%d.%m.%Y %H:%M')} versendet. Überspringe."
            )
            return {
                'sent': 0,
                'errors': 0,
                'course': course.title,
                'skipped': True,
                'reason': f'Bereits versendet am {course.completion_email_sent_at.strftime("%d.%m.%Y %H:%M")}'
            }

        # Hole alle Teilnehmer (Präsenz + Online)
        participants = list(course.participants_inperson.all()) + list(course.participants_online.all())

        if not participants:
            logger.warning(f"Keine Teilnehmer für Kurs {course_id} gefunden")
            return {
                'sent': 0,
                'errors': 0,
                'course': course.title,
                'skipped': True,
                'reason': 'Keine Teilnehmer'
            }

        # Versende E-Mails via Service
        service = CourseCompletionEmailService(CompanyInfo.get_solo())
        result = service.send_course_completion_email(course)

        # Markiere E-Mail als versendet wenn erfolgreich
        if result.get('sent', 0) > 0:
            course.completion_email_sent = True
            course.is_active = False
            course.completion_email_sent_at = timezone.now()
            course.save()
            logger.info(f"✓ Abschluss-E-Mail für Kurs {course_id} erfolgreich versendet und markiert")

        return result

    except Course.DoesNotExist:
        logger.error(f"Kurs {course_id} nicht gefunden")
        return {
            'sent': 0,
            'errors': 1,
            'error': f'Kurs {course_id} nicht gefunden'
        }
    except Exception as e:
        logger.error(f"❌ Kritischer Fehler beim Versand von Completion-Email: {e}")
        return {
            'sent': 0,
            'errors': 1,
            'error': str(e)
        }