"""
customers/admin.py - REFACTORED
================================
Mit centralized admin_styles
"""

from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from leaflet.admin import LeafletGeoAdminMixin
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminSelect2Widget

from bewegungsradius.core.admin_styles import Colors  # Zentrale Farben
from bewegungsradius.core.admin_styles import SimpleText  # Verschiedene Helper
from bewegungsradius.core.admin_styles import (  # Pre-made Status (3 Varianten)
    DisplayHelpers, StatusIndicator)
from courses.models import Course

from .address_validator import CustomerAdminValidationMixin
from .models import ContactChannel, Customer, CustomerDiscountCode

# ========================================
# SERVICES (Business Logic)
# ========================================


class DiscountCodeEmailService:
    """Service für Rabattcode-E-Mail-Versand"""

    def __init__(self, company_info):
        self.company_info = company_info

    def send_single_email(self, discount_code):
        """Sendet E-Mail für einzelnen Code"""
        customer = discount_code.customer

        if not customer.email:
            raise ValueError(f"{customer.get_full_name()} hat keine E-Mail-Adresse")

        html_content = self._render_template(customer, discount_code)
        subject = self._build_subject(discount_code)

        self._send_email(subject, html_content, customer.email)

        discount_code.status = "sent"
        discount_code.email_sent_at = timezone.now()
        discount_code.save()

    def send_bulk_emails(self, discount_codes):
        """Sendet E-Mails für mehrere Codes - gibt (erfolg, fehler) zurück"""
        success, errors = 0, []

        for code in discount_codes:
            try:
                self.send_single_email(code)
                success += 1
            except Exception as e:
                errors.append((code.customer.get_full_name(), str(e)))

        return success, errors

    def _render_template(self, customer, discount_code):
        """Template rendern"""
        from django.template.loader import render_to_string

        return render_to_string(
            "email/notifications/discount_notification.html",
            {
                "customer": customer,
                "discount_code": discount_code,
                "company": self.company_info,
            },
        )

    def _build_subject(self, discount_code):
        """Subject-Zeile bauen"""
        discount_text = (
            f"{int(discount_code.discount_value)}%"
            if discount_code.discount_type == "percentage"
            else f"{discount_code.discount_value:.2f}€"
        )
        return f"Dein {discount_text} Rabattcode für {self.company_info.name}"

    def _send_email(self, subject, html_content, to_email):
        """E-Mail versenden"""
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives

        from_email = self.company_info.email or settings.DEFAULT_FROM_EMAIL

        email = EmailMultiAlternatives(
            subject=subject,
            body=f"Hallo,\n\nDein Rabattcode ist verfügbar.\n\nViele Grüße,\nKathrin Jäger",
            from_email=from_email,
            to=[to_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()


class CustomerService:
    """Service für Kunden-Operationen"""

    @staticmethod
    def geocode_customers(customers):
        """Geocodiert mehrere Kunden"""
        success, errors = 0, 0

        for customer in customers:
            if not customer.coordinates and customer.street and customer.city:
                if customer.geocode_address():
                    customer.save()
                    success += 1
                else:
                    errors += 1

        return success, errors


class CustomerDiscountCodeAdminForm(forms.ModelForm):
    """Custom Form: Schöner Customer-Dropdown mit Select2"""

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=True,
        empty_label="— Keine Kundin ausgewählt —",
        widget=UnfoldAdminSelect2Widget(),  # ← UNFOLD DROPDOWN!
        label="Kunde",
    )

    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        empty_label="— Keinen Kurs ausgewählt —",
        widget=UnfoldAdminSelect2Widget(),
        label="Kurs",
    )

    status = forms.ChoiceField(
        choices=CustomerDiscountCode._meta.get_field("status").choices,
        required=True,
        widget=UnfoldAdminSelect2Widget(),  # ← UNFOLD DROPDOWN!
        label="Status",
    )

    class Meta:
        model = CustomerDiscountCode
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optionale Anpassung der Queryset Label
        self.fields["customer"].label_from_instance = (
            lambda obj: f"{obj.get_full_name()} ({obj.email})"
        )


# ========================================
# ADMIN CLASSES
# ========================================


@admin.register(Customer)
class CustomerAdmin(CustomerAdminValidationMixin, LeafletGeoAdminMixin, ModelAdmin):
    list_display = [
        "display_as_two_line_heading",
        "address",
        "age",
        "birthday_with_muted",
        "course_stats",
        "invoice_stats",
        "is_active_display",
    ]
    list_display_links = ["display_as_two_line_heading"]
    search_fields = [
        "display_as_two_line_heading",
        "last_name",
        "email",
        "mobile",
        "city",
        "postal_code",
    ]
    list_filter = [
        "is_active",
        "city",
        "contact_channel",
        "created_at",
        ("birthday", admin.EmptyFieldListFilter),
    ]
    actions = [
        "archive_customers",
        "unarchive_customers",
        "geocode_selected_customers",
        "export_to_csv",
    ]
    list_per_page = 50

    fieldsets = (
        ("Status", {"fields": (("is_active", "archived_at"),)}),
        (
            "Persönliche Daten",
            {"fields": (("first_name", "last_name"), ("email", "mobile"), "birthday")},
        ),
        ("Kontakt", {"fields": ("contact_channel",)}),
        (
            "Adress-Validierung",
            {"fields": ("address_validation_display",), "classes": ("wide",)},
        ),
        (
            "Adresse",
            {
                "fields": (
                    ("street", "house_number"),
                    ("postal_code", "city"),
                    "country",
                )
            },
        ),
        (
            "Geografische Position",
            {"fields": ("coordinates",), "classes": ("collapse",)},
        ),
        ("Zusätzliche Informationen", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Zeitstempel",
            {"fields": (("created_at", "updated_at"),), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at", "archived_at"]

    # ==================== DISPLAY METHODS ====================

    @display(header=True, description="Kunde")
    def display_as_two_line_heading(self, obj):
        if not obj.is_active:
            return DisplayHelpers.muted_text_two_line(obj.get_full_name(), obj.email)
        return [
            f"{obj.get_full_name()}",
            f"{obj.email}",
        ]

    @display(description="Adresse", ordering="city")
    def address(self, obj):
        """Adresse (PLZ + Stadt)"""
        if not obj.is_active:
            return DisplayHelpers.muted_text(f"{obj.postal_code} {obj.city}")
        return f"{obj.postal_code} {obj.city}"

    @display(description="Geburtstag", ordering="birthday")
    def birthday_with_muted(self, obj):
        """Geburtstag"""
        if not obj.birthday:
            return "-"

        birthday_text = obj.birthday.strftime("%d.%m.%Y")
        return DisplayHelpers.conditional_muted(birthday_text, not obj.is_active)

    @display(description="Alter", ordering="birthday")
    def age(self, obj):
        """Alter basierend auf Geburtstag"""
        if not obj.birthday:
            return "-"

        from datetime import date

        today = date.today()
        calculated_age = (
            today.year
            - obj.birthday.year
            - ((today.month, today.day) < (obj.birthday.month, obj.birthday.day))
        )
        age_text = f"{calculated_age} Jahre"

        return DisplayHelpers.conditional_muted(age_text, not obj.is_active)

    @display(description="Kurse")
    def course_stats(self, obj):
        """Kurse (In-Person | Online)"""
        from courses.models import Course

        inperson = Course.objects.filter(participants_inperson=obj).count()
        online = Course.objects.filter(participants_online=obj).count()
        total = inperson + online

        if total == 0:
            text = "0"
        else:
            text = format_html(
                '<strong>{}</strong> <small style="color: {};">({} | {})</small>',
                total,
                Colors.SECONDARY,
                inperson,
                online,
            )

        return DisplayHelpers.conditional_muted(text, not obj.is_active)

    @display(description="Rechnungen")
    def invoice_stats(self, obj):
        """Rechnungs-Statistik mit Status"""
        total = obj.invoices.count()

        if not obj.is_active:
            return DisplayHelpers.muted_text("0")

        return SimpleText.text(total)

    @display(description="Aktiv")
    def is_active_display(self, obj):
        """Status: Aktiv/Inaktiv"""
        return StatusIndicator.active_inactive_simple(obj.is_active)

    # ==================== ACTIONS ====================

    @admin.action(description="Kunden aktivieren")
    def unarchive_customers(self, request, queryset):
        """Aktiviert Kunden"""
        updated = queryset.update(is_active=True, archived_at=None)
        self.message_user(request, f"✅ {updated} Kunde(n) aktiviert.", level="SUCCESS")

    @admin.action(description="Kunden archivieren")
    def archive_customers(self, request, queryset):
        """Archiviert Kunden"""
        updated = queryset.update(is_active=False, archived_at=timezone.now())
        self.message_user(request, f"⚠️ {updated} Kunde(n) archiviert.", level="WARNING")


@admin.register(CustomerDiscountCode)
class CustomerDiscountCodeAdmin(ModelAdmin):
    form = CustomerDiscountCodeAdminForm
    """Admin für Rabattcodes"""

    actions_detail = ["send_email_action"]
    list_display = [
        "display_as_two_line_heading",
        "discount_display",
        "reason_display",
        "validity_period",
        "status_display",
    ]
    list_filter = ["status", "reason", "discount_type", "valid_from", "valid_until"]
    search_fields = [
        "code",
        "customer__first_name",
        "customer__last_name",
        "customer__email",
        "description",
        "course",
    ]
    readonly_fields = [
        "created_at",
        "used_at",
        "created_by",
        "email_sent_at",
        "cancelled_at",
    ]
    actions = [
        "send_discount_code_email",
        "mark_as_used",
        "mark_as_cancelled",
        "mark_as_planned",
    ]
    list_per_page = 50

    fieldsets = (
        ("Status", {"fields": ("status",)}),
        ("Kunde", {"fields": ("customer",)}),
        ("Kurse", {"fields": ("course",)}),
        ("Rabattcode", {"fields": (("code", "reason"), "description")}),
        ("Rabatt-Details", {"fields": (("discount_type", "discount_value"),)}),
        ("Gültigkeit", {"fields": (("valid_from", "valid_until"),)}),
        (
            "Historie",
            {
                "fields": (
                    ("email_sent_at", "used_at", "cancelled_at"),
                    "cancelled_reason",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "System",
            {"fields": (("created_at", "created_by"),), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        """Speichert created_by User"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # ==================== DISPLAY METHODS ====================

    @display(description="Status")
    def status_display(self, obj):
        """Status Badge"""
        status_map = {
            "planned": "Geplant",
            "sent": "Versendet",
            "used": "Eingelöst",
            "expired": "Abgelaufen",
            "cancelled": "Storniert",
        }

        # Color basierend auf Status
        color_map = {
            "planned": "warning",
            "sent": "success",
            "used": "secondary",
            "expired": "error",
            "cancelled": "error",
        }

        text = status_map.get(obj.status, obj.status)
        color = color_map.get(obj.status, "info")

        return SimpleText.literal_text(text, color)

    @display(header=True, description="Rabattcode")
    def display_as_two_line_heading(self, obj):
        if obj.status in ["used", "cancelled", "expired"]:
            return DisplayHelpers.muted_text_two_line(
                obj.code, obj.customer.get_full_name()
            )
        return [
            f"{obj.code}",
            f"{obj.customer.get_full_name()}",
        ]

    @display(description="Rabatt")
    def discount_display(self, obj):
        """Rabattbetrag mit Icon"""
        icon = "%" if obj.discount_type == "percentage" else "€"

        # Farbe basierend auf Status
        if obj.status in ["used", "cancelled", "expired"]:
            color = Colors.SECONDARY
        elif obj.discount_type == "percentage":
            color = Colors.SUCCESS
        else:
            color = Colors.INFO

        from django.utils.html import format_html

        return format_html(
            '<strong style="color: {}; font-size: 1.1rem;">{}{}</strong>',
            color,
            obj.discount_value,
            icon,
        )

    @display(description="Grund")
    def reason_display(self, obj):
        """Rabatt-Grund Badge"""
        reason_map = {
            "birthday": "Geburtstag",
            "course_completed": "Kurs abgeschlossen",
            "referral": "Empfehlung",
            "loyalty": "Treueprämie",
            "other": "Sonstiges",
        }

        text = reason_map.get(obj.reason, obj.get_reason_display())

        if obj.status in ["used", "cancelled", "expired"]:
            return DisplayHelpers.muted_text(text)
        return f"{text}"

    @display(description="Gültigkeit")
    def validity_period(self, obj):
        """Gültigkeitszeitraum"""
        if obj.status in ["used", "cancelled", "expired"]:
            return DisplayHelpers.muted_text(
                f"{obj.valid_from.strftime('%d.%m.%Y')} bis {obj.valid_until.strftime('%d.%m.%Y')}"
            )

        return f"{obj.valid_from.strftime('%d.%m.%Y')} bis {obj.valid_until.strftime('%d.%m.%Y')}"

    # ==================== ACTIONS ====================

    @action(
        description="Code via E-Mail versenden",
        url_path="send-email",
        permissions=["send_email_action"],
    )
    def send_email_action(self, request, object_id):
        """Sendet E-Mail für einen Code"""
        from django.shortcuts import redirect
        from django.urls import reverse

        from company.models import CompanyInfo

        try:
            discount_code = CustomerDiscountCode.objects.get(pk=object_id)
            service = DiscountCodeEmailService(CompanyInfo.get_solo())
            service.send_single_email(discount_code)
            self.message_user(
                request,
                f"✅ E-Mail an {discount_code.customer.get_full_name()} versendet.",
                level="SUCCESS",
            )
        except Exception as e:
            self.message_user(request, f"❌ Fehler: {str(e)}", level="ERROR")

        return redirect(
            reverse("admin:customers_customerdiscountcode_change", args=[object_id])
        )

    @admin.action(description="Rabattcodes per E-Mail versenden")
    def send_discount_code_email(self, request, queryset):
        """Sendet E-Mails für mehrere Codes"""
        from company.models import CompanyInfo

        service = DiscountCodeEmailService(CompanyInfo.get_solo())
        success, errors = service.send_bulk_emails(queryset)

        self.message_user(
            request, f"✅ {success} E-Mail(s) versendet.", level="SUCCESS"
        )
        if errors:
            error_msg = "\n".join([f"{name}: {err}" for name, err in errors[:5]])
            self.message_user(
                request, f"❌ {len(errors)} Fehler:\n{error_msg}", level="ERROR"
            )

    @admin.action(description="Als eingelöst markieren")
    def mark_as_used(self, request, queryset):
        """Markiert Codes als verwendet"""
        codes_to_use = queryset.exclude(status="used")
        if not codes_to_use.exists():
            self.message_user(
                request, "⚠️ Alle sind bereits eingelöst.", level="WARNING"
            )
            return
        for code in codes_to_use:
            code.use_code()
        self.message_user(
            request,
            f"✅ {codes_to_use.count()} Code(s) als eingelöst markiert.",
            level="SUCCESS",
        )

    @admin.action(description="Als storniert markieren")
    def mark_as_cancelled(self, request, queryset):
        """Storniert Codes"""
        codes_to_cancel = queryset.exclude(status="cancelled")
        if not codes_to_cancel.exists():
            self.message_user(
                request, "⚠️ Alle sind bereits storniert.", level="WARNING"
            )
            return
        codes_to_cancel.update(
            status="cancelled",
            cancelled_at=timezone.now(),
            cancelled_reason="Manuell storniert",
        )
        self.message_user(
            request, f"✅ {codes_to_cancel.count()} Code(s) storniert.", level="SUCCESS"
        )

    @admin.action(description="Als geplant markieren")
    def mark_as_planned(self, request, queryset):
        """Reaktiviert stornierte Codes"""
        codes_to_reactivate = queryset.filter(status__in=["cancelled", "expired"])
        if not codes_to_reactivate.exists():
            self.message_user(request, "⚠️ Keine stornierten Codes.", level="WARNING")
            return
        codes_to_reactivate.update(
            status="planned", cancelled_at=None, cancelled_reason=""
        )
        self.message_user(
            request,
            f"✅ {codes_to_reactivate.count()} Code(s) reaktiviert.",
            level="SUCCESS",
        )

    def has_send_email_action_permission(self, request, object_id):
        return self.has_change_permission(request)


@admin.register(ContactChannel)
class ContactChannelAdmin(ModelAdmin):
    """Admin für Kontaktkanäle"""

    list_display = ["name", "slug", "is_active_display"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]
    list_filter = ["is_active"]

    fieldsets = (
        ("Allgemein", {"fields": ("name", "slug", "description")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Zeitstempel",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    @display(description="Aktiv / Inaktiv")
    def is_active_display(self, obj):
        """Status: Aktiv/Inaktiv"""
        return StatusIndicator.active_inactive_simple(obj.is_active)
