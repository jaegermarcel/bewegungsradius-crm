from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from bewegungsradius.core.admin_styles import (
    DisplayHelpers,
    SimpleText,
    StatusIndicator,
)

from .models import Offer, ZPPCertification


@admin.register(ZPPCertification)
class ZPPCertificationAdmin(ModelAdmin):
    """Admin für ZPP-Zertifizierungen"""

    list_display = [
        "display_as_two_line_heading",
        "format_display",
        "validity_display",
        "days_until_expiry_display",
        "is_active_display",
    ]
    list_filter = ["is_active", "format", "valid_until"]
    search_fields = ["zpp_id", "name", "official_title"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Status", {"fields": ("is_active",)}),
        ("ZPP-Identifikation", {"fields": (("official_title", "zpp_id"), "name")}),
        ("Format", {"fields": ("format",)}),
        ("Gültigkeit", {"fields": (("valid_from", "valid_until"),)}),
        ("Notizen", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Zeitstempel",
            {"fields": (("created_at", "updated_at"),), "classes": ("collapse",)},
        ),
    )

    @display(header=True, description="Zertifizierungen")
    def display_as_two_line_heading(self, obj):
        zpp_id = obj.zpp_id
        zpp_title = obj.name
        if not obj.is_active:
            return DisplayHelpers.muted_text_two_line(zpp_title, zpp_id)
        return [
            f"{zpp_title}",
            f"{zpp_id}",
        ]

    @display(description="Format")
    def format_display(self, obj):
        """Kurs-Format Badge"""
        format_text = obj.get_format_display()
        return (
            DisplayHelpers.muted_text(format_text) if not obj.is_active else format_text
        )

    @display(description="Gültig bis", ordering="valid_until")
    def validity_display(self, obj):
        """Gültigkeitsdatum mit Warnung wenn nah am Ablauf"""
        days = obj.days_until_expiry()

        if days <= 0:
            error_text = SimpleText.literal_text("⚠️ Abgelaufen", "error")
            return (
                DisplayHelpers.muted_text(error_text)
                if not obj.is_active
                else error_text
            )
        elif days <= 30:
            warning_text = SimpleText.literal_text(f"⚠️ {days} Tage", "warning")
            return (
                DisplayHelpers.muted_text(warning_text)
                if not obj.is_active
                else warning_text
            )
        else:
            return (
                DisplayHelpers.muted_text(f'{obj.valid_until.strftime("%d.%m.%Y")}')
                if not obj.is_active
                else f'{obj.valid_until.strftime("%d.%m.%Y")}'
            )

    @display(description="Aktiv")
    def is_active_display(self, obj):
        """Status Badge"""
        return StatusIndicator.active_inactive_simple(obj.is_active)

    @display(description="Ablauf in...")
    def days_until_expiry_display(self, obj):
        """Tage bis Ablauf"""
        days = obj.days_until_expiry()
        if days <= 0:
            text = SimpleText.literal_text("Abgelaufen", "error")
            return DisplayHelpers.muted_text(text) if not obj.is_active else text
        return (
            DisplayHelpers.muted_text(f"{days} Tage")
            if not obj.is_active
            else f"{days} Tage"
        )


@admin.register(Offer)
class OfferAdmin(ModelAdmin):
    """Admin für Angebote (Kurse, 10er-Karten, etc.)"""

    list_display = [
        "title_display",
        "offer_type_display",
        "price_display",
        "description_display",
        "is_active_display",
    ]
    list_filter = ["offer_type", "is_active", "format", "created_at"]
    search_fields = ["title", "notes"]
    readonly_fields = ["created_at", "updated_at", "total_amount", "tax_amount"]

    fieldsets = (
        ("Status", {"fields": ("is_active",)}),
        ("Grundlagen", {"fields": (("title", "offer_type"),)}),
        # Kurs-spezifisch
        (
            "Kurs-Details",
            {
                "fields": (("format", "course_units", "course_duration"),),
                "classes": ("collapse",),
                "description": "Nur für Kurse relevant",
            },
        ),
        # 10er-Karte spezifisch
        (
            "10er-Karte Details",
            {
                "fields": (("ticket_sessions", "ticket_validity_months"),),
                "classes": ("collapse",),
                "description": "Nur für 10er-Karten relevant",
            },
        ),
        # Preise
        (
            "Preise",
            {
                "fields": (
                    "amount",
                    "tax_rate",
                    "is_tax_exempt",
                    "tax_amount",
                    "total_amount",
                )
            },
        ),
        # ZPP (nur für Kurse)
        (
            "ZPP-Zertifizierung",
            {
                "fields": ("zpp_certification",),
                "classes": ("collapse",),
                "description": "Nur für ZPP-zertifizierte Kurse",
            },
        ),
        # Sonstiges
        ("Notizen", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Zeitstempel",
            {"fields": (("created_at", "updated_at"),), "classes": ("collapse",)},
        ),
    )

    def get_fieldsets(self, request, obj=None):
        """Dynamische Fieldsets basierend auf offer_type"""
        fieldsets = list(self.fieldsets)

        if obj:
            # Entferne irrelevante Sections basierend auf offer_type
            if obj.offer_type != "course":
                fieldsets = [fs for fs in fieldsets if fs[0] != "Kurs-Details"]
                fieldsets = [fs for fs in fieldsets if fs[0] != "ZPP-Zertifizierung"]

            if obj.offer_type != "ticket_10":
                fieldsets = [fs for fs in fieldsets if fs[0] != "10er-Karte Details"]

        return fieldsets

    @display(description="Titel", ordering="title")
    def title_display(self, obj):
        """Titel mit Icon basierend auf Typ"""
        return DisplayHelpers.muted_text(obj.title) if not obj.is_active else obj.title

    @display(description="Typ")
    def offer_type_display(self, obj):
        """Angebots-Typ Badge"""
        type_colors = {
            "course": "info",
            "ticket_10": "success",
            "workshop": "warning",
            "seminar": "secondary",
        }
        text = obj.get_offer_type_display()
        return DisplayHelpers.muted_text(text) if not obj.is_active else text

    @display(description="Preis")
    def price_display(self, obj):
        """Preis mit Übersicht"""
        if obj.offer_type == "ticket_10":
            # Für 10er-Karten: Gesamtpreis + Preis pro Session
            price_per_session = obj.get_price_per_session()
            return (
                DisplayHelpers.muted_text(
                    f"{obj.total_amount}€ ({price_per_session}€/Einheit)"
                )
                if not obj.is_active
                else f"{obj.total_amount}€ ({price_per_session}€/Einheit)"
            )

        else:
            return (
                DisplayHelpers.muted_text(f"{obj.total_amount}€")
                if not obj.is_active
                else f"{obj.total_amount}€"
            )

    @display(description="Details")
    def description_display(self, obj):
        """Detaillierte Beschreibung basierend auf Typ"""
        description = obj.get_description()

        return (
            DisplayHelpers.muted_text(description) if not obj.is_active else description
        )
        # Farbe basierend auf ZPP

        return SimpleText.muted(description)

    @display(description="Aktiv")
    def is_active_display(self, obj):
        """Status Badge"""
        return StatusIndicator.active_inactive_simple(obj.is_active)
