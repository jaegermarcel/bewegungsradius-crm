from decimal import Decimal

from django.db import models
from django.utils import timezone


class ZPPCertification(models.Model):
    """
    Modell für ZPP (Zentralstelle Prävention) Zertifizierungen
    """

    FORMAT_CHOICES = [
        ("praesenz", "Präsenz"),
        ("online", "Online"),
        ("hybrid", "Hybrid"),
    ]

    # ZPP Identifikation
    zpp_id = models.CharField(
        max_length=50, unique=True, verbose_name="ZPP-ID", help_text="Z.B. KU-BE-ZCURFS"
    )

    # Beschreibung
    name = models.CharField(
        max_length=200, verbose_name="Bezeichnung", help_text="Z.B. Pilates Präsens"
    )

    official_title = models.CharField(
        max_length=200,
        verbose_name="Offizieller Titel",
        help_text="Der offizielle Titel für die Zertifizierung",
    )

    # Format
    format = models.CharField(
        max_length=50, choices=FORMAT_CHOICES, default="praesenz", verbose_name="Format"
    )

    # Gültigkeit
    valid_from = models.DateField(default=timezone.now, verbose_name="Gültig ab")

    valid_until = models.DateField(
        verbose_name="Gültig bis", help_text="Ablaufdatum der Zertifizierung"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Nur aktive Zertifizierungen können verwendet werden",
    )

    # Notizen
    notes = models.TextField(blank=True, verbose_name="Notizen")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        ordering = ["-valid_until"]
        verbose_name = "ZPP-Zertifizierung"
        verbose_name_plural = "ZPP-Zertifizierungen"

    def __str__(self):
        return f"{self.zpp_id} - {self.name}"

    def is_valid_today(self):
        """Prüft ob die Zertifizierung heute noch gültig ist"""
        today = timezone.now().date()
        return self.is_active and self.valid_from <= today <= self.valid_until

    def days_until_expiry(self):
        """Berechnet Tage bis Ablauf"""

        today = timezone.now().date()
        if today > self.valid_until:
            return 0
        return (self.valid_until - today).days


# ============================================================
# UPDATED OFFER MODEL
# ============================================================


class Offer(models.Model):
    """
    Angebote: Kurse, 10er-Karten, Workshops, etc.
    """

    # ✅ Neue Choice: OFFER_TYPE statt course_type!
    OFFER_TYPE_CHOICES = [
        ("course", "Kurs"),
        ("ticket_10", "10er-Karte"),
        ("workshop", "Workshop"),
        ("seminar", "Seminar"),
    ]

    # Format für Kurse
    FORMAT_CHOICES = [
        ("praesenz", "Präsenz"),
        ("online", "Online"),
        ("hybrid", "Hybrid"),
    ]

    # ============ GRUNDLAGEN ============

    # ✅ Neues Feld: Art des Angebots
    offer_type = models.CharField(
        max_length=50,
        choices=OFFER_TYPE_CHOICES,
        default="course",
        verbose_name="Art des Angebots",
        help_text="Ist das ein Kurs, eine 10er-Karte, Workshop, etc.?",
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Titel",
        help_text="Z.B. 'Pilates Kurs' oder '10er-Karte Yoga'",
    )

    # ============ KURSSPEZIFISCH ============

    # Format (nur für Kurse relevant)
    format = models.CharField(
        max_length=50,
        choices=FORMAT_CHOICES,
        null=True,
        blank=True,
        verbose_name="Kurs-Format",
        help_text="Nur für Kurse: Präsenz/Online/Hybrid",
    )

    # Kursdetails (nur für Kurse relevant)
    course_units = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Anzahl Einheiten",
        help_text="Anzahl der Kurseinheiten (nur für Kurse)",
    )
    course_duration = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Dauer pro Einheit (Minuten)",
        help_text="Dauer einer Kurseinheit in Minuten (nur für Kurse)",
    )

    # ============ 10ER-KARTE SPEZIFISCH ============

    # ✅ Neue Felder für 10er-Karten
    ticket_sessions = models.IntegerField(
        default=10,
        verbose_name="Anzahl Einheiten",
        help_text="Anzahl der Einheiten auf der Karte (z.B. 10)",
    )
    ticket_validity_months = models.IntegerField(
        default=6,
        verbose_name="Gültig für (Monate)",
        help_text="Wie lange ist die Karte nach Kauf gültig? (z.B. 6 Monate)",
    )

    # ============ PREISE ============

    amount = models.DecimalField(
        max_digits=8, decimal_places=2, verbose_name="Betrag (Netto)"
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name="MwSt. (%)"
    )
    is_tax_exempt = models.BooleanField(
        default=True, verbose_name="Kleinunternehmerregelung (§19 UStG)"
    )

    # ============ ZPP ============

    # ZPP-Zertifizierung (nur für Kurse relevant)
    zpp_certification = models.ForeignKey(
        ZPPCertification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offers",
        verbose_name="ZPP-Zertifizierung",
        help_text="Nur für ZPP-zertifizierte Kurse",
    )

    # ============ SONSTIGES ============

    notes = models.TextField(blank=True, verbose_name="Notizen/Besonderheiten")

    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Inaktive Angebote werden nicht angezeigt",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Angebot"
        verbose_name_plural = "Angebote"

    def __str__(self):
        """Zeigt Titel mit Typ und wichtigen Details"""
        parts = [self.title]

        # Zeige Angebots-Typ
        parts.append(f"({self.get_offer_type_display()})")

        # Bei 10er-Karten: Anzahl Sessions
        if self.offer_type == "ticket_10":
            parts.append(f"- {self.ticket_sessions}er")

        # Bei Kursen: Format + Einheiten
        elif self.offer_type == "course":
            if self.format:
                parts.append(f"[{self.get_format_display()}]")
            if self.course_units:
                parts.append(f"- {self.course_units}x")

        # Preis
        parts.append(f"{self.total_amount}€")

        # ZPP-Indikator
        if self.zpp_certification:
            parts.append("[ZPP]")

        return " ".join(parts)

    # ============ PROPERTIES ============

    @property
    def tax_amount(self):
        """Berechnet den MwSt-Betrag"""
        if self.amount is None or self.tax_rate is None or self.is_tax_exempt:
            return Decimal("0.00")
        return (self.amount * self.tax_rate / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def total_amount(self):
        """Berechnet den Gesamtbetrag inkl. MwSt"""
        if self.amount is None:
            return Decimal("0.00")
        return (self.amount + self.tax_amount).quantize(Decimal("0.01"))

    @property
    def zpp_prevention_id(self):
        """Rückwärtskompatibilität - gibt ZPP-ID zurück"""
        return self.zpp_certification.zpp_id if self.zpp_certification else None

    # ✅ NEUE PROPERTIES - DIESE FEHLTEN!
    @property
    def is_course(self):
        """Prüft ob das ein Kurs ist"""
        return self.offer_type == "course"

    @property
    def is_ticket_10(self):
        """✅ Prüft ob das eine 10er-Karte ist"""
        return self.offer_type == "ticket_10"

    @property
    def is_workshop(self):
        """Prüft ob das ein Workshop ist"""
        return self.offer_type == "workshop"

    @property
    def is_seminar(self):
        """Prüft ob das ein Seminar ist"""
        return self.offer_type == "seminar"

    # ============ METHODS ============

    def get_price_per_session(self):
        """Berechnet Preis pro Sitzung (für 10er-Karten)"""
        if self.offer_type == "ticket_10" and self.ticket_sessions:
            return (self.total_amount / self.ticket_sessions).quantize(Decimal("0.01"))
        return self.total_amount

    def get_description(self):
        """Gibt eine ausführliche Beschreibung zurück"""
        if self.offer_type == "ticket_10":
            return f"für Gruppensportkurs (z. B. Pilates / Mama-Workout)"

        if self.offer_type == "course":
            parts = []
            if self.course_units:
                parts.append(f"{self.course_units} Einheiten")
            if self.course_duration:
                parts.append(f"à {self.course_duration} Minuten")
            if self.format:
                parts.append(f"({self.get_format_display()})")
            return " ".join(parts)

        return self.get_offer_type_display()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
