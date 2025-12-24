"""
accounting/admin.py - Mit gefilterten Summary Cards (PRODUCTION)
"""

from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.components import BaseComponent, register_component
from unfold.decorators import display

from .models import AccountingEntry

# ==================== UNFOLD COMPONENT ====================


@register_component
class AccountingSummaryComponent(BaseComponent):
    """Component für Accounting Summary Cards"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Berechne Summen
        queryset = AccountingEntry.objects.all()

        total_income = (
            queryset.filter(entry_type="income").aggregate(Sum("amount"))["amount__sum"]
            or 0
        )
        total_expense = (
            queryset.filter(entry_type="expense").aggregate(Sum("amount"))[
                "amount__sum"
            ]
            or 0
        )
        net_profit = total_income - total_expense

        context.update(
            {
                "total_income": total_income,
                "total_expense": total_expense,
                "net_profit": net_profit,
            }
        )

        return context


# ==================== ADMIN ====================


@admin.register(AccountingEntry)
class AccountingEntryAdmin(SimpleHistoryAdmin, ImportExportModelAdmin, ModelAdmin):
    """Ein-/Ausgaben Management"""

    list_display = [
        "display_as_two_line_heading",
        "amount_display",
        "invoice_link",
    ]
    list_filter = ["entry_type", "date"]
    search_fields = ["description", "notes"]
    readonly_fields = ["created_at", "invoice_link_display"]

    fieldsets = (
        (
            "Eintrag",
            {
                "fields": (
                    ("entry_type", "date"),
                    "description",
                    "amount",
                )
            },
        ),
        ("Rechnung", {"fields": ("invoice_link_display",)}),
        ("Notizen", {"fields": ("notes",)}),
        ("Info", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    # 🔧 Custom Template mit Summary Cards
    change_list_template = "admin/accounting_entry/change_list.html"

    def changelist_view(self, request, extra_context=None):
        """
        ✅ FIXED: Berechne Summen basierend auf GEFILTERTEN Daten

        Die Summen in den Cards werden automatisch aktualisiert,
        wenn Filter angewendet werden!
        """
        response = super().changelist_view(request, extra_context)

        # Prüfe ob response ein TemplateResponse ist
        if not hasattr(response, "context_data"):
            return response

        # Starte mit ALL
        queryset = AccountingEntry.objects.all()

        # 🔧 FILTER 1: entry_type__exact (Entry Type: income/expense)
        entry_type_filter = request.GET.get("entry_type__exact")
        if entry_type_filter:
            queryset = queryset.filter(entry_type=entry_type_filter)

        # 🔧 FILTER 2: date (Nach Datum - Format: YYYY-MM)
        date_filter = request.GET.get("date")
        if date_filter:
            try:
                parts = date_filter.split("-")
                if len(parts) == 2:
                    year, month = int(parts[0]), int(parts[1])
                    queryset = queryset.filter(date__year=year, date__month=month)
            except (ValueError, IndexError):
                pass

        # Berechne Summen auf gefilterte queryset
        total_income = (
            queryset.filter(entry_type="income").aggregate(Sum("amount"))["amount__sum"]
            or 0
        )
        total_expense = (
            queryset.filter(entry_type="expense").aggregate(Sum("amount"))[
                "amount__sum"
            ]
            or 0
        )
        net_profit = total_income - total_expense

        # Übergebe an Template
        if response.context_data is not None:
            response.context_data["total_income"] = total_income
            response.context_data["total_expense"] = total_expense
            response.context_data["net_profit"] = net_profit

        return response

    @display(header=True, description="Eintrag")
    def display_as_two_line_heading(self, obj):
        formatted_date = obj.date.strftime("%d.%m.%Y")

        return [
            formatted_date,
            obj.description,
        ]

    @display(description="Betrag", label="amount")
    def amount_display(self, obj):
        """Betrag mit Farbe"""
        if obj.entry_type == "income":
            return format_html(
                f'<span style="color: #10b981; font-weight: 600;">+{obj.amount}€</span>'
            )
        return format_html(
            f'<span style="color: #ef4444; font-weight: 600;">-{obj.amount}€</span>'
        )

    def invoice_link(self, obj):
        """Link zur Rechnung in List"""
        if obj.invoice:
            url = f"/admin/invoices/invoice/{obj.invoice.id}/change/"
            return format_html(f'<a href="{url}">#{obj.invoice.invoice_number}</a>')
        return "-"

    invoice_link.short_description = "Rechnung"

    def invoice_link_display(self, obj):
        """Link in Detail-View"""
        if obj.invoice:
            url = f"/admin/invoices/invoice/{obj.invoice.id}/change/"
            return format_html(f'<a href="{url}" class="button">Rechnung anschauen</a>')
        return "Keine Rechnung"

    invoice_link_display.short_description = "Verlinkte Rechnung"
