from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0002_transfer_company_info"),
        ("invoices", "0008_invoice_discount_amount_invoice_discount_code_and_more"),
    ]

    operations = [
        # Removed: CompanyInfo aus invoices wird gelöscht
        # migrations.DeleteModel(name='CompanyInfo'),
        # Stattdessen nur deaktivieren für später
    ]
