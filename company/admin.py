from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin

from company.models import CompanyInfo


@admin.register(CompanyInfo)
class CompanyInfoAdmin(SingletonModelAdmin, ModelAdmin):
    fieldsets = (
        ("Firmeninformationen", {"fields": (("name", "tax_number"), "logo")}),
        ("Adresse", {"fields": (("street", "house_number"), ("postal_code", "city"))}),
        ("Kontakt", {"fields": (("phone", "email"),)}),
        ("Bankverbindung", {"fields": (("bank_name", "iban", "bic"),)}),
    )
