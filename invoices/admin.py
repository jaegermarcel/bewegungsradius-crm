from typing import Union

from django import forms
from django.contrib import admin
from django.http import HttpRequest
from django.shortcuts import redirect
from django.utils.html import format_html
from import_export.admin import ExportActionModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminSelect2Widget

from bewegungsradius.core.admin_styles import (
    Colors,
    DisplayHelpers,
    SimpleText,
    StatusIndicator,
)
from customers.models import CustomerDiscountCode

from .admin_services import InvoiceActionHandler, InvoicePDFDownloadHandler
from .models import Invoice

# ========================================
# ✅ CUSTOM FORM MIT GEFILTERTEN RABATTCODES
# ========================================


class InvoiceAdminForm(forms.ModelForm):
    """Custom Form: Rabattcodes nur vom aktuellen Kunden"""

    discount_code = forms.ModelChoiceField(
        queryset=CustomerDiscountCode.objects.none(),
        required=False,
        empty_label="— Kein Rabattcode —",
        widget=UnfoldAdminSelect2Widget(),  # ← UNFOLD DROPDOWN!
        label="Rabattcode",
    )

    class Meta:
        model = Invoice
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ SCHRITT 1: Wenn wir ein existierendes Invoice bearbeiten
        if self.instance and self.instance.customer:
            # Filter Rabattcodes nur für diesen Kunden
            self.fields["discount_code"].queryset = CustomerDiscountCode.objects.filter(
                customer=self.instance.customer
            ).select_related("customer")

    def clean(self):
        """Zusätzliche Validierung: Rabattcode muss zum Kunden passen"""
        cleaned_data = super().clean()
        discount_code = cleaned_data.get("discount_code")
        customer = cleaned_data.get("customer")

        # Prüfe: Wenn Rabattcode, muss er vom Kunden sein
        if discount_code and customer:
            if discount_code.customer != customer:
                raise forms.ValidationError(
                    "❌ Der Rabattcode gehört nicht zu diesem Kunden!"
                )

        return cleaned_data


@admin.register(Invoice)
class InvoiceAdmin(SimpleHistoryAdmin, ExportActionModelAdmin, ModelAdmin):
    form = InvoiceAdminForm

    list_display = [
        "display_as_two_line_heading",
        "item_display",
        "amount_display",
        "discount_display",
        "status_display",
        "dates_display",
        "email_status_display",
        "zpp_indicator",
    ]

    list_display_links = ["display_as_two_line_heading"]

    ordering = ["-invoice_number"]

    search_fields = [
        "invoice_number",
        "customer__first_name",
        "customer__last_name",
        "course__offer__title",
        "offer__title",
        "course_id_custom",
    ]

    list_filter_submit = True
    list_filter = [
        "status",
        "email_sent",
        "is_prevention_certified",
        "is_tax_exempt",
        ("issue_date", RangeDateFilter),
        ("due_date", RangeDateFilter),
    ]

    list_per_page = 50

    readonly_fields = [
        "invoice_number",
        "course_id_custom",
        "created_at",
        "updated_at",
        "tax_amount_display",
        "total_amount_display_readonly",
        "cancelled_at",
        "cancelled_invoice_number",
        "discount_amount",
        "email_sent_at",
    ]

    # Changeform Actions
    actions_detail = [
        "send_invoice_email_action",
        "mark_as_sent_action",
        "mark_as_paid_action",
        "download_invoice_pdf_action",
        "download_storno_pdf_action",
        "stornieren_action",
    ]

    # Bulk Actions
    actions = ["bulk_send_invoice_emails", "bulk_mark_as_sent", "bulk_mark_as_paid"]

    fieldsets = (
        ("Status", {"fields": ("status",)}),
        ("Rechnungsinformationen", {"fields": ("invoice_number", "customer")}),
        (
            "Position - Kurs ODER Angebot (10er-Karte)",
            {
                "fields": (("course", "offer"),),
                "description": "Wähle ENTWEDER einen Kurs ODER ein Angebot (10er-Karte, Workshop, etc.)",
            },
        ),
        (
            "Rechnungsdetails",
            {"fields": (("course_units", "course_duration"), "course_id_custom")},
        ),
        (
            "ZPP-Zertifizierung",
            {
                "fields": ("is_prevention_certified", "zpp_prevention_id"),
                "classes": ("collapse",),
            },
        ),
        (
            "Beträge",
            {
                "fields": (
                    "original_amount",
                    "discount_code",
                    "discount_amount",
                    "is_tax_exempt",
                    "tax_rate",
                    "tax_amount_display",
                    "total_amount_display_readonly",
                ),
            },
        ),
        ("Termine", {"fields": (("issue_date", "due_date"),)}),
        (
            "Email Versand",
            {"fields": ("email_sent", "email_sent_at"), "classes": ("collapse",)},
        ),
        ("Zusätzliche Informationen", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Metadaten",
            {
                "fields": (
                    ("created_at", "cancelled_at"),
                    ("updated_at", "cancelled_invoice_number"),
                ),
                "classes": ("collapse",),
            },
        ),
    )

    # ========================================
    # DISPLAY METHODS - ORIGINAL (INLINE LOGIC)
    # ========================================

    @display(header=True, description="Rechnung")
    def display_as_two_line_heading(self, obj):
        if obj.status in ["paid"]:
            return DisplayHelpers.muted_text_two_line(
                obj.invoice_number, obj.customer.get_full_name()
            )
        return [
            f"{obj.invoice_number}",
            f"{obj.customer.get_full_name()}",
        ]

    @display(description="Rabatt")
    def discount_display(self, obj):
        """✅ Rabatt mit Farbe"""
        is_paid = obj.status == "paid"

        if obj.discount_amount and obj.discount_amount > 0:
            text = SimpleText.text(f"-{obj.discount_amount}€", "warning")
            return DisplayHelpers.conditional_muted(text, is_paid)
        return DisplayHelpers.muted_text("-")

    @display(description="Kurs")
    def item_display(self, obj):
        """✅ Zeigt Kurs oder Offer mit Icon - INLINE LOGIC"""
        is_paid = obj.status == "paid"

        if obj.course:
            return DisplayHelpers.conditional_muted(obj.course.title, is_paid)
        elif obj.offer:
            return DisplayHelpers.conditional_muted(obj.offer.title, is_paid)
        return DisplayHelpers.muted_text("-")

    @display(description="Betrag", ordering="amount")
    def amount_display(self, obj):
        """✅ Betrag mit Total (Brutto)"""
        is_paid = obj.status == "paid"
        return DisplayHelpers.conditional_muted(f"{obj.total_amount}€", is_paid)

    @display(description="Status", ordering="status")
    def status_display(self, obj):
        """✅ Status Badge"""
        is_paid = obj.status == "paid"
        status_colors = {
            "draft": Colors.TEXT_ORANGE,
            "overdue": Colors.TEXT_ERROR,
        }
        color = status_colors.get(obj.status, "info")
        text = obj.get_status_display()
        if is_paid:
            return DisplayHelpers.conditional_muted(text, is_paid)
        return SimpleText.text(text, color)

    @display(description="Fälligkeitsdatum", ordering="issue_date")
    def dates_display(self, obj):
        """✅ Rechnungsdatum und Fälligkeitsdatum"""
        is_paid = obj.status == "paid"
        due = obj.due_date.strftime("%d.%m.%y")
        return DisplayHelpers.conditional_muted(f"{due}", is_paid)

    @display(description="Email")
    def email_status_display(self, obj):
        """✅ Email Versand Status"""
        is_paid = obj.status == "paid"

        if obj.email_sent and obj.email_sent_at:
            text = StatusIndicator.email_status_simple(True, obj.email_sent_at)
        else:
            text = StatusIndicator.email_status_simple(False)

        return DisplayHelpers.conditional_muted(text, is_paid)

    @display(description="ZPP")
    def zpp_indicator(self, obj):
        """✅ ZPP Zertifizierung Indicator"""
        is_paid = obj.status == "paid"

        if obj.is_prevention_certified and obj.zpp_prevention_id:
            text = SimpleText.icon("✓")
        else:
            text = DisplayHelpers.muted_text("-")

        return DisplayHelpers.conditional_muted(text, is_paid)

    # ========================================
    # READONLY FIELD DISPLAYS
    # ========================================

    def total_amount_display_readonly(self, obj):
        """Gesamtbetrag (Brutto) Anzeige"""
        amount_str = f"{obj.total_amount:.2f}" if obj.total_amount else "0.00"
        return format_html(
            '<strong style="color: {};">{} €</strong>', Colors.TEXT_SUCCESS, amount_str
        )

    total_amount_display_readonly.short_description = "Gesamtbetrag (Brutto)"

    def tax_amount_display(self, obj):
        """MwSt-Betrag Anzeige"""
        amount_str = f"{obj.tax_amount:.2f}" if obj.tax_amount else "0.00"
        return format_html("{} €", amount_str)

    tax_amount_display.short_description = "MwSt-Betrag"

    # ========================================
    # CHANGEFORM ACTIONS
    # ========================================

    @action(
        description="Rechnung per Email versenden",
        url_path="send-invoice-email",
        permissions=["send_invoice_email"],
    )
    def send_invoice_email_action(self, request: HttpRequest, object_id: int):
        try:
            from company.models import CompanyInfo
            from invoices.email_services.invoice_emails import InvoiceEmailService

            invoice = Invoice.objects.get(pk=object_id)

            service = InvoiceEmailService(CompanyInfo.get_solo())
            result = service.send_invoice_email(invoice)

            if result.get("sent", 0) > 0 or result.get("success", False):
                from django.utils import timezone

                invoice.status = "sent"
                invoice.email_sent = True
                invoice.email_sent_at = timezone.now()
                invoice.save(update_fields=["status", "email_sent", "email_sent_at"])

                self.message_user(
                    request, f"✅ {result['sent']} Email(s) versendet", level="SUCCESS"
                )

            return redirect("admin:invoices_invoice_change", object_id)

        except Exception as e:
            self.message_user(request, f"❌ Fehler: {str(e)}", level="ERROR")
            return redirect("admin:invoices_invoice_change", object_id)

    def has_send_invoice_email_permission(
        self, request: HttpRequest, object_id: Union[str, int]
    ):
        return request.user.has_perm("invoices.change_invoice")

    @action(
        description="Als versendet markieren",
        url_path="mark-as-sent",
        permissions=["mark_as_sent"],
    )
    def mark_as_sent_action(self, request: HttpRequest, object_id: int):
        handler = InvoiceActionHandler()
        return handler.mark_as_sent(request, object_id, self)

    def has_mark_as_sent_permission(
        self, request: HttpRequest, object_id: Union[str, int]
    ):
        return request.user.has_perm("invoices.change_invoice")

    @action(
        description="Als bezahlt markieren",
        url_path="mark-as-paid",
        permissions=["mark_as_paid"],
    )
    def mark_as_paid_action(self, request: HttpRequest, object_id: int):
        handler = InvoiceActionHandler()
        return handler.mark_as_paid(request, object_id, self)

    def has_mark_as_paid_permission(
        self, request: HttpRequest, object_id: Union[str, int]
    ):
        return request.user.has_perm("invoices.change_invoice")

    @action(
        description="Rechnung stornieren",
        url_path="stornieren",
        permissions=["stornieren"],
    )
    def stornieren_action(self, request: HttpRequest, object_id: int):
        handler = InvoiceActionHandler()
        return handler.stornieren(request, object_id, self)

    def has_stornieren_permission(
        self, request: HttpRequest, object_id: Union[str, int]
    ):
        return InvoiceActionHandler.has_stornieren_permission(object_id, request)

    # ========================================
    # PDF DOWNLOAD ACTIONS
    # ========================================

    @action(
        description="Rechnung als PDF herunterladen",
        url_path="download-invoice-pdf",
        attrs={"onclick": 'return confirm("PDF herunterladen?");'},
        permissions=["download_invoice_pdf"],
    )
    def download_invoice_pdf_action(self, request: HttpRequest, object_id: int):
        pdf_handler = InvoicePDFDownloadHandler()
        return pdf_handler.download_invoice_pdf(request, object_id, self)

    def has_download_invoice_pdf_permission(
        self, request: HttpRequest, object_id: Union[str, int]
    ):
        return request.user.has_perm("invoices.view_invoice")

    @action(
        description="Storno als PDF herunterladen",
        url_path="download-storno-pdf",
        attrs={"onclick": 'return confirm("PDF herunterladen?");'},
        permissions=["download_storno_pdf"],
    )
    def download_storno_pdf_action(self, request: HttpRequest, object_id: int):
        pdf_handler = InvoicePDFDownloadHandler()
        return pdf_handler.download_storno_pdf(request, object_id, self)

    def has_download_storno_pdf_permission(
        self, request: HttpRequest, object_id: Union[str, int]
    ):
        return InvoicePDFDownloadHandler.has_download_storno_pdf_permission(
            object_id, request
        )

    # ========================================
    # BULK ACTIONS
    # ========================================

    @admin.action(description="Ausgewählte per Email versenden")
    def bulk_send_invoice_emails(self, request, queryset):
        """✅ Versendet mehrere Rechnungen per Email"""
        from company.models import CompanyInfo
        from invoices.email_services.invoice_emails import InvoiceEmailService

        service = InvoiceEmailService(CompanyInfo.get_solo())
        result = service.send_bulk_invoice_emails(queryset)

        self.message_user(
            request,
            f"✅ {result['sent']} Rechnung(en) wurden versendet.",
            level="SUCCESS",
        )

        if result["errors"] > 0 and result.get("failed"):
            # Handle verschiedene Error-Formate
            error_messages = []
            for item in result["failed"][:5]:
                if "recipient" in item:
                    error_messages.append(f"{item['recipient']}: {item['error']}")
                elif "invoice" in item:
                    error_messages.append(f"{item['invoice']}: {item['error']}")
                else:
                    error_messages.append(str(item))

            error_msg = "\n".join(error_messages)
            self.message_user(
                request, f"❌ {result['errors']} Fehler:\n{error_msg}", level="ERROR"
            )

        # ✅ Markiere alle versendeten als email_sent
        from django.utils import timezone

        queryset.update(email_sent=True, email_sent_at=timezone.now(), status="sent")

    @admin.action(description="Ausgewählte als versendet markieren")
    def bulk_mark_as_sent(self, request, queryset):
        """✅ Markiere Rechnungen als versendet"""
        count = queryset.update(status="sent")
        self.message_user(
            request, f"✅ {count} Rechnung(en) wurden als versendet markiert."
        )

    @admin.action(description="Ausgewählte als bezahlt markieren")
    def bulk_mark_as_paid(self, request, queryset):
        """✅ Markiere Rechnungen als bezahlt (speichert einzeln um Signals zu triggern)"""
        updated_count = 0
        for invoice in queryset:
            if invoice.status != "paid":
                invoice.status = "paid"
                invoice.save()  # ← Signal wird getriggert! Accounting Entry wird erstellt!
                updated_count += 1

        self.message_user(
            request,
            f"✅ {updated_count} Rechnung(en) wurden als bezahlt markiert.",
            level="SUCCESS",
        )

    # ========================================
    # QUERYSET OPTIMIZATION
    # ========================================

    def get_queryset(self, request):
        """✅ Optimierte Query mit select_related für Course UND Offer"""
        qs = super().get_queryset(request)
        return qs.select_related("customer", "course", "course__offer", "offer")
