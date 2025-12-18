"""
bewegungsradius/tests/test_admin_styles.py - Tests für Admin Styles
===================================================================
✅ Colors
✅ BadgeStyle
✅ SimpleText
✅ IconBadge
✅ StatusIndicator
✅ DisplayHelpers
"""

import pytest
from datetime import datetime
from django.utils.safestring import SafeString

pytestmark = pytest.mark.django_db

# ==================== IMPORTS ====================

from bewegungsradius.core.admin_styles import (
    Colors,
    BadgeStyle,
    SimpleText,
    IconBadge,
    StatusIndicator,
    DisplayHelpers,
)


# ==================== COLORS TESTS ====================

class TestColors:
    """Tests für Color Palette"""

    def test_colors_has_status_colors(self):
        """Test: Status Colors sind definiert"""
        assert Colors.SUCCESS == '#10b981'
        assert Colors.WARNING == '#f59e0b'
        assert Colors.ERROR == '#ef4444'
        assert Colors.INFO == '#3b82f6'
        assert Colors.SECONDARY == '#6b7280'

    def test_colors_has_background_colors(self):
        """Test: Background Colors sind definiert"""
        assert Colors.BG_SUCCESS == '#dcfce7'
        assert Colors.BG_WARNING == '#fef3c7'
        assert Colors.BG_ERROR == '#fee2e2'
        assert Colors.BG_INFO == '#dbeafe'
        assert Colors.BG_SECONDARY == '#f3f4f6'

    def test_colors_has_text_colors(self):
        """Test: Text Colors sind definiert"""
        assert Colors.TEXT_SUCCESS == '#4E9F3D'
        assert Colors.TEXT_WARNING == '#92400e'
        assert Colors.TEXT_ERROR == '#991b1b'
        assert Colors.TEXT_INFO == '#1e40af'
        assert Colors.TEXT_ORANGE == '#ec7c25'


# ==================== BADGE STYLE TESTS ====================

class TestBadgeStyle:
    """Tests für BadgeStyle"""

    def test_badge_style_has_base_style(self):
        """Test: BASE_STYLE ist definiert"""
        assert 'display: inline-block;' in BadgeStyle.BASE_STYLE
        assert 'padding: 4px 8px;' in BadgeStyle.BASE_STYLE
        assert 'border-radius: 4px;' in BadgeStyle.BASE_STYLE

    def test_badge_returns_safestring(self):
        """Test: badge() gibt SafeString zurück"""
        result = BadgeStyle.badge('Test', 'success')
        assert isinstance(result, SafeString)

    def test_badge_success(self):
        """Test: Success Badge"""
        result = BadgeStyle.badge('Success', 'success')
        assert 'Success' in str(result)
        assert Colors.BG_SUCCESS in str(result)
        assert Colors.TEXT_SUCCESS in str(result)
        assert '<span' in str(result)

    def test_badge_warning(self):
        """Test: Warning Badge"""
        result = BadgeStyle.badge('Warning', 'warning')
        assert 'Warning' in str(result)
        assert Colors.BG_WARNING in str(result)
        assert Colors.TEXT_WARNING in str(result)

    def test_badge_error(self):
        """Test: Error Badge"""
        result = BadgeStyle.badge('Error', 'error')
        assert 'Error' in str(result)
        assert Colors.BG_ERROR in str(result)
        assert Colors.TEXT_ERROR in str(result)

    def test_badge_info(self):
        """Test: Info Badge"""
        result = BadgeStyle.badge('Info', 'info')
        assert 'Info' in str(result)
        assert Colors.BG_INFO in str(result)
        assert Colors.TEXT_INFO in str(result)

    def test_badge_secondary(self):
        """Test: Secondary Badge"""
        result = BadgeStyle.badge('Secondary', 'secondary')
        assert 'Secondary' in str(result)
        assert Colors.BG_SECONDARY in str(result)
        assert Colors.SECONDARY in str(result)

    def test_badge_contains_style(self):
        """Test: Badge enthält Style-Attribute"""
        result = BadgeStyle.badge('Test', 'info')
        assert 'style=' in str(result)
        assert 'background:' in str(result)
        assert 'color:' in str(result)


# ==================== SIMPLE TEXT TESTS ====================

class TestSimpleText:
    """Tests für SimpleText"""

    def test_text_returns_safestring(self):
        """Test: text() gibt SafeString zurück"""
        result = SimpleText.text('Test', Colors.SUCCESS)
        assert isinstance(result, SafeString)

    def test_text_with_color(self):
        """Test: Text mit Farbe"""
        result = SimpleText.text('Hello', Colors.SUCCESS)
        assert 'Hello' in str(result)
        assert Colors.SUCCESS in str(result)
        assert '<span' in str(result)

    def test_literal_text_success(self):
        """Test: literal_text mit success"""
        result = SimpleText.literal_text('Success', 'success')
        assert 'Success' in str(result)
        assert Colors.SUCCESS in str(result)

    def test_literal_text_warning(self):
        """Test: literal_text mit warning"""
        result = SimpleText.literal_text('Warning', 'warning')
        assert 'Warning' in str(result)
        assert Colors.WARNING in str(result)

    def test_literal_text_error(self):
        """Test: literal_text mit error"""
        result = SimpleText.literal_text('Error', 'error')
        assert 'Error' in str(result)
        assert Colors.ERROR in str(result)

    def test_literal_text_info(self):
        """Test: literal_text mit info"""
        result = SimpleText.literal_text('Info', 'info')
        assert 'Info' in str(result)
        assert Colors.INFO in str(result)

    def test_bold_returns_strong_tag(self):
        """Test: bold() gibt <strong> zurück"""
        result = SimpleText.bold('Bold', 'success')
        assert '<strong' in str(result)
        assert 'Bold' in str(result)
        assert Colors.SUCCESS in str(result)

    def test_icon_with_color(self):
        """Test: icon() mit Farbe"""
        result = SimpleText.icon('✓', 'success')
        assert '✓' in str(result)
        assert Colors.SUCCESS in str(result)
        assert 'font-size: 1.2em' in str(result)

    def test_icon_without_color(self):
        """Test: icon() ohne Farbe"""
        result = SimpleText.icon('✓', '')
        assert '✓' in str(result)
        assert '<span' in str(result)

    def test_muted_text(self):
        """Test: muted() gibt grauen Text zurück"""
        result = SimpleText.muted('Muted')
        assert 'Muted' in str(result)
        assert Colors.SECONDARY in str(result)


# ==================== ICON BADGE TESTS ====================

class TestIconBadge:
    """Tests für IconBadge"""

    def test_success_badge(self):
        """Test: Success Badge"""
        result = IconBadge.success()
        assert '✓' in str(result)
        assert Colors.BG_SUCCESS in str(result)

    def test_success_badge_custom_label(self):
        """Test: Success Badge mit custom Label"""
        result = IconBadge.success('OK')
        assert 'OK' in str(result)

    def test_warning_badge(self):
        """Test: Warning Badge"""
        result = IconBadge.warning()
        assert '⚠️' in str(result)
        assert Colors.BG_WARNING in str(result)

    def test_error_badge(self):
        """Test: Error Badge"""
        result = IconBadge.error()
        assert '✗' in str(result)
        assert Colors.BG_ERROR in str(result)

    def test_info_badge(self):
        """Test: Info Badge"""
        result = IconBadge.info()
        assert 'ℹ️' in str(result)
        assert Colors.BG_INFO in str(result)


# ==================== STATUS INDICATOR TESTS ====================

class TestStatusIndicator:
    """Tests für StatusIndicator"""

    # ========== MIT BADGE ==========

    def test_yes_no_true(self):
        """Test: yes_no() mit True"""
        result = StatusIndicator.yes_no(True)
        assert 'Ja' in str(result)
        assert '✓' in str(result)
        assert Colors.BG_SUCCESS in str(result)

    def test_yes_no_false(self):
        """Test: yes_no() mit False"""
        result = StatusIndicator.yes_no(False)
        assert 'Nein' in str(result)
        assert '✗' in str(result)
        assert Colors.BG_ERROR in str(result)

    def test_yes_no_custom_labels(self):
        """Test: yes_no() mit custom Labels"""
        result = StatusIndicator.yes_no(True, 'Aktiv', 'Inaktiv')
        assert 'Aktiv' in str(result)

    def test_active_inactive_active(self):
        """Test: active_inactive() aktiv"""
        result = StatusIndicator.active_inactive(True)
        assert 'Aktiv' in str(result)
        assert '●' in str(result)
        assert Colors.BG_SUCCESS in str(result)

    def test_active_inactive_inactive(self):
        """Test: active_inactive() inaktiv"""
        result = StatusIndicator.active_inactive(False)
        assert 'Inaktiv' in str(result)
        assert '●' in str(result)
        assert Colors.BG_SECONDARY in str(result)

    def test_email_status_sent_without_date(self):
        """Test: email_status() versendet ohne Datum"""
        result = StatusIndicator.email_status(True)
        assert 'Versendet' in str(result)
        assert Colors.BG_SUCCESS in str(result)

    def test_email_status_sent_with_date(self):
        """Test: email_status() versendet mit Datum"""
        sent_at = datetime(2024, 1, 15, 10, 30)
        result = StatusIndicator.email_status(True, sent_at)
        assert '15.01.2024' in str(result)
        assert '10:30' in str(result)

    def test_email_status_not_sent(self):
        """Test: email_status() nicht versendet"""
        result = StatusIndicator.email_status(False)
        assert 'Ausstehend' in str(result)
        assert '✗' in str(result)
        assert Colors.BG_ERROR in str(result)

    def test_payment_status_paid(self):
        """Test: payment_status() bezahlt"""
        result = StatusIndicator.payment_status('paid')
        assert 'Bezahlt' in str(result)
        assert Colors.BG_SUCCESS in str(result)

    def test_payment_status_pending(self):
        """Test: payment_status() ausstehend"""
        result = StatusIndicator.payment_status('pending')
        assert 'Ausstehend' in str(result)
        assert Colors.BG_WARNING in str(result)

    def test_payment_status_overdue(self):
        """Test: payment_status() überfällig"""
        result = StatusIndicator.payment_status('overdue')
        assert 'Überfällig' in str(result)
        assert Colors.BG_ERROR in str(result)

    def test_payment_status_cancelled(self):
        """Test: payment_status() storniert"""
        result = StatusIndicator.payment_status('cancelled')
        assert 'Storniert' in str(result)
        assert Colors.BG_ERROR in str(result)

    def test_payment_status_unknown(self):
        """Test: payment_status() unbekannt"""
        result = StatusIndicator.payment_status('unknown')
        assert 'unknown' in str(result)

    # ========== OHNE BADGE - NUR TEXT ==========

    def test_yes_no_simple_true(self):
        """Test: yes_no_simple() mit True"""
        result = StatusIndicator.yes_no_simple(True)
        assert 'Ja' in str(result)
        assert '✓' in str(result)
        assert Colors.SUCCESS in str(result)
        # Sollte KEIN Badge Background haben
        assert Colors.BG_SUCCESS not in str(result)

    def test_yes_no_simple_false(self):
        """Test: yes_no_simple() mit False"""
        result = StatusIndicator.yes_no_simple(False)
        assert 'Nein' in str(result)
        assert '✗' in str(result)
        assert Colors.ERROR in str(result)

    def test_active_inactive_simple_active(self):
        """Test: active_inactive_simple() aktiv"""
        result = StatusIndicator.active_inactive_simple(True)
        assert 'Aktiv' in str(result)
        assert '●' in str(result)
        assert Colors.SUCCESS in str(result)

    def test_active_inactive_simple_inactive(self):
        """Test: active_inactive_simple() inaktiv"""
        result = StatusIndicator.active_inactive_simple(False)
        assert 'Inaktiv' in str(result)
        assert '●' in str(result)
        assert Colors.SECONDARY in str(result)

    def test_email_status_simple_sent(self):
        """Test: email_status_simple() versendet"""
        result = StatusIndicator.email_status_simple(True)
        assert 'Versendet' in str(result)

    def test_email_status_simple_sent_with_date(self):
        """Test: email_status_simple() versendet mit Datum"""
        sent_at = datetime(2024, 1, 15, 10, 30)
        result = StatusIndicator.email_status_simple(True, sent_at)
        assert '15.01.2024' in str(result)
        assert '10:30' in str(result)

    def test_email_status_simple_not_sent(self):
        """Test: email_status_simple() nicht versendet"""
        result = StatusIndicator.email_status_simple(False)
        assert 'Ausstehend' in str(result)
        assert '✗' in str(result)

    def test_payment_status_simple_paid(self):
        """Test: payment_status_simple() bezahlt"""
        result = StatusIndicator.payment_status_simple('paid')
        assert 'Bezahlt' in str(result)
        assert '<strong' in str(result)

    # ========== NUR ICON ==========

    def test_yes_no_icon_only_true(self):
        """Test: yes_no_icon_only() mit True"""
        result = StatusIndicator.yes_no_icon_only(True)
        assert '✓' in str(result)
        assert Colors.SUCCESS in str(result)
        assert 'font-size: 1.2em' in str(result)

    def test_yes_no_icon_only_false(self):
        """Test: yes_no_icon_only() mit False"""
        result = StatusIndicator.yes_no_icon_only(False)
        assert '✗' in str(result)
        assert Colors.ERROR in str(result)

    def test_active_inactive_icon_only_active(self):
        """Test: active_inactive_icon_only() aktiv"""
        result = StatusIndicator.active_inactive_icon_only(True)
        assert '●' in str(result)
        assert Colors.SUCCESS in str(result)

    def test_active_inactive_icon_only_inactive(self):
        """Test: active_inactive_icon_only() inaktiv"""
        result = StatusIndicator.active_inactive_icon_only(False)
        assert '●' in str(result)
        assert Colors.SECONDARY in str(result)

    def test_email_status_icon_only_sent(self):
        """Test: email_status_icon_only() versendet"""
        result = StatusIndicator.email_status_icon_only(True)
        assert '✓' in str(result)
        assert Colors.SUCCESS in str(result)

    def test_email_status_icon_only_not_sent(self):
        """Test: email_status_icon_only() nicht versendet"""
        result = StatusIndicator.email_status_icon_only(False)
        assert '✗' in str(result)
        assert Colors.ERROR in str(result)


# ==================== DISPLAY HELPERS TESTS ====================

class TestDisplayHelpers:
    """Tests für DisplayHelpers"""

    def test_colored_text_success(self):
        """Test: colored_text() mit success"""
        result = DisplayHelpers.colored_text('Test', 'success')
        assert 'Test' in str(result)
        assert Colors.SUCCESS in str(result)

    def test_colored_text_warning(self):
        """Test: colored_text() mit warning"""
        result = DisplayHelpers.colored_text('Test', 'warning')
        assert 'Test' in str(result)
        assert Colors.WARNING in str(result)

    def test_colored_bold_returns_strong(self):
        """Test: colored_bold() gibt <strong> zurück"""
        result = DisplayHelpers.colored_bold('Test', 'success')
        assert '<strong' in str(result)
        assert 'Test' in str(result)
        assert Colors.SUCCESS in str(result)

    def test_muted_text(self):
        """Test: muted_text() gibt grauen Text zurück"""
        result = DisplayHelpers.muted_text('Muted')
        assert 'Muted' in str(result)
        assert Colors.SECONDARY in str(result)

    def test_muted_text_two_line(self):
        """Test: muted_text_two_line() gibt Liste zurück"""
        result = DisplayHelpers.muted_text_two_line('Line 1', 'Line 2')
        assert isinstance(result, list)
        assert len(result) == 2
        assert 'Line 1' in str(result[0])
        assert 'Line 2' in str(result[1])
        assert Colors.SECONDARY in str(result[0])

    def test_conditional_muted_true(self):
        """Test: conditional_muted() mit is_muted=True"""
        result = DisplayHelpers.conditional_muted('Test', True)
        assert 'Test' in str(result)
        assert Colors.SECONDARY in str(result)

    def test_conditional_muted_false(self):
        """Test: conditional_muted() mit is_muted=False"""
        result = DisplayHelpers.conditional_muted('Test', False)
        assert result == 'Test'

    def test_conditional_muted_with_html(self):
        """Test: conditional_muted() mit HTML Content"""
        html_content = '<strong>Bold</strong>'
        result = DisplayHelpers.conditional_muted(html_content, True)
        assert '&lt;strong&gt;Bold&lt;/strong&gt;' in str(result)
        assert Colors.SECONDARY in str(result)

    def test_highlight_box_success(self):
        """Test: highlight_box() mit success"""
        result = DisplayHelpers.highlight_box('Success', 'success')
        assert 'Success' in str(result)
        assert Colors.BG_SUCCESS in str(result)
        assert Colors.TEXT_SUCCESS in str(result)
        assert '<div' in str(result)
        assert 'padding:' in str(result)

    def test_highlight_box_warning(self):
        """Test: highlight_box() mit warning"""
        result = DisplayHelpers.highlight_box('Warning', 'warning')
        assert 'Warning' in str(result)
        assert Colors.BG_WARNING in str(result)

    def test_highlight_box_error(self):
        """Test: highlight_box() mit error"""
        result = DisplayHelpers.highlight_box('Error', 'error')
        assert 'Error' in str(result)
        assert Colors.BG_ERROR in str(result)

    def test_highlight_box_info(self):
        """Test: highlight_box() mit info"""
        result = DisplayHelpers.highlight_box('Info', 'info')
        assert 'Info' in str(result)
        assert Colors.BG_INFO in str(result)

    def test_link_with_color(self):
        """Test: link() mit Farbe"""
        result = DisplayHelpers.link('Click', '/url/', 'success')
        assert '<a' in str(result)
        assert 'Click' in str(result)
        assert '/url/' in str(result)
        assert Colors.SUCCESS in str(result)

    def test_link_default_info(self):
        """Test: link() mit default info color"""
        result = DisplayHelpers.link('Click', '/url/')
        assert '<a' in str(result)
        assert Colors.INFO in str(result)


# ==================== INTEGRATION TESTS ====================

class TestAdminStylesIntegration:
    """Integration Tests für zusammenarbeitende Komponenten"""

    def test_badge_and_simple_text_difference(self):
        """Test: Badge vs Simple Text haben unterschiedliche Styles"""
        badge = BadgeStyle.badge('Test', 'success')
        text = SimpleText.literal_text('Test', 'success')

        # Badge hat Background
        assert Colors.BG_SUCCESS in str(badge)
        # SimpleText hat KEINEN Background
        assert Colors.BG_SUCCESS not in str(text)

    def test_icon_badge_vs_icon_simple(self):
        """Test: IconBadge vs Simple Icon unterscheiden sich"""
        badge = IconBadge.success()
        icon = SimpleText.icon('✓', 'success')

        # Badge hat Background + Padding
        assert 'padding:' in str(badge)
        # Icon hat größere font-size
        assert 'font-size: 1.2em' in str(icon)

    def test_status_indicator_variants(self):
        """Test: StatusIndicator hat alle 3 Varianten"""
        # Mit Badge
        badge_result = StatusIndicator.yes_no(True)
        # Simple (nur Text)
        simple_result = StatusIndicator.yes_no_simple(True)
        # Nur Icon
        icon_result = StatusIndicator.yes_no_icon_only(True)

        # Alle enthalten ✓
        assert '✓' in str(badge_result)
        assert '✓' in str(simple_result)
        assert '✓' in str(icon_result)

        # Badge hat Background
        assert Colors.BG_SUCCESS in str(badge_result)
        # Simple hat KEINEN Background
        assert Colors.BG_SUCCESS not in str(simple_result)
        # Icon hat größere font-size
        assert 'font-size: 1.2em' in str(icon_result)

    def test_all_colors_used_in_badges(self):
        """Test: Alle Farben funktionieren in Badges"""
        colors = ['success', 'warning', 'error', 'info', 'secondary']

        for color in colors:
            result = BadgeStyle.badge('Test', color)
            assert isinstance(result, SafeString)
            assert 'Test' in str(result)

    def test_display_helpers_with_various_content(self):
        """Test: DisplayHelpers mit verschiedenen Content-Types"""
        # String
        result1 = DisplayHelpers.colored_text('Simple', 'success')
        assert 'Simple' in str(result1)

        # Bereits formatierter HTML (SafeString)
        formatted = SimpleText.bold('Bold', 'success')
        result2 = DisplayHelpers.conditional_muted(formatted, False)
        assert result2 == formatted

    def test_safestring_output_everywhere(self):
        """Test: Alle Methoden geben SafeString zurück"""
        outputs = [
            BadgeStyle.badge('Test', 'success'),
            SimpleText.text('Test', Colors.SUCCESS),
            SimpleText.literal_text('Test', 'success'),
            SimpleText.bold('Test', 'success'),
            SimpleText.icon('✓', 'success'),
            SimpleText.muted('Test'),
            IconBadge.success(),
            StatusIndicator.yes_no(True),
            StatusIndicator.yes_no_simple(True),
            StatusIndicator.yes_no_icon_only(True),
            DisplayHelpers.colored_text('Test', 'success'),
            DisplayHelpers.muted_text('Test'),
            DisplayHelpers.highlight_box('Test', 'success'),
            DisplayHelpers.link('Test', '/url/'),
        ]

        for output in outputs:
            assert isinstance(output, (SafeString, list))  # list für two_line


# ==================== EDGE CASES ====================

class TestEdgeCases:
    """Tests für Edge Cases"""

    def test_empty_string_handling(self):
        """Test: Leere Strings werden handled"""
        result = SimpleText.text('', Colors.SUCCESS)
        assert isinstance(result, SafeString)

    def test_special_characters_in_text(self):
        """Test: Sonderzeichen werden korrekt escaped"""
        result = SimpleText.text('<script>alert("xss")</script>', Colors.SUCCESS)
        # Django sollte automatisch escapen
        assert '&lt;' in str(result) or '<script>' not in str(result)

    def test_unicode_characters(self):
        """Test: Unicode-Zeichen funktionieren"""
        result = SimpleText.text('🎉 Erfolg! äöü', Colors.SUCCESS)
        assert '🎉' in str(result)
        assert 'Erfolg' in str(result)

    def test_very_long_text(self):
        """Test: Sehr langer Text"""
        long_text = 'A' * 1000
        result = SimpleText.text(long_text, Colors.SUCCESS)
        assert long_text in str(result)

    def test_none_datetime_handling(self):
        """Test: None datetime wird handled"""
        result = StatusIndicator.email_status_simple(True, None)
        assert 'Versendet' in str(result)

    def test_conditional_muted_with_safestring(self):
        """Test: conditional_muted mit SafeString Content"""
        safe_content = SimpleText.bold('Test', 'success')
        result = DisplayHelpers.conditional_muted(safe_content, True)
        assert Colors.SECONDARY in str(result)