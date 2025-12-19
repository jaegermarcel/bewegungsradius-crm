"""
courses/tests/test_email_services.py - Tests für Course Email Services
====================================================================
✅ DiscountCodeRepository Tests
✅ DiscountCodeService Tests
✅ CourseStartEmailService Tests
✅ CourseCompletionEmailService Tests
✅ Integration Tests
"""

from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.django_db


# ==================== IMPORTS ====================

from courses.email_services.course_emails import (CourseCompletionEmailService,
                                                  CourseStartEmailService,
                                                  DiscountCodeRepository,
                                                  DiscountCodeService)
from customers.models import CustomerDiscountCode
from tests.factories import (CompanyInfoFactory, CourseFactory,
                             CourseWithParticipantsFactory, CustomerFactory)

# ==================== FIXTURES ====================


@pytest.fixture
def company_info(db):
    """Company Info Fixture"""
    return CompanyInfoFactory()


@pytest.fixture
def customer(db):
    """Customer Fixture"""
    return CustomerFactory()


@pytest.fixture
def course(db):
    """Course Fixture"""
    return CourseFactory()


@pytest.fixture
def course_with_participants(db):
    """Course mit Teilnehmern"""
    return CourseWithParticipantsFactory()


@pytest.fixture
def discount_code(db, customer, course):
    """Discount Code für Course und Customer"""
    return CustomerDiscountCode.objects.create(
        customer=customer,
        course=course,
        code="COURSE-DISCOUNT",
        discount_type="percentage",
        discount_value=10.00,
        valid_from=date.today(),
        valid_until=date.today() + timedelta(days=30),
        status="sent",
    )


# ==================== DISCOUNT CODE REPOSITORY TESTS ====================


class TestDiscountCodeRepository:
    """Tests für DiscountCodeRepository"""

    def test_repository_initialization(self):
        """Test: Repository wird initialisiert"""
        repo = DiscountCodeRepository()
        assert repo is not None

    def test_find_active_for_course_and_customer_found(
        self, customer, course, discount_code
    ):
        """Test: Findet aktiven Rabattcode"""
        repo = DiscountCodeRepository()
        result = repo.find_active_for_course_and_customer(course, customer)

        assert result == discount_code
        assert result.code == "COURSE-DISCOUNT"

    def test_find_active_for_course_and_customer_not_found(self, customer, course):
        """Test: Gibt None zurück wenn kein Code"""
        repo = DiscountCodeRepository()
        result = repo.find_active_for_course_and_customer(course, customer)

        assert result is None

    def test_find_active_for_course_and_customer_wrong_customer(
        self, course, discount_code
    ):
        """Test: Findet Code nicht für anderen Kunden"""
        other_customer = CustomerFactory()
        repo = DiscountCodeRepository()
        result = repo.find_active_for_course_and_customer(course, other_customer)

        assert result is None

    def test_find_active_for_course_and_customer_wrong_course(
        self, customer, discount_code
    ):
        """Test: Findet Code nicht für anderen Kurs"""
        other_course = CourseFactory()
        repo = DiscountCodeRepository()
        result = repo.find_active_for_course_and_customer(other_course, customer)

        assert result is None

    def test_find_active_for_course_and_customer_expired(self, customer, course):
        """Test: Findet Code nicht wenn abgelaufen"""
        expired_code = CustomerDiscountCode.objects.create(
            customer=customer,
            course=course,
            code="EXPIRED",
            discount_type="percentage",
            discount_value=10.00,
            valid_from=date.today() - timedelta(days=60),
            valid_until=date.today() - timedelta(days=10),
            status="expired",
        )

        repo = DiscountCodeRepository()
        result = repo.find_active_for_course_and_customer(course, customer)

        assert result is None

    def test_find_active_for_course_and_customer_only_planned_sent(
        self, customer, course
    ):
        """Test: Findet nur planned oder sent Status"""
        planned = CustomerDiscountCode.objects.create(
            customer=customer,
            course=course,
            code="PLANNED",
            discount_type="percentage",
            discount_value=10.00,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            status="planned",
        )

        repo = DiscountCodeRepository()
        result = repo.find_active_for_course_and_customer(course, customer)

        assert result == planned


# ==================== DISCOUNT CODE SERVICE TESTS ====================


class TestDiscountCodeService:
    """Tests für DiscountCodeService"""

    def test_service_initialization_default_repository(self):
        """Test: Service mit Default Repository"""
        service = DiscountCodeService()
        assert service.repository is not None
        assert isinstance(service.repository, DiscountCodeRepository)

    def test_service_initialization_custom_repository(self):
        """Test: Service mit Custom Repository"""
        mock_repo = Mock()
        service = DiscountCodeService(repository=mock_repo)
        assert service.repository == mock_repo

    def test_get_discount_code_for_participant_success(
        self, customer, course, discount_code
    ):
        """Test: Gibt Rabattcode zurück wenn vorhanden"""
        service = DiscountCodeService()
        result = service.get_discount_code_for_participant(course, customer)

        assert result == discount_code

    def test_get_discount_code_for_participant_not_found(self, customer, course):
        """Test: Gibt None zurück wenn kein Code"""
        service = DiscountCodeService()
        result = service.get_discount_code_for_participant(course, customer)

        assert result is None

    @patch("courses.email_services.course_emails.logger")
    def test_get_discount_code_logs_success(
        self, mock_logger, customer, course, discount_code
    ):
        """Test: Loggt erfolgreiche Suche"""
        service = DiscountCodeService()
        service.get_discount_code_for_participant(course, customer)

        mock_logger.info.assert_called()

    @patch("courses.email_services.course_emails.logger")
    def test_get_discount_code_logs_error_on_exception(self, mock_logger):
        """Test: Loggt Fehler bei Exception"""
        mock_repo = Mock()
        mock_repo.find_active_for_course_and_customer.side_effect = Exception(
            "DB Error"
        )

        service = DiscountCodeService(repository=mock_repo)
        result = service.get_discount_code_for_participant(Mock(), Mock())

        assert result is None
        mock_logger.error.assert_called()


# ==================== COURSE START EMAIL SERVICE TESTS ====================


class TestCourseStartEmailService:
    """Tests für CourseStartEmailService"""

    @pytest.fixture
    def service(self, company_info):
        """Service Fixture"""
        return CourseStartEmailService(company_info=company_info)

    def test_service_initialization(self, company_info):
        """Test: Service wird initialisiert"""
        service = CourseStartEmailService(company_info=company_info)
        assert service.company_info == company_info

    def test_template_path_set(self, service):
        """Test: Template Path ist gesetzt"""
        assert service.TEMPLATE_PATH == "email/notifications/course_start_email.html"

    def test_get_template_config(self, service, course, customer, company_info):
        """Test: get_template_config erstellt Config"""
        config = service.get_template_config(course=course, customer=customer)

        assert config.template_path == service.TEMPLATE_PATH
        assert config.context["customer"] == customer
        assert config.context["course"] == course
        assert config.context["company"] == company_info

    def test_build_email_payload(self, service, course, customer):
        """Test: build_email_payload erstellt Payload"""
        payload = service.build_email_payload(
            course=course, customer=customer, html_content="<p>Course Start</p>"
        )

        assert payload.subject == f"Kurs startet bald: {course.offer.title}"
        assert payload.html_content == "<p>Course Start</p>"
        assert payload.recipient_email == customer.email

    def test_build_email_payload_no_html_content(self, service, course, customer):
        """Test: build_email_payload ohne html_content"""
        payload = service.build_email_payload(course=course, customer=customer)

        assert payload.html_content == ""

    @patch(
        "courses.email_services.course_emails.CourseStartEmailService.send_bulk_emails"
    )
    def test_send_course_start_email(
        self, mock_bulk, service, course_with_participants
    ):
        """Test: send_course_start_email versendet an alle Teilnehmer"""
        mock_bulk.return_value = {"sent": 5, "errors": 0}

        result = service.send_course_start_email(course_with_participants)

        assert result["sent"] == 5
        mock_bulk.assert_called_once()

    @patch(
        "courses.email_services.course_emails.CourseStartEmailService.send_bulk_emails"
    )
    def test_send_course_start_email_mixed_participants(self, mock_bulk, service):
        """Test: send_course_start_email mit Präsenz + Online"""
        course = CourseFactory()
        inperson = CustomerFactory.create_batch(3)
        online = CustomerFactory.create_batch(2)

        for p in inperson:
            course.participants_inperson.add(p)
        for p in online:
            course.participants_online.add(p)

        mock_bulk.return_value = {"sent": 5, "errors": 0}

        service.send_course_start_email(course)

        # Sollte alle 5 Teilnehmer bekommen
        call_args = mock_bulk.call_args[0][0]
        assert len(call_args) == 5

    @patch(
        "courses.email_services.course_emails.CourseStartEmailService.send_bulk_emails"
    )
    def test_send_course_start_email_empty_participants(
        self, mock_bulk, service, course
    ):
        """Test: send_course_start_email ohne Teilnehmer"""
        mock_bulk.return_value = {"sent": 0, "errors": 0}

        service.send_course_start_email(course)

        call_args = mock_bulk.call_args[0][0]
        assert len(call_args) == 0


# ==================== COURSE COMPLETION EMAIL SERVICE TESTS ====================


class TestCourseCompletionEmailService:
    """Tests für CourseCompletionEmailService"""

    @pytest.fixture
    def service(self, company_info):
        """Service Fixture"""
        return CourseCompletionEmailService(company_info=company_info)

    def test_service_initialization(self, company_info):
        """Test: Service wird initialisiert"""
        service = CourseCompletionEmailService(company_info=company_info)
        assert service.company_info == company_info
        assert service.discount_service is not None

    def test_service_initialization_custom_discount_service(self, company_info):
        """Test: Service mit Custom DiscountCodeService"""
        mock_service = Mock()
        service = CourseCompletionEmailService(
            company_info=company_info, discount_service=mock_service
        )
        assert service.discount_service == mock_service

    def test_template_path_set(self, service):
        """Test: Template Path ist gesetzt"""
        assert (
            service.TEMPLATE_PATH == "email/notifications/course_completion_email.html"
        )

    def test_get_template_config_with_discount(
        self, service, course, customer, company_info, discount_code
    ):
        """Test: get_template_config mit Rabattcode"""
        config = service.get_template_config(course=course, customer=customer)

        assert config.template_path == service.TEMPLATE_PATH
        assert config.context["customer"] == customer
        assert config.context["course"] == course
        assert config.context["company"] == company_info
        # discount_code wird vom Service geladen
        assert "discount_code" in config.context

    def test_get_template_config_without_discount(self, service, course, customer):
        """Test: get_template_config ohne Rabattcode"""
        config = service.get_template_config(course=course, customer=customer)

        assert config.context["discount_code"] is None

    def test_build_email_payload(self, service, course, customer):
        """Test: build_email_payload erstellt Payload"""
        payload = service.build_email_payload(
            course=course, customer=customer, html_content="<p>Course Complete</p>"
        )

        assert payload.subject == f"Glückwunsch zum Abschluss: {course.offer.title}"
        assert payload.html_content == "<p>Course Complete</p>"
        assert payload.recipient_email == customer.email

    def test_build_email_payload_no_html_content(self, service, course, customer):
        """Test: build_email_payload ohne html_content"""
        payload = service.build_email_payload(course=course, customer=customer)

        assert payload.html_content == ""

    @patch(
        "courses.email_services.course_emails.CourseCompletionEmailService.send_bulk_emails"
    )
    def test_send_course_completion_email(
        self, mock_bulk, service, course_with_participants
    ):
        """Test: send_course_completion_email versendet an alle Teilnehmer"""
        mock_bulk.return_value = {"sent": 5, "errors": 0}

        result = service.send_course_completion_email(course_with_participants)

        assert result["sent"] == 5
        mock_bulk.assert_called_once()

    @patch(
        "courses.email_services.course_emails.CourseCompletionEmailService.send_bulk_emails"
    )
    def test_send_course_completion_email_mixed_participants(self, mock_bulk, service):
        """Test: send_course_completion_email mit Präsenz + Online"""
        course = CourseFactory()
        inperson = CustomerFactory.create_batch(3)
        online = CustomerFactory.create_batch(2)

        for p in inperson:
            course.participants_inperson.add(p)
        for p in online:
            course.participants_online.add(p)

        mock_bulk.return_value = {"sent": 5, "errors": 0}

        service.send_course_completion_email(course)

        # Sollte alle 5 Teilnehmer bekommen
        call_args = mock_bulk.call_args[0][0]
        assert len(call_args) == 5

    @patch(
        "courses.email_services.course_emails.CourseCompletionEmailService.send_bulk_emails"
    )
    def test_send_course_completion_email_empty_participants(
        self, mock_bulk, service, course
    ):
        """Test: send_course_completion_email ohne Teilnehmer"""
        mock_bulk.return_value = {"sent": 0, "errors": 0}

        service.send_course_completion_email(course)

        call_args = mock_bulk.call_args[0][0]
        assert len(call_args) == 0


# ==================== INTEGRATION TESTS ====================


class TestCourseEmailServicesIntegration:
    """Integration Tests für Course Email Services"""

    def test_full_course_email_workflow_start(self, company_info):
        """Test: Kompletter Workflow - Kurs Start Email"""
        # 1. Course mit Teilnehmern
        CourseWithParticipantsFactory()

        # 2. Service erstellen
        service = CourseStartEmailService(company_info=company_info)

        # 3. Email Service initialisiert
        assert service.company_info == company_info
        assert service.TEMPLATE_PATH == "email/notifications/course_start_email.html"

    def test_full_course_email_workflow_completion(self, company_info):
        """Test: Kompletter Workflow - Kurs Completion Email"""
        # 1. Course mit Teilnehmern
        course = CourseWithParticipantsFactory()

        # 2. Rabattkode für einen Teilnehmer
        participant = course.participants_inperson.first()
        discount_code = CustomerDiscountCode.objects.create(
            customer=participant,
            course=course,
            code="COMPLETION-DISCOUNT",
            discount_type="percentage",
            discount_value=15.00,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            status="sent",
        )

        # 3. Service erstellen
        service = CourseCompletionEmailService(company_info=company_info)

        # 4. Template Config laden
        config = service.get_template_config(course=course, customer=participant)

        # 5. Rabattcode sollte in Context sein
        assert config.context["discount_code"] == discount_code

    def test_discount_code_service_in_completion_email(self, company_info):
        """Test: DiscountCodeService wird in CompletionEmailService genutzt"""
        course = CourseFactory()
        customer = CustomerFactory()

        # Discount Code erstellen
        discount_code = CustomerDiscountCode.objects.create(
            customer=customer,
            course=course,
            code="TEST-DISCOUNT",
            discount_type="percentage",
            discount_value=20.00,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            status="sent",
        )

        # Service mit DiscountCodeService
        service = CourseCompletionEmailService(company_info=company_info)

        # Config laden sollte Rabattcode finden
        config = service.get_template_config(course=course, customer=customer)
        assert config.context["discount_code"] == discount_code

    def test_multiple_courses_different_participants(self, company_info):
        """Test: Verschiedene Kurse mit verschiedenen Teilnehmern"""
        course1 = CourseWithParticipantsFactory()
        course2 = CourseWithParticipantsFactory()

        service = CourseStartEmailService(company_info=company_info)

        # Beide Kurse sollten ihre Teilnehmer haben
        assert course1.participants_inperson.count() > 0
        assert course2.participants_inperson.count() > 0

        # Services sollten unterschiedliche Template Configs erstellen
        participant1 = course1.participants_inperson.first()
        participant2 = course2.participants_inperson.first()

        config1 = service.get_template_config(course=course1, customer=participant1)
        config2 = service.get_template_config(course=course2, customer=participant2)

        assert config1.context["course"] == course1
        assert config2.context["course"] == course2
