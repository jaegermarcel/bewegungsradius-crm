from django.db import migrations


def transfer_company_info_forward(apps, schema_editor):
    """
    Migriert CompanyInfo von invoices zu company App
    """
    # Hole die alten und neuen Models
    OldCompanyInfo = apps.get_model("invoices", "CompanyInfo")
    NewCompanyInfo = apps.get_model("company", "CompanyInfo")

    # Lese alle Einträge aus der alten Tabelle
    old_entries = OldCompanyInfo.objects.all()

    print(f"\n📦 Migriere {old_entries.count()} CompanyInfo Einträge...")

    for old_entry in old_entries:
        # Erstelle neuen Eintrag mit denselben Daten
        new_entry = NewCompanyInfo(
            id=old_entry.id,
            name=old_entry.name,
            street=old_entry.street,
            house_number=old_entry.house_number,
            postal_code=old_entry.postal_code,
            city=old_entry.city,
            phone=old_entry.phone,
            email=old_entry.email,
            tax_number=old_entry.tax_number,
            bank_name=old_entry.bank_name,
            iban=old_entry.iban,
            bic=old_entry.bic,
            logo=old_entry.logo,
        )
        new_entry.save()
        print(f"  ✓ {new_entry.name}")

    print(f"✅ Migration abgeschlossen: {old_entries.count()} Einträge übertragen\n")


def transfer_company_info_backward(apps, schema_editor):
    """
    Rollback - löscht alle neuen Einträge
    """
    NewCompanyInfo = apps.get_model("company", "CompanyInfo")
    count = NewCompanyInfo.objects.count()
    NewCompanyInfo.objects.all().delete()
    print(f"\n⏮️  Rollback: {count} Einträge gelöscht\n")


class Migration(migrations.Migration):
    dependencies = [
        ("company", "0001_initial"),
        ("invoices", "0008_invoice_discount_amount_invoice_discount_code_and_more"),
    ]

    operations = [
        migrations.RunPython(
            transfer_company_info_forward, transfer_company_info_backward
        ),
    ]
