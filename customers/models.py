from datetime import date

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone

from .services import AddressGeocoder, DiscountCodeGenerator, DiscountCodeValidator


class ContactChannel(models.Model):
    name = models.CharField(max_length=100, verbose_name="Name")
    slug = models.SlugField(unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        ordering = ["name"]
        verbose_name = "Kontaktkanal"
        verbose_name_plural = "Kontaktkanäle"

    def __str__(self):
        return self.name


class Customer(models.Model):

    # Persönliche Daten
    first_name = models.CharField(max_length=100, verbose_name="Vorname")
    last_name = models.CharField(max_length=100, verbose_name="Nachname")
    email = models.EmailField(unique=True, verbose_name="E-Mail")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobil")
    birthday = models.DateField(blank=True, null=True, verbose_name="Geburtstag")

    # Adressdaten
    street = models.CharField(max_length=200, verbose_name="Straße")
    house_number = models.CharField(max_length=10, verbose_name="Hausnummer")
    postal_code = models.CharField(max_length=10, verbose_name="PLZ")
    city = models.CharField(max_length=100, verbose_name="Stadt")
    country = models.CharField(
        max_length=100, default="Deutschland", verbose_name="Land"
    )

    # Geografische Koordinaten
    coordinates = gis_models.PointField(
        null=True, blank=True, verbose_name="Koordinaten", srid=4326
    )
    contact_channel = models.ForeignKey(
        ContactChannel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
        verbose_name="Kontaktkanal",
    )

    # Zusätzliche Informationen
    notes = models.TextField(blank=True, verbose_name="Notizen")

    # Status
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    archived_at = models.DateTimeField(
        blank=True, null=True, verbose_name="Archiviert am"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kunde"
        verbose_name_plural = "Kunden"

    def __str__(self):
        return self.get_full_name()

    def get_full_address(self):
        """Gibt die vollständige Adresse zurück"""
        parts = [
            f"{self.street} {self.house_number}".strip(),
            f"{self.postal_code} {self.city}".strip(),
            self.country,
        ]
        return ", ".join([p for p in parts if p])

    def get_full_name(self):
        """Gibt den vollständigen Namen zurück"""
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        """Geocodiert Adresse wenn nötig"""
        if self._should_geocode():
            geocoder = AddressGeocoder()
            self.coordinates = geocoder.geocode(self.get_full_address())
        super().save(*args, **kwargs)

    def _should_geocode(self):
        """Prüft ob Geocoding durchgeführt werden sollte"""
        # ✅ Basis-Check: Sind Pflichtfelder vorhanden?
        if not self.street or not self.city:
            return False

        # ✅ KEY: Wenn Koordinaten BEREITS existieren: NICHT geocodieren!
        if self.coordinates:
            return False

        # ✅ Wenn neu: geocodieren
        if not self.pk:
            return True

        # ✅ Wenn Adresse sich GEÄNDERT hat: re-geocodieren
        if self._address_has_changed():
            return True

        return False

    def _address_has_changed(self):
        """Prüft ob die Adresse sich geändert hat"""
        if not self.pk:
            return False

        try:
            old_instance = Customer.objects.get(pk=self.pk)
            old_address = old_instance.get_full_address()
            new_address = self.get_full_address()

            changed = old_address != new_address

            if changed:
                import logging

                logger = logging.getLogger(__name__)
                logger.info(f"[GEOCODING] Address changed for {self.get_full_name()}")
                logger.info(f"   Old: {old_address}")
                logger.info(f"   New: {new_address}")

            return changed
        except Customer.DoesNotExist:
            return True


class CustomerDiscountCode(models.Model):
    """Kundenspezifischer Rabattcode"""

    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Prozent"),
        ("fixed", "Fester Betrag"),
    ]

    REASON_CHOICES = [
        ("birthday", "Geburtstag"),
        ("course_completed", "Kurs abgeschlossen"),
        ("referral", "Empfehlung"),
        ("loyalty", "Treueprämie"),
        ("other", "Sonstiges"),
    ]

    STATUS_CHOICES = [
        ("planned", "Geplant"),
        ("sent", "Versendet"),
        ("used", "Eingelöst"),
        ("expired", "Abgelaufen"),
        ("cancelled", "Storniert"),
    ]

    # Verknüpfung zum Kunden
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="discount_codes",
        verbose_name="Kunde",
    )

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="discount_codes",
        verbose_name="Kurs",
        null=True,
        blank=True,
    )

    # Rabattcode
    code = models.CharField(max_length=50, unique=True, verbose_name="Code")

    # Rabatt-Details
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default="percentage",
        verbose_name="Rabatt-Typ",
    )

    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Rabattwert"
    )

    # Grund für den Rabatt
    reason = models.CharField(
        max_length=50, choices=REASON_CHOICES, default="other", verbose_name="Grund"
    )

    description = models.TextField(blank=True, verbose_name="Beschreibung")

    # Gültigkeit (nur Datum, keine Uhrzeit)
    valid_from = models.DateField(default=date.today, verbose_name="Gültig von")

    valid_until = models.DateField(verbose_name="Gültig bis")

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="planned", verbose_name="Status"
    )

    # Verwendung (Timestamps für Historie)
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Verwendet am")

    # E-Mail-Versand (Timestamps für Historie)
    email_sent_at = models.DateTimeField(
        null=True, blank=True, verbose_name="E-Mail versendet am"
    )

    # Stornierung (Timestamps für Historie)
    cancelled_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Storniert am"
    )

    cancelled_reason = models.TextField(blank=True, verbose_name="Stornierungsgrund")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")

    created_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Erstellt von",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Rabattcode"
        verbose_name_plural = "Rabattcodes"

    def __str__(self):
        return f"{self.code} - {self.customer.get_full_name()}"

    def is_valid(self):
        """Prüft ob der Code gültig und verwendbar ist"""
        validator = DiscountCodeValidator(self)
        return validator.validate()

    def calculate_discount(self, amount):
        """Berechnet den Rabattbetrag"""
        if self.discount_type == "percentage":
            return amount * (self.discount_value / 100)
        return min(self.discount_value, amount)

    def use_code(self):
        """Markiert den Code als verwendet"""
        self.status = "used"
        self.used_at = timezone.now()
        self.save()

    def get_discount_display(self):
        """Formatierte Rabattanzeige"""
        if self.discount_type == "percentage":
            return f"{self.discount_value}%"
        return f"{self.discount_value}€"

    def get_status(self):
        """Gibt den aktuellen Status zurück"""
        return self.status

    @staticmethod
    def generate_course_code(course, customer):
        """Generiert einen kursspezifischen Code"""
        generator = DiscountCodeGenerator()
        return generator.generate(course, customer)
