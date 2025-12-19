"""
bewegungsradius/core/admin_styles.py
====================================
Zentralisierte Admin UI Styles & Colors
Mit Badges UND ohne Badges (nur Icons/Text)
"""

from typing import Literal

from django.utils.html import format_html

# ================== COLOR PALETTE ==================


class Colors:
    """Zentrale Farbpalette für Admin Interface"""

    # Status Colors
    SUCCESS = "#10b981"  # Grün
    WARNING = "#f59e0b"  # Orange
    ERROR = "#ef4444"  # Rot
    INFO = "#3b82f6"  # Blau
    SECONDARY = "#6b7280"  # Grau

    # Light Backgrounds
    BG_SUCCESS = "#dcfce7"
    BG_WARNING = "#fef3c7"
    BG_ERROR = "#fee2e2"
    BG_INFO = "#dbeafe"
    BG_SECONDARY = "#f3f4f6"

    # Text Colors
    TEXT_SUCCESS = "#4E9F3D"
    TEXT_WARNING = "#92400e"
    TEXT_ERROR = "#991b1b"
    TEXT_INFO = "#1e40af"
    TEXT_ORANGE = "#ec7c25"


# ================== BADGE STYLES ==================


class BadgeStyle:
    """Badge Styling für verschiedene Status"""

    BASE_STYLE = (
        "display: inline-block; "
        "padding: 4px 8px; "
        "border-radius: 4px; "
        "font-size: 0.875rem; "
        "font-weight: 500; "
        "white-space: nowrap;"
    )

    @staticmethod
    def badge(
        text: str,
        color: Literal["success", "warning", "error", "info", "secondary"] = "info",
    ) -> str:
        """Erstellt ein Badge mit einheitlichem Style"""
        colors = {
            "success": (Colors.BG_SUCCESS, Colors.TEXT_SUCCESS),
            "warning": (Colors.BG_WARNING, Colors.TEXT_WARNING),
            "error": (Colors.BG_ERROR, Colors.TEXT_ERROR),
            "info": (Colors.BG_INFO, Colors.TEXT_INFO),
            "secondary": (Colors.BG_SECONDARY, Colors.SECONDARY),
        }
        bg, fg = colors[color]
        style = f"{BadgeStyle.BASE_STYLE} background: {bg}; color: {fg};"
        return format_html('<span style="{}">{}</span>', style, text)


# ================== SIMPLE TEXT STYLES ==================


class SimpleText:
    """Text Styling - OHNE Badge, nur Farbe"""

    @staticmethod
    def text(content: str, color: str = "") -> str:
        """Einfach nur farbiger Text"""
        return format_html('<span style="color: {};">{}</span>', color, content)

    @staticmethod
    def literal_text(
        content: str,
        color: Literal["success", "warning", "error", "info", "secondary"] = "info",
    ) -> str:
        """Einfach nur farbiger Text"""
        colors = {
            "success": Colors.SUCCESS,
            "warning": Colors.WARNING,
            "error": Colors.ERROR,
            "info": Colors.INFO,
            "secondary": Colors.SECONDARY,
        }
        fg = colors[color]
        return format_html('<span style="color: {};">{}</span>', fg, content)

    @staticmethod
    def bold(
        content: str,
        color: Literal["success", "warning", "error", "info", "secondary"] = "info",
    ) -> str:
        """Fetter, farbiger Text"""
        colors = {
            "success": Colors.SUCCESS,
            "warning": Colors.WARNING,
            "error": Colors.ERROR,
            "info": Colors.INFO,
            "secondary": Colors.SECONDARY,
        }
        fg = colors[color]
        return format_html('<strong style="color: {};">{}</strong>', fg, content)

    @staticmethod
    def icon(
        content: str,
        color: Literal["success", "warning", "error", "info", "secondary"] = "",
    ) -> str:
        """Nur Icon mit Farbe - KEINE Badge"""
        colors = {
            "success": Colors.SUCCESS,
            "warning": Colors.WARNING,
            "error": Colors.ERROR,
            "info": Colors.INFO,
            "secondary": Colors.SECONDARY,
        }
        fg = colors.get(color, "")
        return format_html(
            '<span style="color: {}; font-size: 1.2em;">{}</span>', fg, content
        )

    @staticmethod
    def muted(content: str) -> str:
        """Grauer Text (inaktiv)"""
        return format_html(
            '<span style="color: {};">{}</span>', Colors.SECONDARY, content
        )


# ================== ICON BADGES ==================


class IconBadge:
    """Icons mit Farben - MIT Badge"""

    @staticmethod
    def success(label: str = "✓") -> str:
        """Grünes Success Badge"""
        return BadgeStyle.badge(label, "success")

    @staticmethod
    def warning(label: str = "⚠️") -> str:
        """Orange Warning Badge"""
        return BadgeStyle.badge(label, "warning")

    @staticmethod
    def error(label: str = "✗") -> str:
        """Rotes Error Badge"""
        return BadgeStyle.badge(label, "error")

    @staticmethod
    def info(label: str = "ℹ️") -> str:
        """Blaues Info Badge"""
        return BadgeStyle.badge(label, "info")


# ================== STATUS INDICATORS ==================


class StatusIndicator:
    """Standardisierte Status-Anzeigen"""

    # ========== MIT BADGE ==========

    @staticmethod
    def yes_no(value: bool, yes_label: str = "Ja", no_label: str = "Nein") -> str:
        """Boolean-Status MIT Badge"""
        if value:
            return BadgeStyle.badge(f"✓ {yes_label}", "success")
        return BadgeStyle.badge(f"✗ {no_label}", "error")

    @staticmethod
    def active_inactive(is_active: bool) -> str:
        """Aktiv/Inaktiv Status MIT Badge"""
        if is_active:
            return BadgeStyle.badge("● Aktiv", "success")
        return BadgeStyle.badge("● Inaktiv", "secondary")

    @staticmethod
    def email_status(was_sent: bool, sent_at=None) -> str:
        """Email-Versand Status MIT Badge"""
        if was_sent:
            text = sent_at.strftime("%d.%m.%Y %H:%M") if sent_at else "Versendet"
            return BadgeStyle.badge(f"{text}", "success")
        return BadgeStyle.badge("✗ Ausstehend", "error")

    @staticmethod
    def payment_status(status: str) -> str:
        """Zahlungs-Status MIT Badge"""
        status_map = {
            "paid": ("Bezahlt", "success"),
            "pending": ("Ausstehend", "warning"),
            "overdue": ("Überfällig", "error"),
            "cancelled": ("Storniert", "error"),
        }
        text, color = status_map.get(status, (status, "info"))
        return BadgeStyle.badge(text, color)

    # ========== OHNE BADGE - NUR TEXT ==========

    @staticmethod
    def yes_no_simple(
        value: bool, yes_label: str = "Ja", no_label: str = "Nein"
    ) -> str:
        """Boolean-Status - einfach nur Text/Icon"""
        if value:
            return SimpleText.literal_text(f"✓ {yes_label}", "success")
        return SimpleText.literal_text(f"✗ {no_label}", "error")

    @staticmethod
    def active_inactive_simple(is_active: bool) -> str:
        """Aktiv/Inaktiv - einfach nur Text/Icon"""
        if is_active:
            return SimpleText.literal_text("● Aktiv", "success")
        return SimpleText.muted("● Inaktiv")

    @staticmethod
    def email_status_simple(was_sent: bool, sent_at=None) -> str:
        """Email-Versand Status - einfach nur Text/Icon"""
        if was_sent:
            text = sent_at.strftime("%d.%m.%Y %H:%M") if sent_at else "Versendet"
            return SimpleText.text(f"{text}")
        return SimpleText.text("✗ Ausstehend")

    @staticmethod
    def payment_status_simple(status: str) -> str:
        """Zahlungs-Status - einfach nur Text"""
        status_map = {
            "paid": ("Bezahlt", "success"),
            "pending": ("Ausstehend", "warning"),
            "overdue": ("Überfällig", "error"),
            "cancelled": ("Storniert", "error"),
        }
        text, color = status_map.get(status, (status, "info"))
        return SimpleText.bold(text, color)

    # ========== NUR ICON - KEINE TEXT/BADGE ==========

    @staticmethod
    def yes_no_icon_only(value: bool) -> str:
        """Boolean - nur Icon"""
        return SimpleText.icon("✓" if value else "✗", "success" if value else "error")

    @staticmethod
    def active_inactive_icon_only(is_active: bool) -> str:
        """Aktiv/Inaktiv - nur Icon"""
        return SimpleText.icon("●", "success" if is_active else "secondary")

    @staticmethod
    def email_status_icon_only(was_sent: bool) -> str:
        """Email - nur Icon"""
        return SimpleText.icon(
            "✓" if was_sent else "✗", "success" if was_sent else "error"
        )


# ================== DISPLAY HELPERS ==================


class DisplayHelpers:
    """Helper für @display Methoden"""

    @staticmethod
    def colored_text(
        text: str,
        color: Literal["success", "warning", "error", "info", "secondary"] = "info",
    ) -> str:
        """Text mit Farbe ohne Badge"""
        return SimpleText.literal_text(text, color)

    @staticmethod
    def colored_bold(
        text: str,
        color: Literal["success", "warning", "error", "info", "secondary"] = "info",
    ) -> str:
        """Fetter Text mit Farbe"""
        return SimpleText.bold(text, color)

    @staticmethod
    def muted_text(text: str) -> str:
        """Gedimmter Text (inaktiv)"""
        return SimpleText.muted(text)

    @staticmethod
    def muted_text_two_line(text_line1: str, text_line2: str = "") -> list:
        return [
            format_html(
                '<span style="color: {};">{}</span>', Colors.SECONDARY, text_line1
            ),
            format_html(
                '<span style="color: {}; font-size: 0.9em;">{}</span>',
                Colors.SECONDARY,
                text_line2,
            ),
        ]

    @staticmethod
    def conditional_muted(content, is_muted: bool):
        """Content optional muten basierend auf Condition"""
        if is_muted:
            return format_html(
                '<span style="color: {};">{}</span>', Colors.SECONDARY, content
            )
        return content

    @staticmethod
    def highlight_box(
        content: str, color: Literal["success", "warning", "error", "info"] = "info"
    ) -> str:
        """Box mit Hintergrund"""
        colors = {
            "success": (Colors.BG_SUCCESS, Colors.TEXT_SUCCESS),
            "warning": (Colors.BG_WARNING, Colors.TEXT_WARNING),
            "error": (Colors.BG_ERROR, Colors.TEXT_ERROR),
            "info": (Colors.BG_INFO, Colors.TEXT_INFO),
        }
        bg, fg = colors[color]
        style = (
            f"padding: 10px; background: {bg}; color: {fg}; "
            "border-radius: 6px; border-left: 4px solid {fg};"
        )
        return format_html('<div style="{}">{}</div>', style, content)

    @staticmethod
    def link(
        text: str,
        href: str,
        color: Literal["success", "warning", "error", "info", "secondary"] = "info",
    ) -> str:
        """Link mit Farbe"""
        colors = {
            "success": Colors.SUCCESS,
            "warning": Colors.WARNING,
            "error": Colors.ERROR,
            "info": Colors.INFO,
            "secondary": Colors.SECONDARY,
        }
        fg = colors[color]
        return format_html('<a href="{}" style="color: {};">{}</a>', href, fg, text)
