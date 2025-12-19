from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from leaflet.admin import LeafletGeoAdminMixin
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminSelect2Widget

from bewegungsradius.core.admin_styles import StatusIndicator  # Verschiedene Helper
from bewegungsradius.core.admin_styles import DisplayHelpers
from offers.models import Offer

from .admin_services import (
    CourseAdminDisplay,
    CourseWarningHandler,
    LocationAdminDisplay,
)
from .models import Course, Location


class CourseAdminForm(forms.ModelForm):
    """Custom Form: Schöner Offer-Dropdown mit Select2"""

    offer = forms.ModelChoiceField(
        queryset=Offer.objects.all(),
        required=True,
        empty_label="— Kein Angebot ausgewählt —",
        widget=UnfoldAdminSelect2Widget(),
        label="Angebot",
    )

    class Meta:
        model = Course
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offer"].label_from_instance = (
            lambda obj: f"{obj.title} ({obj.get_offer_type_display()})"
        )


@admin.register(Location)
class LocationAdmin(LeafletGeoAdminMixin, ModelAdmin):

    list_display = ["location_name", "address", "capacity", "registered"]

    list_display_links = ["location_name"]
    search_fields = ["name", "city", "street", "postal_code"]
    list_filter = ["city"]
    actions = ["geocode_selected_locations"]
    list_per_page = 50

    fieldsets = (
        ("Standort-Informationen", {"fields": (("name", "max_participants"),)}),
        (
            "Adresse",
            {
                "fields": (
                    ("street", "house_number"),
                    ("postal_code", "city"),
                )
            },
        ),
        (
            "Geografische Position",
            {"fields": ("coordinates",), "classes": ("collapse",)},
        ),
        ("Zusätzliche Informationen", {"fields": ("notes",), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at", "updated_at"]

    @display(description="Standort", ordering="name")
    def location_name(self, obj):
        return LocationAdminDisplay.get_location_name(obj)

    @display(description="Adresse", ordering="city")
    def address(self, obj):
        return LocationAdminDisplay.get_address(obj)

    @display(description="Kapazität", ordering="max_participants")
    def capacity(self, obj):
        return LocationAdminDisplay.get_capacity(obj)

    @display(description="Erstellt", ordering="created_at")
    def registered(self, obj):
        return LocationAdminDisplay.get_registered_date(obj)

    @admin.action(description="Koordinaten ermitteln")
    def geocode_selected_locations(self, request, queryset):
        """Geocodiert ausgewählte Standorte"""
        count = 0
        errors = 0

        for location in queryset:
            if not location.coordinates and location.street and location.city:
                coords = location.geocode_address()
                if coords:
                    location.coordinates = coords
                    location.save()
                    count += 1
                else:
                    errors += 1

        if count > 0:
            self.message_user(
                request, f"{count} Standort(e) geocodiert.", level="SUCCESS"
            )
        if errors > 0:
            self.message_user(
                request,
                f"{errors} Standort(e) konnten nicht geocodiert werden.",
                level="WARNING",
            )
        if count == 0 and errors == 0:
            self.message_user(
                request,
                "Alle ausgewählten Standorte haben bereits Koordinaten.",
                level="INFO",
            )


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    form = CourseAdminForm

    actions_detail = ["send_start_email_action", "send_end_email_action"]
    list_display = [
        "display_as_two_line_heading",
        "location_info",
        "participants",
        "schedule",
        "period",
        "start_time_display",
        "email_status",
        "status_badge",
    ]

    list_display_links = ["display_as_two_line_heading"]

    search_fields = ["offer__title", "location__name"]

    list_filter = [
        "is_active",
        "offer__offer_type",
        "location",
        "is_weekly",
        "weekday",
        "start_date",
    ]

    filter_horizontal = ["participants_inperson", "participants_online"]

    actions = ["mark_as_inactive", "mark_as_active"]

    list_per_page = 50

    fieldsets = (
        ("Status", {"fields": ("is_active",)}),
        ("Angebot", {"fields": ("offer",)}),
        (
            "Termine & Ort",
            {
                "fields": (
                    ("start_date", "end_date"),
                    ("start_time", "end_time"),
                    ("location", "is_weekly"),
                ),
                "description": "Das Enddatum wird NICHT automatisch verlängert. "
                "Bei Feiertagen an Kurstagen erhalten Sie eine Warnung.",
            },
        ),
        ("Teilnehmer", {"fields": ("participants_inperson", "participants_online")}),
        (
            "E-Mail Tracking",
            {
                "fields": (
                    ("start_email_sent", "start_email_sent_at"),
                    ("completion_email_sent", "completion_email_sent_at"),
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = [
        "weekday",
        "start_email_sent",
        "start_email_sent_at",
        "completion_email_sent",
        "completion_email_sent_at",
    ]

    # ========================================
    # DISPLAY METHODS
    # ========================================

    @display(header=True, description="Kurs")
    def display_as_two_line_heading(self, obj):
        title = CourseAdminDisplay.get_course_title(obj)
        badge = obj.offer.get_offer_type_display()
        if not obj.is_active:
            return DisplayHelpers.muted_text_two_line(title, badge)
        return [
            f"{title}",
            f"{badge}",
        ]

    @display(description="Wochentag", ordering="weekday")
    def schedule(self, obj):
        schedule = obj.get_weekday_display()
        return DisplayHelpers.muted_text(schedule) if not obj.is_active else schedule

    @display(description="Uhrzeit", ordering="start_time")
    def start_time_display(self, obj):
        start_time = CourseAdminDisplay.get_start_time(obj)
        return (
            DisplayHelpers.muted_text(start_time) if not obj.is_active else start_time
        )

    @display(description="Ort", ordering="location__name")
    def location_info(self, obj):
        return CourseAdminDisplay.get_location_info(obj)

    @display(description="Teilnehmer")
    def participants(self, obj):
        participant = CourseAdminDisplay.get_participants(obj)
        return (
            DisplayHelpers.muted_text(participant) if not obj.is_active else participant
        )

    @display(description="Zeitraum", ordering="start_date")
    def period(self, obj):
        period = CourseAdminDisplay.get_period(obj)
        return DisplayHelpers.muted_text(period) if not obj.is_active else period

    @display(description="Status")
    def status_badge(self, obj):
        return StatusIndicator.active_inactive_simple(obj.is_active)

    @display(description="E-Mail Status")
    def email_status(self, obj):
        return CourseAdminDisplay.get_email_status(obj)

    # ========================================
    # ACTIONS
    # ========================================

    @admin.action(description="Als inaktiv markieren")
    def mark_as_inactive(self, request, queryset):
        """Markiert ausgewählte Kurse als inaktiv"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, f"{updated} Kurs(e) als inaktiv markiert.", level="WARNING"
        )

    @admin.action(description="Als aktiv markieren")
    def mark_as_active(self, request, queryset):
        """Markiert ausgewählte Kurse als aktiv"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, f"{updated} Kurs(e) als aktiv markiert.", level="SUCCESS"
        )

    @action(
        description="Start E-Mail senden",
        url_path="send-email",
        permissions=["send_start_email_action"],
    )
    def send_start_email_action(self, request, object_id):
        try:
            from company.models import CompanyInfo
            from courses.email_services.course_emails import CourseStartEmailService

            # Laden des Kurses
            course = Course.objects.get(id=object_id)

            # Email versenden (NICHT mit course_id, sondern mit course Object!)
            service = CourseStartEmailService(CompanyInfo.get_solo())
            result = service.send_course_start_email(course)  # ← RICHTIG!

            if result.get("sent", 0) > 0:
                course.mark_start_email_sent()

            # Benachrichtigung
            self.message_user(
                request, f"✓ {result['sent']} Email(s) versendet", level="SUCCESS"
            )

            return redirect("admin:courses_course_change", object_id)

        except Exception as e:
            self.message_user(request, f"❌ Fehler: {str(e)}", level="ERROR")
            return redirect("admin:courses_course_change", object_id)

    @action(
        description="Ende E-Mail senden",
        url_path="send-completion-email",
        permissions=["send_end_email_action"],
    )
    def send_end_email_action(self, request, object_id):
        try:
            from company.models import CompanyInfo
            from courses.email_services.course_emails import (
                CourseCompletionEmailService,
            )

            course = Course.objects.get(id=object_id)

            # Email versenden (NICHT mit course_id, sondern mit course Object!)
            service = CourseCompletionEmailService(CompanyInfo.get_solo())
            result = service.send_course_completion_email(course)  # ← RICHTIG!

            if result.get("sent", 0) > 0:
                course.mark_completion_email_sent()

            # Benachrichtigung
            self.message_user(
                request, f"✓ {result['sent']} Email(s) versendet", level="SUCCESS"
            )

            return redirect("admin:courses_course_change", object_id)

        except Exception as e:
            self.message_user(request, f"❌ Fehler: {str(e)}", level="ERROR")
            return redirect("admin:courses_course_change", object_id)

    def save_model(self, request, obj, form, change):
        """Speichert Model und zeigt Warnungen"""
        super().save_model(request, obj, form, change)

        warning_handler = CourseWarningHandler()
        warning_handler.handle_holiday_warnings(request, obj)

    def has_send_start_email_action_permission(self, request, object_id):
        return self.has_change_permission(request)

    def has_send_end_email_action_permission(self, request, object_id):
        return self.has_change_permission(request)
