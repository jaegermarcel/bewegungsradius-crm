"""
customers/services.py - Business Logic Layer
==============================================
Alle E-Mail- und Kundenlogik, unabhängig von Django Admin
"""
from datetime import datetime

from django.utils import timezone
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from django.contrib.gis.geos import Point
import time
import logging

logger = logging.getLogger(__name__)


class AddressGeocoder:
    """Service für Adress-Geocoding"""

    TIMEOUT = 10
    DELAY = 1  # Verzögerung zwischen Requests (respektvolle API-Nutzung)
    USER_AGENT = "bewegungsradius_app"

    def __init__(self):
        self.geolocator = Nominatim(user_agent=self.USER_AGENT)

    def geocode(self, address):
        """Konvertiert Adresse in Koordinaten oder None"""
        if not address:
            return None

        try:
            time.sleep(self.DELAY)
            location = self.geolocator.geocode(address, timeout=self.TIMEOUT)

            if location:
                return Point(location.longitude, location.latitude, srid=4326)

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding Fehler für '{address}': {e}")

        return None


class DiscountCodeValidator:
    """Service für Rabattcode-Validierung"""

    def __init__(self, discount_code):
        self.code = discount_code

    def validate(self):
        """Rückgabe: (is_valid: bool, message: str)"""
        if self.code.status == 'used':
            return False, "Code wurde bereits verwendet"

        if self.code.status == 'cancelled':
            return False, "Code wurde storniert"

        if self.code.status == 'expired':
            return False, "Code ist abgelaufen"

        if not self._is_in_validity_period():
            return False, self._get_validity_message()

        return True, "Code ist gültig"

    def _is_in_validity_period(self):
        """Prüft ob Code innerhalb des Gültigkeitszeitraums ist"""
        today = timezone.now().date()
        return self.code.valid_from <= today <= self.code.valid_until

    def _get_validity_message(self):
        """Gibt passende Fehlermeldung für Ungültigkeit zurück"""
        today = timezone.now().date()

        if self.code.valid_from > today:
            return "Code ist noch nicht gültig"

        return "Code ist abgelaufen"


class DiscountCodeGenerator:
    """Service für Rabattcode-Generierung"""

    COURSE_INITIALS = {
        'rueckbildung': 'RB',
        'rückbildung': 'RB',
        'pilates': 'P',
        'body-workout': 'BW',
    }

    def generate(self, course, customer):
        """Generiert einen eindeutigen kursspezifischen Code

        Format: [Kurs-Initial][Monat][Jahr-2-Digit][Kunden-Initialen]
        Beispiel: RB1025MJ (Rückbildung, Oktober 2025, Marcel Jäger)
        """
        base_code = self._build_base_code(course, customer)
        return self._ensure_uniqueness(base_code)

    def _build_base_code(self, course, customer):
        """Erstellt Basis-Code aus Komponenten"""
        course_initial = self._get_course_initial(course)
        date_part = self._get_date_part(course)
        customer_initials = self._get_customer_initials(customer)

        return f"{course_initial}{date_part}{customer_initials}"

    def _get_course_initial(self, course):
        """Ermittelt Kurs-Initialen"""
        course_title = course.offer.title.lower()

        for key, initial in self.COURSE_INITIALS.items():
            if key in course_title:
                return initial

        return 'XX'  # Fallback

    def _get_date_part(self, course):
        """Extrahiert Monat und Jahr aus Kurs-Enddatum"""
        if course.end_date:
            return course.end_date.strftime('%m%y')

        return datetime.now().strftime('%m%y')

    def _get_customer_initials(self, customer):
        """Extrahiert Initialen aus Kundennamen"""
        return f"{customer.first_name[0]}{customer.last_name[0]}".upper()

    def _ensure_uniqueness(self, base_code):
        """Prüft Eindeutigkeit und hängt Nummer an falls nötig"""
        from customers.models import CustomerDiscountCode

        if not CustomerDiscountCode.objects.filter(code=base_code).exists():
            return base_code

        counter = 1
        while CustomerDiscountCode.objects.filter(
                code=f"{base_code}{counter}"
        ).exists():
            counter += 1

        return f"{base_code}{counter}"


class DiscountCodeCalculator:
    """Service für Rabattberechnungen"""

    @staticmethod
    def calculate_discount_amount(discount_code, amount):
        """Berechnet Rabattbetrag basierend auf Code-Typ"""
        if discount_code.discount_type == 'percentage':
            return amount * (discount_code.discount_value / 100)

        return min(discount_code.discount_value, amount)

    @staticmethod
    def calculate_final_amount(original_amount, discount_amount):
        """Berechnet finalen Betrag nach Rabatt"""
        return max(original_amount - discount_amount, 0)


class DiscountCodeFormatter:
    """Service für Rabattcode-Formatierung"""

    @staticmethod
    def format_discount_display(discount_code):
        """Formatiert Rabatt für Anzeige"""
        if discount_code.discount_type == 'percentage':
            return f"{discount_code.discount_value}%"

        return f"{discount_code.discount_value}€"

    @staticmethod
    def format_full_info(discount_code):
        """Formatiert vollständige Rabattinfo"""
        return (
            f"{discount_code.code} - "
            f"{DiscountCodeFormatter.format_discount_display(discount_code)} "
            f"({discount_code.get_reason_display()})"
        )