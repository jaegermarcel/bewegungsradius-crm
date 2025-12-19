from django.contrib.gis.db import models as gis_models
from django.db import models

from offers.models import Offer

from .services import (CeleryTaskManager, CourseHolidayCalculator,
                       CourseScheduleCalculator, LocationGeocoder)


class Location(models.Model):
    name = models.CharField(max_length=200, verbose_name="Standort-Name")
    street = models.CharField(max_length=200, blank=True, verbose_name="Straße")
    house_number = models.CharField(
        max_length=10, blank=True, verbose_name="Hausnummer"
    )
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="PLZ")
    city = models.CharField(max_length=100, blank=True, verbose_name="Stadt")
    max_participants = models.PositiveIntegerField(
        default=10, verbose_name="Max. Teilnehmer (Präsenz)"
    )
    notes = models.TextField(blank=True, verbose_name="Notizen")

    # Geografische Koordinaten
    coordinates = gis_models.PointField(
        null=True, blank=True, verbose_name="Koordinaten", srid=4326
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        ordering = ["name"]
        verbose_name = "Kursort"
        verbose_name_plural = "Kursorte"

    def __str__(self):
        return f"{self.name} (max. {self.max_participants} Teilnehmer)"

    def get_full_address(self):
        parts = [
            f"{self.street} {self.house_number}".strip(),
            f"{self.postal_code} {self.city}".strip(),
        ]
        return ", ".join([p for p in parts if p])

    def save(self, *args, **kwargs):
        """Geocodiert Adresse wenn nötig"""
        if self._should_geocode():
            geocoder = LocationGeocoder()
            self.coordinates = geocoder.geocode(self.get_full_address())
        super().save(*args, **kwargs)

    def _should_geocode(self):
        """Prüft ob Geocoding durchgeführt werden sollte"""
        return self.street and self.city and not self.coordinates


class Course(models.Model):
    WEEKDAY_CHOICES = [
        (0, "Montag"),
        (1, "Dienstag"),
        (2, "Mittwoch"),
        (3, "Donnerstag"),
        (4, "Freitag"),
        (5, "Samstag"),
        (6, "Sonntag"),
    ]

    # Referenz zum Angebot
    offer = models.ForeignKey(
        Offer, on_delete=models.PROTECT, related_name="courses", verbose_name="Angebot"
    )

    start_date = models.DateField(verbose_name="Startdatum")
    end_date = models.DateField(blank=True, null=True, verbose_name="Enddatum")
    start_time = models.TimeField(
        blank=True, null=True, verbose_name="Startzeit", help_text="Z.B. 10:00 Uhr"
    )
    end_time = models.TimeField(
        blank=True, null=True, verbose_name="Endzeit", help_text="Z.B. 10:00 Uhr"
    )

    is_weekly = models.BooleanField(
        default=True, verbose_name="Wöchentlich wiederkehrend"
    )
    weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        verbose_name="Wochentag",
        editable=False,
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name="Kursort",
    )

    participants_inperson = models.ManyToManyField(
        "customers.Customer",
        related_name="courses_inperson",
        blank=True,
        verbose_name="Teilnehmer (Präsenz)",
    )
    participants_online = models.ManyToManyField(
        "customers.Customer",
        related_name="courses_online",
        blank=True,
        verbose_name="Teilnehmer (Online)",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Inaktive Kurse werden nicht in der Hauptliste angezeigt",
    )

    # E-Mail Tracking
    start_email_sent = models.BooleanField(
        default=False,
        verbose_name="Start-E-Mail versendet",
        help_text="Wurde die Kursstart-E-Mail an die Teilnehmer versendet?",
    )
    start_email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Start-E-Mail versendet am",
        help_text="Zeitpunkt des Versands der Kursstart-E-Mail",
    )

    completion_email_sent = models.BooleanField(
        default=False,
        verbose_name="Abschluss-E-Mail versendet",
        help_text="Wurde die Kursabschluss-E-Mail an die Teilnehmer versendet?",
    )
    completion_email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Abschluss-E-Mail versendet am",
        help_text="Zeitpunkt des Versands der Kursabschluss-E-Mail",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Kurs"
        verbose_name_plural = "Kurse"

    def __str__(self):
        return f"{self.offer.title} - {self.start_date.strftime('%d.%m.%Y')}"

    # Properties die Daten vom Offer holen
    @property
    def title(self):
        """Titel vom Angebot"""
        return self.offer.title

    @property
    def course_type(self):
        """Kurstyp vom Angebot"""
        return self.offer.offer_type

    @property
    def is_zpp_certified(self):
        """ZPP-Zertifizierung vom Angebot"""
        return bool(self.offer.zpp_prevention_id)

    @property
    def zpp_prevention_id(self):
        """ZPP-ID vom Angebot"""
        return self.offer.zpp_prevention_id

    @property
    def price(self):
        """Preis vom Angebot"""
        return self.offer.total_amount

    @property
    def max_participants_inperson(self):
        """Gibt die maximale Teilnehmerzahl der Location zurück"""
        return self.location.max_participants if self.location else 0

    @property
    def is_full_inperson(self):
        """Prüft ob Präsenzplätze voll sind"""
        if not self.location:
            return False
        return self.participants_inperson.count() >= self.location.max_participants

    @property
    def total_participants(self):
        """Gesamtzahl aller Teilnehmer"""
        return self.participants_inperson.count() + self.participants_online.count()

    # Delegiert an Services
    def get_holidays_in_range(self):
        """Gibt alle Feiertage im Kurszeitraum zurück"""
        calculator = CourseHolidayCalculator()
        return calculator.get_holidays_in_range(self.start_date, self.end_date)

    def get_course_dates(self):
        """Gibt alle Kurstermine zurück (ohne Feiertage)"""
        if not self.is_weekly or not self.start_date or not self.end_date:
            return [self.start_date] if self.start_date else []

        schedule_calc = CourseScheduleCalculator()
        return schedule_calc.get_course_dates(
            self.start_date, self.end_date, self.weekday
        )

    def get_skipped_dates_due_to_holidays(self):
        """Gibt alle Termine zurück, die wegen Feiertagen ausfallen"""
        if not self.is_weekly or not self.start_date or not self.end_date:
            return []

        schedule_calc = CourseScheduleCalculator()
        return schedule_calc.get_skipped_dates_due_to_holidays(
            self.start_date, self.end_date, self.weekday
        )

    def get_total_course_units(self):
        """Berechnet die tatsächliche Anzahl der Kurseinheiten (ohne Feiertage)"""
        if not self.is_weekly:
            return 1
        return len(self.get_course_dates())

    def check_holidays_on_course_day(self):
        """Prüft ob Feiertage auf den Kurstag fallen"""
        holiday_calc = CourseHolidayCalculator()
        return holiday_calc.check_holidays_on_course_day(
            self.start_date, self.end_date, self.weekday
        )

    def deactivate_if_expired(self):
        """Deaktiviert den Kurs wenn Enddatum vorbei ist"""
        from django.utils import timezone

        if self.end_date and self.end_date < timezone.now().date() and self.is_active:
            self.is_active = False
            self.save()
            return True
        return False

    def mark_start_email_sent(self):
        """Markiert Start-E-Mail als versendet"""
        from django.utils import timezone

        self.start_email_sent = True
        self.start_email_sent_at = timezone.now()
        self.save(update_fields=["start_email_sent", "start_email_sent_at"])

    def mark_completion_email_sent(self):
        """Markiert Abschluss-E-Mail als versendet"""
        from django.utils import timezone

        self.completion_email_sent = True
        self.is_active = False
        self.completion_email_sent_at = timezone.now()
        self.save(update_fields=["completion_email_sent", "completion_email_sent_at"])

    @property
    def email_status_display(self):
        """Gibt E-Mail Status für Admin-Anzeige zurück"""
        status = []
        if self.start_email_sent:
            status.append(f"Start: ✓ ({self.start_email_sent_at.strftime('%d.%m.%Y')})")
        else:
            status.append("Start: ✗")

        if self.completion_email_sent:
            status.append(
                f"Abschluss: ✓ ({self.completion_email_sent_at.strftime('%d.%m.%Y')})"
            )
        else:
            status.append("Abschluss: ✗")

        return " | ".join(status)

    def save(self, *args, **kwargs):
        # Wochentag berechnen
        if self.start_date:
            self.weekday = self.start_date.weekday()

        # Model speichern
        super().save(*args, **kwargs)

        task_manager = CeleryTaskManager()

        if self.start_date:
            task_manager.manage_course_start_email_task(self)

        if self.end_date:
            task_manager.manage_course_completion_email_task(self)

    def delete(self, *args, **kwargs):
        task_manager = CeleryTaskManager()
        task_manager.delete_course_task(self)
        super().delete(*args, **kwargs)
