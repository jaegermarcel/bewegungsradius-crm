from django.db import models
from solo.models import SingletonModel


class CompanyInfo(SingletonModel):
    name = models.CharField(max_length=200, verbose_name="Name")
    street = models.CharField(max_length=200, verbose_name="Straße")
    house_number = models.CharField(max_length=10, verbose_name="Hausnummer")
    postal_code = models.CharField(max_length=10, verbose_name="PLZ")
    city = models.CharField(max_length=100, verbose_name="Stadt")

    phone = models.CharField(max_length=50, verbose_name="Telefon")
    email = models.EmailField(verbose_name="E-Mail")
    tax_number = models.CharField(max_length=50, verbose_name="Steuernummer")

    bank_name = models.CharField(max_length=200, verbose_name="Bankname")
    iban = models.CharField(max_length=34, verbose_name="IBAN")
    bic = models.CharField(max_length=11, verbose_name="BIC")

    logo = models.ImageField(
        upload_to="company/", blank=True, null=True, verbose_name="Logo"
    )

    class Meta:
        verbose_name = "Unternehmenseinstellungen"

    def __str__(self):
        return self.name
