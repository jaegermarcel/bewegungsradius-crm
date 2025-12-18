"""
Final Address Validator
Akzeptiert: house, farm, cottage, etc.
"""

import logging
from typing import Tuple, Optional
import requests
from django.utils.html import format_html
from django.forms import ValidationError
from django.core.cache import cache
import hashlib
import json

logger = logging.getLogger(__name__)


class AddressValidator:
    """Validiert Adressen über Nominatim (OpenStreetMap)"""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    TIMEOUT = 10
    CACHE_TIMEOUT = 86400  # 24 Stunden cachen
    USER_AGENT = "BewegungsradiusApp/1.0"
    DEBUG = True

    # ✅ Akzeptierte Gebäudetypen
    VALID_BUILDING_TYPES = {
        'house',           # Normales Haus
        'farm',            # Bauernhof
        'cottage',         # Häuschen
        'building',        # Gebäude
        'apartments',      # Mehrfamilienhaus
        'detached',        # Einfamilienhaus
        'semi',            # Doppelhaus
        'terrace',         # Reihenhaus
        'bungalow',        # Bungalow
    }

    # ❌ Nicht akzeptierte Typen
    INVALID_BUILDING_TYPES = {
        'residential',     # NUR STRASSE
        'road',            # NUR STRASSE
        'street',          # NUR STRASSE
    }

    def validate(self, street: str, house_number: str, postal_code: str, city: str, country: str = "Deutschland") -> Tuple[bool, Optional[str]]:
        """Validiert Adresse"""

        if self.DEBUG:
            logger.info(f"🔍 [DEBUG] Starting address validation")
            logger.info(f"   📍 Input: {street} {house_number}, {postal_code} {city}, {country}")

        if not self._has_required_fields(street, city):
            msg = "❌ Straße und Stadt sind erforderlich"
            if self.DEBUG:
                logger.warning(f"🔍 [DEBUG] {msg}")
            return False, msg

        try:
            cache_key = self._get_cache_key(street, house_number, postal_code, city)
            cached_result = cache.get(cache_key)

            if cached_result:
                if self.DEBUG:
                    logger.info(f"✅ [DEBUG] Result from cache!")
                logger.info(f"Address validation from cache: {street}, {city}")
                return cached_result

            if self.DEBUG:
                logger.info(f"🔍 [DEBUG] No cache found, making API request...")

            is_found, message = self._search_address(street, house_number, postal_code, city, country)
            result = (is_found, message)

            cache.set(cache_key, result, self.CACHE_TIMEOUT)

            if self.DEBUG:
                logger.info(f"✅ [DEBUG] Result cached")

            return result
        except Exception as e:
            logger.error(f"❌ [DEBUG] Address validation error: {e}", exc_info=True)
            return False, f"⚠️ Validierung nicht möglich: {str(e)}"

    def _has_required_fields(self, street: str, city: str) -> bool:
        """Prüft ob Pflichtfelder vorhanden sind"""
        return bool(street and city)

    def _get_cache_key(self, street: str, house_number: str, postal_code: str, city: str) -> str:
        """Generiert Cache-Schlüssel"""
        address_str = f"{street}_{house_number}_{postal_code}_{city}".lower()
        hash_digest = hashlib.md5(address_str.encode()).hexdigest()
        return f"address_validation_{hash_digest}"

    def _search_address(self, street: str, house_number: str, postal_code: str, city: str, country: str) -> Tuple[bool, str]:
        """Sucht Adresse via Nominatim"""
        address_parts = [f"{street} {house_number}".strip(), postal_code, city, country]
        address_string = ", ".join([p for p in address_parts if p])

        if self.DEBUG:
            logger.info(f"🔗 [DEBUG] Nominatim Query String: {address_string}")

        params = {
            'q': address_string,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }

        headers = {'User-Agent': self.USER_AGENT}

        try:
            if self.DEBUG:
                logger.info(f"📡 [DEBUG] Sending request to Nominatim...")

            response = requests.get(
                self.NOMINATIM_URL,
                params=params,
                timeout=self.TIMEOUT,
                headers=headers
            )

            if self.DEBUG:
                logger.info(f"📊 [DEBUG] Status Code: {response.status_code}")
                logger.info(f"🔗 [DEBUG] Full URL: {response.url}")
                logger.info(f"⏱️  [DEBUG] Response Time: {response.elapsed.total_seconds():.2f}s")

            response.raise_for_status()

            results = response.json()

            if self.DEBUG:
                logger.info(f"📋 [DEBUG] Results count: {len(results)}")
                if results:
                    logger.debug(f"📋 [DEBUG] Full Response:\n{json.dumps(results, indent=2, ensure_ascii=False)}")

            if not results:
                msg = f"❌ Adresse nicht gefunden: {address_string}"
                if self.DEBUG:
                    logger.warning(f"🔍 [DEBUG] {msg}")
                return False, msg

            result = results[0]
            address = result.get('address', {})

            # Extrahiere Details
            found_city = address.get('city') or address.get('town') or address.get('village') or address.get('hamlet')
            found_postal = address.get('postcode')
            found_house_number = address.get('house_number')
            result_type = result.get('type')
            importance = float(result.get('importance', 0))

            if self.DEBUG:
                logger.info(f"✅ [DEBUG] FIRST RESULT DETAILS:")
                logger.info(f"   Type: {result_type}")
                logger.info(f"   House Number: {found_house_number}")
                logger.info(f"   City: {found_city}")
                logger.info(f"   Postal: {found_postal}")
                logger.info(f"   Importance: {importance:.6f} ({importance*100:.4f}%)")
                logger.info(f"   Display Name: {result.get('display_name')}")

            # ✅ KEY CHECK: Ist es ein GÜLTIGER GEBÄUDETYP?
            is_valid_building = result_type in self.VALID_BUILDING_TYPES
            is_invalid_building = result_type in self.INVALID_BUILDING_TYPES

            if self.DEBUG:
                logger.info(f"🔍 [DEBUG] Validation Checks:")
                logger.info(f"   Type: {result_type}")
                logger.info(f"   Is Valid Building? {is_valid_building}")
                logger.info(f"   Is Invalid Building? {is_invalid_building}")

            # Validierungslogik
            message_parts = []

            # ❌ Problem 1: NUR STRASSE gefunden, nicht das Haus
            if is_invalid_building:
                msg = f"⚠️ NUR STRASSE gefunden, nicht die Hausnummer {house_number}!"
                message_parts.append(msg)
                if self.DEBUG:
                    logger.warning(f"🔍 [DEBUG] {msg}")
            elif is_valid_building:
                msg = f"✅ Adresse gefunden"
                message_parts.append(msg)
                if self.DEBUG:
                    logger.info(f"✅ [DEBUG] {msg} (Type: {result_type})")
            else:
                # Unbekannter Typ - aber hat Hausnummer, also OK
                if found_house_number:
                    msg = f"✅ Adresse gefunden (Type: {result_type})"
                    message_parts.append(msg)
                    if self.DEBUG:
                        logger.info(f"✅ [DEBUG] {msg}")
                else:
                    msg = f"⚠️ Unbekannter Typ: {result_type} (kein house_number)"
                    message_parts.append(msg)
                    if self.DEBUG:
                        logger.warning(f"🔍 [DEBUG] {msg}")

            # ❌ Problem 2: Stadt stimmt nicht
            city_match = self._cities_match(city, found_city)
            if self.DEBUG:
                logger.info(f"   City Match? {city_match} (input={city}, found={found_city})")

            if not city_match:
                msg = f"⚠️ Stadt: '{city}' vs gefunden '{found_city}'"
                message_parts.append(msg)
                if self.DEBUG:
                    logger.warning(f"🔍 [DEBUG] {msg}")

            # ❌ Problem 3: PLZ stimmt nicht
            if postal_code and found_postal:
                postal_match = self._postal_codes_match(postal_code, found_postal)
                if self.DEBUG:
                    logger.info(f"   Postal Match? {postal_match} (input={postal_code}, found={found_postal})")

                if not postal_match:
                    msg = f"⚠️ PLZ: '{postal_code}' vs gefunden '{found_postal}'"
                    message_parts.append(msg)
                    if self.DEBUG:
                        logger.warning(f"🔍 [DEBUG] {msg}")

            # ❌ Problem 4: Hausnummer stimmt nicht
            if house_number and found_house_number:
                house_match = self._house_numbers_match(house_number, found_house_number)
                if self.DEBUG:
                    logger.info(f"   House Number Match? {house_match} (input={house_number}, found={found_house_number})")

                if not house_match:
                    msg = f"⚠️ Hausnummer: '{house_number}' vs gefunden '{found_house_number}'"
                    message_parts.append(msg)
                    if self.DEBUG:
                        logger.warning(f"🔍 [DEBUG] {msg}")

            message = " | ".join(message_parts)

            if self.DEBUG:
                logger.info(f"📝 [DEBUG] Final Message: {message}")
                logger.info(f"✅ [DEBUG] Validation complete!")

            return True, message

        except requests.exceptions.Timeout:
            msg = "⚠️ Nominatim API antwortet zu langsam"
            logger.warning(f"❌ [DEBUG] Nominatim timeout: {address_string}")
            return False, msg
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                msg = "⚠️ Nominatim Server überlastet"
                logger.warning(f"❌ [DEBUG] Nominatim 403 Forbidden - Rate limit exceeded")
                return False, msg
            elif e.response.status_code == 503:
                msg = "⚠️ Nominatim Service temporär nicht verfügbar"
                logger.warning(f"❌ [DEBUG] Nominatim 503 Service Unavailable")
                return False, msg
            else:
                msg = f"⚠️ Nominatim Fehler ({e.response.status_code})"
                logger.error(f"❌ [DEBUG] Nominatim HTTP error: {e}")
                return False, msg
        except requests.exceptions.RequestException as e:
            msg = "⚠️ Nominatim Verbindungsfehler"
            logger.error(f"❌ [DEBUG] Nominatim request error: {e}")
            return False, msg

    @staticmethod
    def _cities_match(city1: str, city2: Optional[str]) -> bool:
        """Vergleicht Stadtnamen (fuzzy)"""
        if not city2:
            return False

        c1 = city1.lower().strip()
        c2 = city2.lower().strip()

        return c1 == c2 or c1 in c2 or c2 in c1

    @staticmethod
    def _postal_codes_match(plz1: str, plz2: str) -> bool:
        """Vergleicht PLZ"""
        p1 = plz1.replace(" ", "")
        p2 = plz2.replace(" ", "")
        return p1 == p2 or p1.startswith(p2) or p2.startswith(p1)

    @staticmethod
    def _house_numbers_match(house1: str, house2: str) -> bool:
        """Vergleicht Hausnummern"""
        h1 = house1.lower().strip()
        h2 = house2.lower().strip()
        return h1 == h2


class AdminAddressValidator:
    """Helper für Admin-Integration"""

    @staticmethod
    def validate_and_display(street: str, house_number: str, postal_code: str, city: str, country: str = "Deutschland") -> str:
        """Validiert Adresse und gibt formatiertes HTML zurück"""
        validator = AddressValidator()
        is_valid, message = validator.validate(street, house_number, postal_code, city, country)

        if not message:
            return ""

        if "❌" in message or "NUR STRASSE" in message:
            return format_html(
                '<div style="padding: 10px; color: #b81d1d; margin-top: 10px; border-radius: 4px;">{}</div>',
                message
            )
        elif "⚠️" in message:
            return format_html(
                '<div style="padding: 10px; color: #b34f12; margin-top: 10px; border-radius: 4px;">{}</div>',
                message
            )
        else:
            return format_html(
                '<div style="padding: 10px; color: #1e8f49; margin-top: 10px; border-radius: 4px;">{}</div>',
                message
            )


class CustomerAdminValidationMixin:
    """Mixin für Customer Admin - fügt Validierung hinzu"""

    def save_model(self, request, obj, form, change):
        """Überschreibe save_model um Validierung zu zeigen"""
        logger.info(f"💾 [SAVE] Saving customer: {obj.get_full_name()}")

        validator = AddressValidator()
        is_valid, message = validator.validate(
            obj.street,
            obj.house_number,
            obj.postal_code,
            obj.city,
            obj.country
        )

        super().save_model(request, obj, form, change)

        if message:
            logger.info(f"📝 [SAVE] Validation message: {message}")

            if "❌" in message or "NUR STRASSE" in message:
                self.message_user(request, message, level='ERROR')
            elif "⚠️" in message:
                self.message_user(request, message, level='WARNING')
            else:
                self.message_user(request, message, level='SUCCESS')

    def get_readonly_fields(self, request, obj=None):
        """Füge Validierungs-Feld hinzu (readonly)"""
        readonly = list(super().get_readonly_fields(request, obj))
        readonly.append('address_validation_display')
        return readonly

    def address_validation_display(self, obj):
        """Zeigt Validierungsergebnis"""
        if not obj or not obj.city or not obj.street:
            return format_html(
                '<div style="padding: 10px; background: #f3f4f6; border-left: 4px solid #d1d5db; color: #4b5563; margin-top: 10px; border-radius: 4px;">ℹ️ Bitte Straße und Stadt ausfüllen für Validierung</div>'
            )

        return AdminAddressValidator.validate_and_display(
            obj.street,
            obj.house_number,
            obj.postal_code,
            obj.city,
            obj.country
        )

    address_validation_display.short_description = "Adressvalidierung"


class CustomerAddressForm:
    """Form-Level Validierung (optional)"""

    @staticmethod
    def validate_address(cleaned_data):
        """Validiert Adresse in Form"""
        street = cleaned_data.get('street')
        city = cleaned_data.get('city')
        postal_code = cleaned_data.get('postal_code')
        house_number = cleaned_data.get('house_number')

        if not street or not city:
            return

        validator = AddressValidator()
        is_valid, message = validator.validate(street, house_number, postal_code, city)

        if "❌" in message or "NUR STRASSE" in message:
            raise ValidationError(f"⚠️ {message}")

        return cleaned_data