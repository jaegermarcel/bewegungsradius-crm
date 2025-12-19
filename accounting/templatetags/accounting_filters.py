from django import template

register = template.Library()


@register.filter
def format_thousands(value):
    """Formatiert Tausender mit Punkt und behält 2 Dezimalstellen (z.B. 1.234,56)"""
    try:
        value = float(value)
        # Formatiere mit 2 Dezimalstellen und Tausender-Punkt
        formatted = (
            f"{value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        )
        return formatted
    except (ValueError, TypeError):
        return value
