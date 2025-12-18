from django.db import models
from decimal import Decimal
from datetime import timedelta, date, datetime
from customers.models import Customer
from courses.models import Course


# ==================== Service-Klassen ====================

class InvoiceNumberGenerator:
    """Generiert eindeutige Rechnungsnummern"""

    @staticmethod
    def generate() -> str:
        """Generiert eine Rechnungsnummer im Format YYYY-XXX"""
        year = datetime.now().year
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=f"{year}-"
        ).order_by('-invoice_number').first()

        new_number = 1
        if last_invoice:
            try:
                last_number = int(last_invoice.invoice_number.split('-')[-1])
                new_number = last_number + 1
            except ValueError:
                pass

        return f"{year}-{new_number:03d}"


class CourseIdGenerator:
    """Generiert eindeutige Kurs-IDs"""

    @staticmethod
    def generate(course_type: str) -> str:
        """Generiert eine Kurs-ID im Format KU-XX-XXXXXX"""
        import random
        import string

        prefix = course_type[:2].upper()
        random_part = ''.join(random.choices(string.ascii_uppercase, k=6))
        return f"KU-{prefix}-{random_part}"


class TaxCalculator:
    """Berechnet Steuern und Gesamtbeträge"""

    def __init__(self, amount: Decimal, tax_rate: Decimal, is_tax_exempt: bool):
        self.amount = amount
        self.tax_rate = tax_rate
        self.is_tax_exempt = is_tax_exempt

    def calculate_tax_amount(self) -> Decimal:
        """Berechnet den MwSt-Betrag"""
        if self.amount is None or self.is_tax_exempt:
            return Decimal('0.00')

        tax = (self.amount * self.tax_rate / Decimal('100'))
        return tax.quantize(Decimal('0.01'))

    def calculate_total(self) -> Decimal:
        """Berechnet den Gesamtbetrag inkl. MwSt"""
        if self.amount is None:
            return Decimal('0.00')

        total = self.amount + self.calculate_tax_amount()
        return total.quantize(Decimal('0.01'))


class DiscountApplier:
    """Verwaltet und wendet Rabatte an"""

    def __init__(self, amount: Decimal, discount_code=None):
        self.amount = amount
        self.discount_code = discount_code
        self.original_amount = None
        self.discount_amount = Decimal('0.00')

    def apply(self) -> 'DiscountApplier':
        """Wendet Rabattcode an und speichert Original"""
        if self.discount_code and not self.original_amount:
            self.original_amount = self.amount
            self.discount_amount = self.discount_code.calculate_discount(self.amount)
            self.amount = self.amount - self.discount_amount

        return self

    def get_final_amount(self) -> Decimal:
        """Gibt den finalen Betrag nach Rabatt zurück"""
        return self.amount

    def get_original_amount(self) -> Decimal:
        """Gibt den Originalbetrag zurück"""
        return self.original_amount or self.amount


class InvoiceDateManager:
    """Verwaltet Rechnungsdaten"""

    @staticmethod
    def get_issue_date(issue_date) -> date:
        """Gibt das Rechnungsdatum zurück oder heute"""
        return issue_date or date.today()

    @staticmethod
    def get_due_date(due_date, issue_date) -> date:
        """Gibt das Fälligkeitsdatum zurück oder +14 Tage"""
        if due_date:
            return due_date

        actual_issue_date = InvoiceDateManager.get_issue_date(issue_date)
        return actual_issue_date + timedelta(days=14)


class InvoiceInitializer:
    """Initialisiert Invoice-Felder mit Defaults"""

    def __init__(self, invoice):
        self.invoice = invoice

    def initialize(self) -> None:
        """Setzt alle Default-Werte"""
        self._set_invoice_number()
        self._set_amount_from_offer_or_course()
        self._set_details_from_source()
        self._set_dates()

    def _set_invoice_number(self) -> None:
        if not self.invoice.invoice_number:
            self.invoice.invoice_number = InvoiceNumberGenerator.generate()

    def _set_amount_from_offer_or_course(self) -> None:
        """✅ Betrag von Course ODER Offer holen"""
        if not self.invoice.amount:
            # Versuch 1: Vom Course
            if self.invoice.course:
                course_price = self.invoice.course.price
                if course_price:
                    self.invoice.amount = course_price
                    return

            # Versuch 2: Vom Offer (für 10er-Karten)
            if self.invoice.offer:
                offer_price = self.invoice.offer.total_amount
                if offer_price:
                    self.invoice.amount = offer_price
                    return

    def _set_details_from_source(self) -> None:
        """✅ Details von Course ODER Offer holen"""
        # Aus Course
        if self.invoice.course:
            offer = self.invoice.course.offer
            if not self.invoice.course_units and offer.course_units:
                self.invoice.course_units = offer.course_units
            if not self.invoice.course_duration and offer.course_duration:
                self.invoice.course_duration = offer.course_duration
            if not self.invoice.course_id_custom:
                generator = CourseIdGenerator()
                self.invoice.course_id_custom = generator.generate(
                    self.invoice.course.course_type
                )

        # Aus Offer (für 10er-Karten)
        elif self.invoice.offer:
            if self.invoice.offer.is_ticket_10:
                if not self.invoice.course_units:
                    self.invoice.course_units = self.invoice.offer.ticket_sessions
                # Für 10er-Karten: course_id setzen
                if not self.invoice.course_id_custom:
                    generator = CourseIdGenerator()
                    self.invoice.course_id_custom = generator.generate('ticket')

    def _set_dates(self) -> None:
        self.invoice.issue_date = InvoiceDateManager.get_issue_date(
            self.invoice.issue_date
        )
        self.invoice.due_date = InvoiceDateManager.get_due_date(
            self.invoice.due_date,
            self.invoice.issue_date
        )


# ==================== Django Model ====================

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Entwurf'),
        ('sent', 'Versendet'),
        ('paid', 'Bezahlt'),
        ('overdue', 'Überfällig'),
        ('cancelled', 'Storniert'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, verbose_name="Rechnungsnummer")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices', verbose_name="Kunde")

    # ✅ GEÄNDERT: Course ist jetzt optional
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Kurs",
        null=True,
        blank=True,
        help_text="Kurs (für normale Kurse)"
    )

    # ✅ NEU: Offer (für 10er-Karten etc.)
    offer = models.ForeignKey(
        'offers.Offer',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Angebot",
        null=True,
        blank=True,
        help_text="Angebot (für 10er-Karten, Workshops, etc.)"
    )

    discount_code = models.ForeignKey(
        'customers.CustomerDiscountCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
        verbose_name="Rabattcode"
    )

    issue_date = models.DateField(verbose_name="Rechnungsdatum")
    due_date = models.DateField(verbose_name="Fälligkeitsdatum")

    course_units = models.IntegerField(verbose_name="Anzahl Kurseinheiten")
    course_duration = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Dauer pro Einheit (Minuten)"
    )
    course_id_custom = models.CharField(max_length=50, blank=True, verbose_name="Kurs-ID")

    amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Betrag (Netto)")

    original_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Originalbetrag (vor Rabatt)"
    )
    discount_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Rabattbetrag"
    )

    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="MwSt. (%)")
    is_tax_exempt = models.BooleanField(default=True, verbose_name="Kleinunternehmerregelung (§19 UStG)")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Status")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="Storniert am")
    cancelled_invoice_number = models.CharField(max_length=50, blank=True, null=True,
                                                verbose_name="Storno-Rechnungsnummer")

    is_prevention_certified = models.BooleanField(default=True, verbose_name="Zertifiziert nach § 20 SGB V")
    zpp_prevention_id = models.CharField(max_length=50, blank=True, verbose_name="ZPP Präventions-ID")

    notes = models.TextField(blank=True, verbose_name="Notizen")

    # Email Tracking
    email_sent = models.BooleanField(
        default=False,
        verbose_name="Email versendet",
        help_text="Wurde die Rechnung per Email versendet?"
    )
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Email versendet am",
        help_text="Zeitpunkt des Email-Versands"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        ordering = ['-issue_date']
        verbose_name = "Rechnung"
        verbose_name_plural = "Rechnungen"
        constraints = [
            models.CheckConstraint(
                check=models.Q(course__isnull=False) | models.Q(offer__isnull=False),
                name='invoice_has_course_or_offer'
            )
        ]

    def __str__(self):
        if self.course:
            return f"Rechnung {self.invoice_number} - {self.customer.get_full_name()} (Kurs)"
        elif self.offer:
            return f"Rechnung {self.invoice_number} - {self.customer.get_full_name()} ({self.offer.title})"
        return f"Rechnung {self.invoice_number} - {self.customer.get_full_name()}"

    def get_title(self):
        """Gibt Titel für die Rechnung zurück"""
        if self.course:
            return self.course.title
        elif self.offer:
            return self.offer.title
        return "Rechnung"

    @property
    def tax_amount(self) -> Decimal:
        """Berechnet den MwSt-Betrag"""
        calculator = TaxCalculator(self.amount, self.tax_rate, self.is_tax_exempt)
        return calculator.calculate_tax_amount()

    @property
    def total_amount(self) -> Decimal:
        """Berechnet den Gesamtbetrag inkl. MwSt"""
        calculator = TaxCalculator(self.amount, self.tax_rate, self.is_tax_exempt)
        return calculator.calculate_total()

    def apply_discount(self) -> None:
        """Wendet den Rabattcode an"""
        applier = DiscountApplier(self.amount, self.discount_code)
        applier.apply()

        self.original_amount = applier.get_original_amount()
        self.discount_amount = applier.discount_amount
        self.amount = applier.get_final_amount()

    def save(self, *args, **kwargs) -> None:
        """Speichert die Rechnung mit automatischen Defaults"""
        # ✅ Validierung: Entweder Course ODER Offer
        if not self.course and not self.offer:
            raise ValueError("Eine Rechnung muss entweder einen Kurs oder ein Angebot haben!")

            # ✅ SCHRITT 2: Initialisiere (invoice_number, amount, dates etc.)
        initializer = InvoiceInitializer(self)
        initializer.initialize()

        # ✅ SCHRITT 3: Setze original_amount BEIM ERSTEN MAL
        # (Wenn noch nicht gesetzt, kopiere von amount)
        if not self.original_amount:
            self.original_amount = self.amount

        # ✅ SCHRITT 4: Berechne discount_amount basierend auf discount_code
        # 🔴 WICHTIG: Nutze die calculate_discount() Methode vom Model!
        if self.discount_code:
            # Die calculate_discount() Methode arbeitet mit beiden Typen:
            # - percentage: amount * (value / 100)
            # - fixed: min(value, amount)
            self.discount_amount = self.discount_code.calculate_discount(self.original_amount)
        else:
            # Kein Code = Kein Rabatt
            self.discount_amount = Decimal('0.00')

        # ✅ SCHRITT 5: Berechne amount (original - discount)
        self.amount = self.original_amount - self.discount_amount

        # ✅ SCHRITT 6: Speichere
        super().save(*args, **kwargs)