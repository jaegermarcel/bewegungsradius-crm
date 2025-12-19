import logging

from django.utils.html import format_html

from bewegungsradius.core.admin_styles import Colors, DisplayHelpers

logger = logging.getLogger(__name__)


class LocationAdminDisplay:
    """Service für Location Admin Display"""

    @staticmethod
    def get_location_name(location):
        """Gibt Standortnamen zurück"""
        return location.name

    @staticmethod
    def get_address(location):
        """Formatiert Adresse"""
        if not location.city:
            return "-"
        if location.postal_code:
            return f"{location.postal_code} {location.city}"
        return location.city

    @staticmethod
    def get_capacity(location):
        """Formatiert Kapazität"""
        return format_html(
            '<strong>{}</strong> <small style="color: #6b7280;">Teilnehmer</small>',
            location.max_participants,
        )

    @staticmethod
    def get_registered_date(location):
        """Formatiert Erstellungsdatum"""
        return location.created_at.strftime("%d.%m.%Y")


class CourseAdminDisplay:
    """Service für Course Admin Display"""

    @staticmethod
    def get_course_title(course):
        return course.title

    @staticmethod
    def get_start_time(course):
        """Formatiert Kurszeit"""
        return course.start_time.strftime("%H:%M") if course.start_time else "-"

    def get_location_info(course):
        """Formatiert Standort-Info mit Kapazität"""

        # Online-Kurs
        if not course.location:
            location_html = format_html('<span style="color: #3b82f6;">Online</span>')
            return (
                DisplayHelpers.muted_text(location_html)
                if not course.is_active
                else location_html
            )

        current = course.participants_inperson.count()
        max_capacity = course.location.max_participants

        # ✅ SCHRITT 2: Bestimme Status-Farbe
        if not course.is_active:
            # Wenn inaktiv: Alles grau
            color_status = Colors.SECONDARY
        else:
            # Wenn aktiv: Normale Logik
            if current >= max_capacity:
                color_status = Colors.TEXT_ERROR  # Rot
            elif current >= max_capacity * 0.8:
                color_status = Colors.TEXT_ORANGE  # Orange
            else:
                color_status = Colors.TEXT_SUCCESS  # Grün

        status = (
            "Ausgebucht"
            if current >= max_capacity
            else f"{max_capacity - current} frei"
        )

        # ✅ SCHRITT 3: Format HTML mit Farben
        location_html = format_html(
            '{}<br><small style="color: {};">{}</small>',
            course.location.name,
            color_status,
            status,
        )

        # ✅ SCHRITT 4: Wrap mit muted_text wenn inaktiv
        return (
            DisplayHelpers.muted_text(location_html)
            if not course.is_active
            else location_html
        )

    @staticmethod
    def get_units_display(course):
        """Formatiert Anzahl Kurseinheiten"""
        if course.is_weekly and course.end_date:
            total_units = course.get_total_course_units()
            skipped = course.get_skipped_dates_due_to_holidays()

            if skipped:
                return format_html(
                    '<strong>{}</strong> <small style="color: #f59e0b;" title="{} wegen Feiertagen ausgefallen">({} ausgefallen)</small>',
                    total_units,
                    len(skipped),
                    len(skipped),
                )
            return format_html("<strong>{}</strong>", total_units)
        return "1"

    @staticmethod
    def get_participants(course):
        """Formatiert Teilnehmer-Count"""
        inperson = course.participants_inperson.count()
        online = course.participants_online.count()
        total = inperson + online

        # ✅ NEU: Prüfe is_active auch bei 0
        if total == 0:
            participants_html = format_html('<span style="color: #9ca3af;">0</span>')
            return (
                DisplayHelpers.muted_text(participants_html)
                if not course.is_active
                else participants_html
            )

        max_inperson = course.max_participants_inperson

        # ✅ NEU: Prüfe is_active für die Hauptfarbe
        if not course.is_active:
            color_total = Colors.SECONDARY  # Grau wenn inaktiv
        else:
            # Normale Logik wenn aktiv
            if course.location:
                percentage = (inperson / max_inperson) * 100 if max_inperson > 0 else 0
                if percentage >= 100:
                    color_total = Colors.TEXT_ERROR
                elif percentage >= 80:
                    color_total = Colors.TEXT_ORANGE
                else:
                    color_total = Colors.TEXT_SUCCESS
            else:
                color_total = "#3b82f6"

        # Format HTML (Details bleiben grau)
        participants_html = format_html(
            '<strong style="color: {}">{}</strong> <small style="color: {};">({} | {})</small>',
            color_total,  # ← Ändert sich basierend auf is_active
            total,
            Colors.SECONDARY,  # ← Bleibt immer grau
            inperson,
            online,
        )

        # ✅ NEU: Wrap mit muted_text wenn inaktiv
        return (
            DisplayHelpers.muted_text(participants_html)
            if not course.is_active
            else participants_html
        )

    @staticmethod
    def get_price_display(course):
        """Formatiert Preis"""
        return format_html("<strong>{}</strong> €", course.price)

    @staticmethod
    def get_period(course):
        """Formatiert Zeitraum"""
        start = course.start_date.strftime("%d.%m.%Y")

        if course.end_date:
            end = course.end_date.strftime("%d.%m.%Y")
            return format_html(
                '{}<br><small style="color: #6b7280;">bis {}</small>', start, end
            )

        return start

    def get_email_status(course):
        """Formatiert E-Mail Versand Status (SICHER für None-Werte)"""
        if not course.is_active:
            color_success = Colors.SECONDARY
            color_error = Colors.SECONDARY
            color_neutral = Colors.SECONDARY
        else:
            color_success = "#10b981"
            color_error = "#ef4444"
            color_neutral = "#6b7280"

        parts = []

        # Start-E-Mail Status
        if course.start_email_sent and course.start_email_sent_at:  # ← Prüfe BEIDE!
            parts.append(
                format_html(
                    '<span style="color: {};">✓ Start</span> '
                    '<small style="color: {};">({})</small>',
                    color_success,
                    color_neutral,
                    course.start_email_sent_at.strftime("%d.%m.%y"),
                )
            )
        elif course.start_email_sent:  # Sent aber keine Time
            parts.append(
                format_html(
                    '<span style="color: {};">✓ Start</span> '
                    '<small style="color: {};">(-)</small>',
                    color_success,
                    color_neutral,
                )
            )
        else:
            parts.append(
                format_html('<span style="color: {};">✗ Start</span>', color_error)
            )

        # Abschluss-E-Mail Status
        if (
            course.completion_email_sent and course.completion_email_sent_at
        ):  # ← Prüfe BEIDE!
            parts.append(
                format_html(
                    '<span style="color: {};">✓ Abschluss</span> '
                    '<small style="color: {};">({})</small>',
                    color_success,
                    color_neutral,
                    course.completion_email_sent_at.strftime("%d.%m.%y"),
                )
            )
        else:
            parts.append(
                format_html(
                    '<span style="color: {};">○ Abschluss</span>', color_neutral
                )
            )

        return format_html("<br>".join(parts))


class CourseWarningHandler:
    """Service für Kurswarnungen"""

    def handle_holiday_warnings(self, request, course):
        """Zeigt Warnungen für Feiertage"""
        if not course.is_weekly:
            return

        warnings = course.check_holidays_on_course_day()
        if not warnings:
            return

        total_units = course.get_total_course_units()
        skipped_count = len(warnings)

        message = f"<strong>Achtung: {skipped_count} Kurseinheit(en) fallen wegen Feiertagen aus!</strong><br>"
        message += (
            f"<strong>Tatsächliche Anzahl Einheiten: {total_units}</strong><br><br>"
        )
        message += "<strong>Betroffene Termine:</strong><br>"

        for warning in warnings:
            message += f"• {warning['message']}<br>"

        message += "<br><em>Tipp: Verlängern Sie bei Bedarf das Enddatum manuell.</em>"

        from django.utils.html import format_html

        request._messages = None  # Reset messages
        from django.contrib import messages

        messages.warning(request, format_html(message))
