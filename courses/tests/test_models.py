"""
courses/tests/test_models.py - Tests für Location und Course Models
===================================================================
✅ Location Model Tests
✅ Course Model Tests
✅ Properties & Methods
✅ Email Tracking
✅ Integration Tests
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.gis.geos import Point
from django.utils import timezone

pytestmark = pytest.mark.django_db

# ==================== IMPORTS ====================

from courses.models import Course, Location
from tests.factories import (CourseFactory, CourseWithParticipantsFactory,
                             CustomerFactory, LocationFactory, OfferFactory)

# ==================== FIXTURES ====================


@pytest.fixture
def location(db):
    """Location Fixture"""
    return LocationFactory()


@pytest.fixture
def course(db):
    """Course Fixture"""
    return CourseFactory()


@pytest.fixture
def course_with_participants(db):
    """Course mit Teilnehmern"""
    return CourseWithParticipantsFactory()


# ==================== LOCATION MODEL TESTS ====================


class TestLocationModel:
    """Tests für Location Model"""

    def test_location_creation(self):
        """Test: Location wird erstellt"""
        location = LocationFactory(
            name="Studio München",
            street="Hauptstraße",
            house_number="42",
            postal_code="80801",
            city="München",
        )

        assert location.id is not None
        assert location.name == "Studio München"
        assert location.street == "Hauptstraße"
        assert location.postal_code == "80801"

    def test_location_string_representation(self):
        """Test: __str__ gibt Name mit Teilnehmerzahl"""
        location = LocationFactory(name="Studio", max_participants=15)

        assert str(location) == "Studio (max. 15 Teilnehmer)"

    def test_location_get_full_address(self):
        """Test: get_full_address() kombiniert Adresse"""
        location = LocationFactory(
            street="Hauptstraße", house_number="42", postal_code="80801", city="München"
        )

        full_address = location.get_full_address()
        assert "Hauptstraße 42" in full_address
        assert "80801 München" in full_address

    def test_location_get_full_address_with_missing_fields(self):
        """Test: get_full_address() mit fehlenden Feldern"""
        location = LocationFactory(
            street="Hauptstraße", house_number="", postal_code="80801", city="München"
        )

        full_address = location.get_full_address()
        assert "Hauptstraße" in full_address
        assert "80801 München" in full_address

    def test_location_coordinates_optional(self):
        """Test: Koordinaten sind optional"""
        location = LocationFactory(coordinates=None)
        assert location.coordinates is None

    def test_location_created_at_auto_set(self):
        """Test: created_at wird automatisch gesetzt"""
        before = timezone.now()
        location = LocationFactory()
        after = timezone.now()

        assert before <= location.created_at <= after

    def test_location_updated_at_auto_set(self):
        """Test: updated_at wird automatisch gesetzt"""
        before = timezone.now()
        location = LocationFactory()
        after = timezone.now()

        assert before <= location.updated_at <= after

    @patch("courses.models.LocationGeocoder")
    def test_location_geocoding_on_save(self, mock_geocoder_class):
        """Test: Geocoding wird aufgerufen wenn nötig"""
        mock_geocoder = MagicMock()
        mock_geocoder_class.return_value = mock_geocoder
        mock_geocoder.geocode.return_value = None

        location = LocationFactory(
            street="Hauptstraße", house_number="42", city="München", coordinates=None
        )

        # Geocoding sollte aufgerufen worden sein
        mock_geocoder_class.assert_called()
        mock_geocoder.geocode.assert_called()

    @patch("courses.models.LocationGeocoder")
    def test_location_no_geocoding_if_coordinates_exist(self, mock_geocoder_class):
        """Test: Kein Geocoding wenn Koordinaten existieren"""
        mock_geocoder = MagicMock()
        mock_geocoder_class.return_value = mock_geocoder

        location = LocationFactory(coordinates=Point(13.405, 52.52))

        # Geocoding sollte NICHT aufgerufen werden
        mock_geocoder.geocode.assert_not_called()

    def test_location_ordering(self):
        """Test: Locations sind alphabetisch sortiert"""
        LocationFactory(name="Studio C")
        LocationFactory(name="Studio A")
        LocationFactory(name="Studio B")

        locations = Location.objects.all()
        names = [loc.name for loc in locations]
        assert names == ["Studio A", "Studio B", "Studio C"]


# ==================== COURSE MODEL TESTS ====================


class TestCourseModel:
    """Tests für Course Model"""

    def test_course_creation(self):
        """Test: Course wird erstellt"""
        course = CourseFactory(is_active=True, is_weekly=True)

        assert course.id is not None
        assert course.offer is not None
        assert course.is_active is True
        assert course.is_weekly is True

    def test_course_string_representation(self, course):
        """Test: __str__ gibt Title und Datum"""
        str_repr = str(course)
        assert course.offer.title in str_repr
        assert course.start_date.strftime("%d.%m.%Y") in str_repr

    def test_course_weekday_auto_calculated(self):
        """Test: weekday wird automatisch berechnet"""
        start_date = date(2025, 11, 24)  # Montag
        course = CourseFactory(start_date=start_date)

        # Weekday sollte 0 sein (Montag)
        assert course.weekday == 0

    def test_course_start_time_and_end_time(self):
        """Test: start_time und end_time können gesetzt werden"""
        from datetime import time

        start_time = time(10, 0)
        end_time = time(11, 30)

        course = CourseFactory(start_time=start_time, end_time=end_time)

        assert course.start_time == start_time
        assert course.end_time == end_time

    def test_course_email_tracking_flags(self):
        """Test: Email Tracking Flags"""
        course = CourseFactory()

        assert course.start_email_sent is False
        assert course.completion_email_sent is False
        assert course.start_email_sent_at is None
        assert course.completion_email_sent_at is None


# ==================== COURSE PROPERTIES TESTS ====================


class TestCourseProperties:
    """Tests für Course Properties"""

    def test_course_title_property(self, course):
        """Test: title Property gibt Offer-Titel zurück"""
        assert course.title == course.offer.title

    def test_course_course_type_property(self, course):
        """Test: course_type Property gibt Offer-Typ zurück"""
        assert course.course_type == course.offer.offer_type

    def test_course_price_property(self, course):
        """Test: price Property gibt Offer-Preis zurück"""
        assert course.price == course.offer.total_amount

    def test_course_is_zpp_certified_property(self):
        """Test: is_zpp_certified Property"""
        offer_without_zpp = OfferFactory(zpp_certification=None)
        course_without_zpp = CourseFactory(offer=offer_without_zpp)

        assert course_without_zpp.is_zpp_certified is False

    def test_course_zpp_prevention_id_property(self, course):
        """Test: zpp_prevention_id Property"""
        zpp_id = course.offer.zpp_prevention_id
        assert course.zpp_prevention_id == zpp_id

    def test_course_max_participants_inperson_property(self):
        """Test: max_participants_inperson Property"""
        location = LocationFactory(max_participants=20)
        course = CourseFactory(location=location)

        assert course.max_participants_inperson == 20

    def test_course_max_participants_without_location(self):
        """Test: max_participants_inperson wenn keine Location"""
        course = CourseFactory(location=None)

        assert course.max_participants_inperson == 0

    def test_course_total_participants_property(self, course_with_participants):
        """Test: total_participants zählt alle Teilnehmer"""
        inperson_count = course_with_participants.participants_inperson.count()
        total = course_with_participants.total_participants

        assert total >= inperson_count


# ==================== COURSE METHODS TESTS ====================


class TestCourseMethods:
    """Tests für Course Methods"""

    def test_course_mark_start_email_sent(self, course):
        """Test: mark_start_email_sent() setzt Flag und Zeitstempel"""
        assert course.start_email_sent is False
        assert course.start_email_sent_at is None

        before = timezone.now()
        course.mark_start_email_sent()
        after = timezone.now()

        assert course.start_email_sent is True
        assert before <= course.start_email_sent_at <= after

    def test_course_mark_completion_email_sent(self, course):
        """Test: mark_completion_email_sent() setzt Flag und Zeitstempel"""
        assert course.completion_email_sent is False
        assert course.completion_email_sent_at is None

        before = timezone.now()
        course.mark_completion_email_sent()
        after = timezone.now()

        assert course.completion_email_sent is True
        assert before <= course.completion_email_sent_at <= after

    def test_course_deactivate_if_expired_past_date(self):
        """Test: deactivate_if_expired() deaktiviert abgelaufene Kurse"""
        past_date = date.today() - timedelta(days=10)
        course = CourseFactory(end_date=past_date, is_active=True)

        result = course.deactivate_if_expired()

        assert result is True
        assert course.is_active is False

    def test_course_deactivate_if_expired_future_date(self):
        """Test: deactivate_if_expired() ändert nichts für zukünftige Kurse"""
        future_date = date.today() + timedelta(days=30)
        course = CourseFactory(end_date=future_date, is_active=True)

        result = course.deactivate_if_expired()

        assert result is False
        assert course.is_active is True

    def test_course_deactivate_if_expired_already_inactive(self):
        """Test: deactivate_if_expired() für bereits inaktive Kurse"""
        past_date = date.today() - timedelta(days=10)
        course = CourseFactory(end_date=past_date, is_active=False)

        result = course.deactivate_if_expired()

        assert result is False

    @patch("courses.models.CourseHolidayCalculator")
    def test_course_get_holidays_in_range(self, mock_calculator_class, course):
        """Test: get_holidays_in_range() ruft Service auf"""
        mock_calculator = MagicMock()
        mock_calculator_class.return_value = mock_calculator
        mock_calculator.get_holidays_in_range.return_value = []

        result = course.get_holidays_in_range()

        mock_calculator.get_holidays_in_range.assert_called_once()
        assert result == []

    @patch("courses.models.CourseScheduleCalculator")
    def test_course_get_course_dates(self, mock_calc_class, course):
        """Test: get_course_dates() ruft Service auf"""
        mock_calc = MagicMock()
        mock_calc_class.return_value = mock_calc
        mock_calc.get_course_dates.return_value = []

        result = course.get_course_dates()

        mock_calc.get_course_dates.assert_called_once()

    def test_course_email_status_display_both_sent(self):
        """Test: email_status_display wenn beide Emails versendet"""
        course = CourseFactory()
        course.mark_start_email_sent()
        course.mark_completion_email_sent()

        status = course.email_status_display

        assert "Start: ✓" in status
        assert "Abschluss: ✓" in status

    def test_course_email_status_display_none_sent(self):
        """Test: email_status_display wenn keine Emails versendet"""
        course = CourseFactory()

        status = course.email_status_display

        assert "Start: ✗" in status
        assert "Abschluss: ✗" in status


# ==================== COURSE PARTICIPANTS TESTS ====================


class TestCourseParticipants:
    """Tests für Course Participants"""

    def test_course_add_inperson_participant(self):
        """Test: Präsenz-Teilnehmer hinzufügen"""
        course = CourseFactory()
        customer = CustomerFactory()

        course.participants_inperson.add(customer)

        assert course.participants_inperson.count() == 1
        assert customer in course.participants_inperson.all()

    def test_course_add_online_participant(self):
        """Test: Online-Teilnehmer hinzufügen"""
        course = CourseFactory()
        customer = CustomerFactory()

        course.participants_online.add(customer)

        assert course.participants_online.count() == 1
        assert customer in course.participants_online.all()

    def test_course_is_full_inperson_true(self):
        """Test: is_full_inperson True wenn voll"""
        location = LocationFactory(max_participants=2)
        course = CourseFactory(location=location)

        customer1 = CustomerFactory()
        customer2 = CustomerFactory()

        course.participants_inperson.add(customer1, customer2)

        assert course.is_full_inperson is True

    def test_course_is_full_inperson_false(self):
        """Test: is_full_inperson False wenn nicht voll"""
        location = LocationFactory(max_participants=10)
        course = CourseFactory(location=location)

        customer = CustomerFactory()
        course.participants_inperson.add(customer)

        assert course.is_full_inperson is False

    def test_course_is_full_inperson_no_location(self):
        """Test: is_full_inperson False ohne Location"""
        course = CourseFactory(location=None)

        assert course.is_full_inperson is False


# ==================== COURSE SIGNALS & CELERY TESTS ====================


class TestCourseSignalsAndCelery:
    """Tests für Course Signals und Celery"""

    @patch("courses.models.CeleryTaskManager")
    def test_course_save_calls_celery_task_manager(self, mock_task_manager_class):
        """Test: Course.save() ruft CeleryTaskManager auf"""
        mock_task_manager = MagicMock()
        mock_task_manager_class.return_value = mock_task_manager

        course = CourseFactory()

        # Task Manager sollte aufgerufen worden sein
        mock_task_manager_class.assert_called()
        mock_task_manager.manage_course_start_email_task.assert_called()

    @patch("courses.models.CeleryTaskManager")
    def test_course_delete_calls_celery_task_manager(self, mock_task_manager_class):
        """Test: Course.delete() ruft CeleryTaskManager auf"""
        mock_task_manager = MagicMock()
        mock_task_manager_class.return_value = mock_task_manager

        course = CourseFactory()
        course.delete()

        # Task Manager sollte aufgerufen worden sein
        mock_task_manager.delete_course_task.assert_called()


# ==================== COURSE INTEGRATION TESTS ====================


class TestCourseIntegration:
    """Integration Tests für Course"""

    def test_full_course_workflow(self):
        """Test: Kompletter Course Workflow"""
        # 1. Course mit Location und Teilnehmern erstellen
        location = LocationFactory(max_participants=20)
        course = CourseFactory(location=location)

        customers = CustomerFactory.create_batch(5)
        for customer in customers:
            course.participants_inperson.add(customer)

        # 2. Assertions
        assert course.total_participants == 5
        assert course.is_full_inperson is False

        # 3. Start-Email markieren
        course.mark_start_email_sent()
        assert course.start_email_sent is True

        # 4. Abschluss-Email markieren
        course.mark_completion_email_sent()
        assert course.completion_email_sent is True

    def test_course_expiration_workflow(self):
        """Test: Course Verfallsdatum Workflow"""
        # 1. Course mit Verfallsdatum erstellen
        past_date = date.today() - timedelta(days=5)
        course = CourseFactory(end_date=past_date, is_active=True)

        # 2. Course sollte noch aktiv sein
        assert course.is_active is True

        # 3. Deaktivieren
        course.deactivate_if_expired()

        # 4. Course sollte inaktiv sein
        assert course.is_active is False

    def test_course_with_multiple_location_courses(self):
        """Test: Mehrere Kurse an gleicher Location"""
        location = LocationFactory()

        course1 = CourseFactory(location=location)
        course2 = CourseFactory(location=location)

        assert location.courses.count() == 2
