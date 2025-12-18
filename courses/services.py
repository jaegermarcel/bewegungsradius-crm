from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from django.contrib.gis.geos import Point
from workalendar.europe import Bavaria
from datetime import timedelta, time
import time as time_module
from django.utils import timezone as tz
from django_celery_beat.models import PeriodicTask, ClockedSchedule
import json
import logging

logger = logging.getLogger(__name__)


class LocationGeocoder:
    """Service für Location-Geocoding"""

    TIMEOUT = 10
    DELAY = 1
    USER_AGENT = "bewegungsradius_app"

    def __init__(self):
        self.geolocator = Nominatim(user_agent=self.USER_AGENT)

    def geocode(self, address):
        """Konvertiert Adresse in Koordinaten oder None"""
        if not address:
            return None

        try:
            time_module.sleep(self.DELAY)
            location = self.geolocator.geocode(address, timeout=self.TIMEOUT)

            if location:
                return Point(location.longitude, location.latitude, srid=4326)

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding Fehler für '{address}': {e}")

        return None


class CourseHolidayCalculator:
    """Service für Feiertagsberechnungen"""

    def __init__(self):
        self.cal = Bavaria()

    def get_holidays_in_range(self, start_date, end_date):
        """Gibt alle Feiertage im Bereich zurück"""
        if not start_date or not end_date:
            return []

        holidays = []
        for year in range(start_date.year, end_date.year + 1):
            year_holidays = self.cal.holidays(year)
            holidays.extend([
                h[0] for h in year_holidays
                if start_date <= h[0] <= end_date
            ])

        return sorted(holidays)

    def get_holidays_for_year(self, year):
        """Gibt alle Feiertage für ein Jahr zurück"""
        holidays = self.cal.holidays(year)
        return [h[0] for h in holidays]

    def is_holiday(self, date):
        """Prüft ob ein Datum ein Feiertag ist"""
        holidays = self.get_holidays_for_year(date.year)
        return date in holidays

    def get_holiday_name(self, date):
        """Gibt den Namen des Feiertags zurück oder None"""
        holidays_dict = dict(self.cal.holidays(date.year))
        return holidays_dict.get(date)

    def check_holidays_on_course_day(self, start_date, end_date, weekday):
        """Prüft ob Feiertage auf den Kurstag fallen"""
        if not start_date or not end_date or weekday is None:
            return []

        holidays = self.get_holidays_in_range(start_date, end_date)
        warnings = []

        for holiday in holidays:
            if holiday.weekday() == weekday:
                holiday_name = self.get_holiday_name(holiday)
                warnings.append({
                    'date': holiday,
                    'name': holiday_name or 'Feiertag',
                    'message': f"⚠️ {holiday.strftime('%d.%m.%Y')} ({holiday_name or 'Feiertag'}) - Kurs fällt aus"
                })

        return warnings


class CourseScheduleCalculator:
    """Service für Kursplan-Berechnungen"""

    def __init__(self):
        self.holiday_calc = CourseHolidayCalculator()

    def get_course_dates(self, start_date, end_date, weekday):
        """Gibt alle Kurstermine zurück (ohne Feiertage)"""
        holidays = set(self.holiday_calc.get_holidays_in_range(start_date, end_date))
        dates = []
        current_date = start_date

        while current_date <= end_date:
            if current_date not in holidays:
                dates.append(current_date)
            current_date += timedelta(weeks=1)

        return dates

    def get_skipped_dates_due_to_holidays(self, start_date, end_date, weekday):
        """Gibt alle Termine zurück, die wegen Feiertagen ausfallen"""
        holidays = set(self.holiday_calc.get_holidays_in_range(start_date, end_date))
        skipped_dates = []
        current_date = start_date

        while current_date <= end_date:
            if current_date in holidays:
                skipped_dates.append(current_date)
            current_date += timedelta(weeks=1)

        return skipped_dates

    def count_course_units(self, start_date, end_date, weekday):
        """Berechnet die Anzahl der Kurseinheiten (ohne Feiertage)"""
        return len(self.get_course_dates(start_date, end_date, weekday))


class CeleryTaskManager:
    """Service für Celery Task Management - mit Start + Completion Email Support"""

    EMAIL_LEAD_TIME_DAYS = 2  # 2 Tage vor Kursbeginn
    EMAIL_SEND_HOUR = 8  # 08:00 Uhr

    def get_task_name(self, course, task_type='start'):
        """
        🔧 IMPROVED: Generiert aussagekräftigen Task-Namen

        Format: "Kursstart Email - Kurstitel Zeitraum, Uhrzeit und Kursort"

        Beispiele:
        - "Kursstart Email - Pilates Grundkurs 25.11-06.12, 09:00-10:00, Studio A"
        - "Kurs-Abschluss Email - Yoga Advanced 10.11-15.12, 18:30-19:30, Online"
        """
        prefix = "Kursstart Email" if task_type == 'start' else "Kurs-Abschluss Email"

        title = course.offer.title if course.offer else "Unbekannter Kurs"

        start_date = course.start_date.strftime('%d.%m') if course.start_date else "?"
        end_date = course.end_date.strftime('%d.%m') if course.end_date else "?"
        timerange = f"{start_date}-{end_date}"

        start_time = course.start_time.strftime('%H:%M') if course.start_time else "?"
        end_time = course.end_time.strftime('%H:%M') if course.end_time else "?"
        time_str = f"{start_time}-{end_time}"

        location = course.location.name if course.location else "Online"

        task_name = f"{prefix} - {title} {timerange}, {time_str}, {location}"

        if len(task_name) > 200:
            task_name = task_name[:197] + "..."

        return task_name

    def calculate_email_send_datetime(self, start_date):
        """Berechnet Zeitpunkt für Start-Email (2 Tage vor Start um 08:00)"""
        email_send_date = start_date - timedelta(days=self.EMAIL_LEAD_TIME_DAYS)
        email_send_datetime = tz.make_aware(
            tz.datetime.combine(email_send_date, time(self.EMAIL_SEND_HOUR, 0))
        )

        # Falls Zeitpunkt in der Vergangenheit liegt, verschiebe auf jetzt + 10 Min
        now = tz.now()
        if email_send_datetime <= now:
            logger.warning(f"Start-Email Task-Zeit in Vergangenheit. Verschiebe auf jetzt + 10 Min.")
            email_send_datetime = now + timedelta(minutes=10)

        return email_send_datetime

    def calculate_completion_email_send_datetime(self, end_date, end_time):
        """✅ Berechnet Zeitpunkt für Completion-Email (Enddatum + Endzeit)"""
        if not end_time:
            # Fallback: 18:00 Uhr wenn keine Endzeit gesetzt
            end_time = time(18, 0)

        email_send_datetime = tz.make_aware(
            tz.datetime.combine(end_date, end_time)
        )

        # Falls Zeitpunkt in der Vergangenheit liegt, verschiebe auf jetzt + 10 Min
        now = tz.now()
        if email_send_datetime <= now:
            logger.warning(f"Completion-Email Task-Zeit in Vergangenheit. Verschiebe auf jetzt + 10 Min.")
            email_send_datetime = now + timedelta(minutes=10)

        return email_send_datetime

    def manage_course_start_email_task(self, course):
        """Erstellt oder aktualisiert Celery Task für Start-Email

        WICHTIG: Erstellt/aktualisiert Task NUR wenn E-Mail noch nicht versendet wurde
        """
        if not course.start_date:
            return

        # Prüfe ob E-Mail bereits versendet wurde
        if course.start_email_sent:
            logger.info(
                f"Start-E-Mail für Kurs {course.id} wurde bereits am "
                f"{course.start_email_sent_at.strftime('%d.%m.%Y %H:%M')} versendet. "
                f"Task wird NICHT erstellt/aktualisiert."
            )
            # Lösche existierende Tasks wenn E-Mail bereits versendet
            self._delete_task_if_exists(course, task_type='start')
            return

        task_name = self.get_task_name(course, task_type='start')
        email_send_datetime = self.calculate_email_send_datetime(course.start_date)

        try:
            # Hole oder erstelle ClockedSchedule
            clocked_schedule, _ = ClockedSchedule.objects.get_or_create(
                clocked_time=email_send_datetime
            )

            # Prüfe ob Task bereits existiert
            task_exists = PeriodicTask.objects.filter(name=task_name).exists()

            if task_exists:
                self._update_existing_task(task_name, clocked_schedule, email_send_datetime)
            else:
                self._create_new_task(
                    task_name,
                    course.id,
                    clocked_schedule,
                    'courses.tasks.send_course_start_email'
                )

        except Exception as e:
            logger.error(f"Fehler beim Start-Email Task Management für Kurs {course.id}: {e}")

    def manage_course_completion_email_task(self, course):
        """✅ Erstellt oder aktualisiert Celery Task für Completion-Email

        WICHTIG: Erstellt/aktualisiert Task NUR wenn E-Mail noch nicht versendet wurde
        """
        if not course.end_date:
            return

        # Prüfe ob E-Mail bereits versendet wurde
        if course.completion_email_sent:
            logger.info(
                f"Abschluss-E-Mail für Kurs {course.id} wurde bereits am "
                f"{course.completion_email_sent_at.strftime('%d.%m.%Y %H:%M')} versendet. "
                f"Task wird NICHT erstellt/aktualisiert."
            )
            # Lösche existierende Tasks wenn E-Mail bereits versendet
            self._delete_task_if_exists(course, task_type='completion')
            return

        task_name = self.get_task_name(course, task_type='completion')
        email_send_datetime = self.calculate_completion_email_send_datetime(course.end_date, course.end_time)

        try:
            # Hole oder erstelle ClockedSchedule
            clocked_schedule, _ = ClockedSchedule.objects.get_or_create(
                clocked_time=email_send_datetime
            )

            # Prüfe ob Task bereits existiert
            task_exists = PeriodicTask.objects.filter(name=task_name).exists()

            if task_exists:
                self._update_existing_task(task_name, clocked_schedule, email_send_datetime)
            else:
                self._create_new_task(
                    task_name,
                    course.id,
                    clocked_schedule,
                    'courses.tasks.send_course_completion_email'
                )

        except Exception as e:
            logger.error(f"Fehler beim Completion-Email Task Management für Kurs {course.id}: {e}")

    def _create_new_task(self, task_name, course_id, clocked_schedule, task_function):
        """Erstellt neue Celery Task"""
        PeriodicTask.objects.create(
            name=task_name,
            task=task_function,
            args=json.dumps([course_id]),
            one_off=True,
            clocked=clocked_schedule,
        )
        logger.info(f"✓ Celery Task ERSTELLT: {task_name}")

    def _update_existing_task(self, task_name, new_clocked_schedule, new_datetime):
        """Aktualisiert existierende Celery Task wenn nötig"""
        task = PeriodicTask.objects.get(name=task_name)

        if task.clocked.clocked_time != new_datetime:
            task.clocked = new_clocked_schedule
            task.save()
            logger.info(f"✓ Celery Task AKTUALISIERT: {task_name}")
        else:
            logger.debug(f"✓ Celery Task EXISTIERT: {task_name} (keine Änderung)")

    def _delete_task_if_exists(self, course, task_type='start'):
        """Löscht Task wenn vorhanden (für bereits versendete E-Mails)"""
        task_name = self.get_task_name(course, task_type=task_type)
        try:
            task = PeriodicTask.objects.get(name=task_name)
            task.delete()
            logger.info(f"✓ Task GELÖSCHT (E-Mail bereits versendet): {task_name}")
        except PeriodicTask.DoesNotExist:
            pass

    def delete_course_task(self, course):
        """✅ Löscht BEIDE Tasks (Start + Completion) für einen Kurs"""
        # Lösche Start-Email Task
        start_task_name = self.get_task_name(course, task_type='start')
        try:
            task = PeriodicTask.objects.get(name=start_task_name)
            task.delete()
            logger.info(f"✓ Start-Email Task GELÖSCHT: {start_task_name}")
        except PeriodicTask.DoesNotExist:
            pass

        # Lösche Completion-Email Task
        completion_task_name = self.get_task_name(course, task_type='completion')
        try:
            task = PeriodicTask.objects.get(name=completion_task_name)
            task.delete()
            logger.info(f"✓ Completion-Email Task GELÖSCHT: {completion_task_name}")
        except PeriodicTask.DoesNotExist:
            pass


class CourseStatusChecker:
    """Service für Kursstatus-Prüfungen"""

    @staticmethod
    def is_expired(course):
        """Prüft ob Kurs abgelaufen ist"""
        if not course.end_date:
            return False
        return course.end_date < tz.now().date()

    @staticmethod
    def is_ongoing(course):
        """Prüft ob Kurs gerade läuft"""
        today = tz.now().date()
        if not course.start_date or not course.end_date:
            return False
        return course.start_date <= today <= course.end_date

    @staticmethod
    def is_upcoming(course):
        """Prüft ob Kurs in der Zukunft liegt"""
        if not course.start_date:
            return False
        return course.start_date > tz.now().date()

    @staticmethod
    def deactivate_expired_courses():
        """Deaktiviert alle abgelaufenen Kurse"""
        from courses.models import Course

        expired_courses = Course.objects.filter(
            end_date__lt=tz.now().date(),
            is_active=True
        )

        count = expired_courses.update(is_active=False)
        logger.info(f"Deaktiviert {count} abgelaufene Kurse")
        return count


class CourseParticipantCounter:
    """Service für Teilnehmer-Zählung"""

    @staticmethod
    def get_inperson_count(course):
        """Gibt Anzahl Präsenz-Teilnehmer zurück"""
        return course.participants_inperson.count()

    @staticmethod
    def get_online_count(course):
        """Gibt Anzahl Online-Teilnehmer zurück"""
        return course.participants_online.count()

    @staticmethod
    def get_total_count(course):
        """Gibt Gesamtzahl Teilnehmer zurück"""
        return course.total_participants

    @staticmethod
    def get_available_spots_inperson(course):
        """Gibt verfügbare Präsenz-Plätze zurück"""
        if not course.location:
            return 0
        return course.location.max_participants - course.participants_inperson.count()

    @staticmethod
    def is_full_inperson(course):
        """Prüft ob Präsenz-Plätze voll sind"""
        return course.is_full_inperson

    @staticmethod
    def can_add_participant_inperson(course):
        """Prüft ob noch Präsenz-Teilnehmer hinzugefügt werden können"""
        return CourseParticipantCounter.get_available_spots_inperson(course) > 0