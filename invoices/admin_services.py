import logging
import os
import tempfile
from urllib.parse import quote

from django.http import FileResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy

from .models import Invoice

logger = logging.getLogger(__name__)


class InvoiceActionHandler:
    """Service für Invoice Admin Actions"""

    @staticmethod
    def mark_as_sent(request, object_id, admin_instance):
        """Markiert Rechnung als versendet"""
        try:
            invoice = Invoice.objects.get(pk=object_id)
            invoice.status = "sent"
            invoice.save()

            admin_instance.message_user(
                request,
                f"Rechnung {invoice.invoice_number} wurde als versendet markiert.",
                level="success",
            )

            logger.info(f"Invoice {invoice.invoice_number} marked as sent")
        except Invoice.DoesNotExist:
            admin_instance.message_user(
                request, "Rechnung nicht gefunden.", level="error"
            )
        except Exception as e:
            admin_instance.message_user(
                request, f"Fehler beim Aktualisieren: {str(e)}", level="error"
            )
            logger.error(f"Error marking invoice {object_id} as sent: {e}")

        return redirect(
            reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
        )

    @staticmethod
    def mark_as_paid(request, object_id, admin_instance):
        """Markiert Rechnung als bezahlt"""
        try:
            invoice = Invoice.objects.get(pk=object_id)
            invoice.status = "paid"
            invoice.save()

            admin_instance.message_user(
                request,
                f"Rechnung {invoice.invoice_number} wurde als bezahlt markiert.",
                level="success",
            )

            logger.info(f"Invoice {invoice.invoice_number} marked as paid")
        except Invoice.DoesNotExist:
            admin_instance.message_user(
                request, "Rechnung nicht gefunden.", level="error"
            )
        except Exception as e:
            admin_instance.message_user(
                request, f"Fehler beim Aktualisieren: {str(e)}", level="error"
            )
            logger.error(f"Error marking invoice {object_id} as paid: {e}")

        return redirect(
            reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
        )

    @staticmethod
    def stornieren(request, object_id, admin_instance):
        """Storniert die Rechnung"""
        try:
            invoice = Invoice.objects.get(pk=object_id)

            if invoice.status == "cancelled":
                admin_instance.message_user(
                    request, "Diese Rechnung ist bereits storniert.", level="warning"
                )
                return redirect(
                    reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
                )

            invoice.status = "cancelled"
            invoice.save()

            admin_instance.message_user(
                request,
                f"Rechnung {invoice.invoice_number} wurde storniert.",
                level="success",
            )

            logger.info(f"Invoice {invoice.invoice_number} cancelled")
        except Invoice.DoesNotExist:
            admin_instance.message_user(
                request, "Rechnung nicht gefunden.", level="error"
            )
        except Exception as e:
            admin_instance.message_user(
                request, f"Fehler beim Stornieren: {str(e)}", level="error"
            )
            logger.error(f"Error cancelling invoice {object_id}: {e}")

        return redirect(
            reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
        )

    @staticmethod
    def has_stornieren_permission(object_id, request):
        """Prüft ob Stornierung erlaubt ist"""
        if not request.user.has_perm("invoices.change_invoice"):
            return False

        if not object_id:
            return False

        try:
            obj_id = int(object_id) if isinstance(object_id, str) else object_id
            invoice = Invoice.objects.get(pk=obj_id)
            return invoice.status != "cancelled"
        except (Invoice.DoesNotExist, ValueError, TypeError):
            return False


class InvoicePDFDownloadHandler:
    """Service für PDF-Downloads - mit temporärer Speicherung

    ✅ Nutzt neue InvoicePdfServiceFactory
    """

    @staticmethod
    def download_invoice_pdf(request, object_id, admin_instance):
        """✅ Generiert und lädt Invoice-PDF herunter"""
        temp_file = None
        try:
            # ✅ NEUE IMPORT - nutzt invoices/pdf_service.py!
            from invoices.pdf_service import InvoicePdfServiceFactory

            invoice = Invoice.objects.get(pk=object_id)
            filename = f"Rechnung_{invoice.invoice_number}.pdf"

            # ✅ 1. GENERIERE PDF
            service = InvoicePdfServiceFactory.create()
            try:
                # ✅ CORRECT METHOD - generate_invoice() existiert!
                pdf_bytes = service.generate_invoice(invoice)
                logger.info(f"Invoice PDF generated")
            except Exception as gen_error:
                logger.error(f"PDF generation failed: {gen_error}", exc_info=True)
                admin_instance.message_user(
                    request,
                    f"❌ PDF-Generierung fehlgeschlagen: {str(gen_error)}",
                    level="error",
                )
                return redirect(
                    reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
                )

            # ✅ 2. VALIDIERE PDF
            if not pdf_bytes or len(pdf_bytes) == 0:
                logger.error("PDF bytes are empty!")
                admin_instance.message_user(
                    request,
                    "❌ PDF ist leer - Template oder Rendering Problem",
                    level="error",
                )
                return redirect(
                    reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
                )

            # ✅ 3. SPEICHERE TEMPORÄR
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file.write(pdf_bytes)
            temp_file.close()
            logger.info(f"Temporary file created: {temp_file.name}")

            # ✅ 4. DOWNLOAD
            response = FileResponse(
                open(temp_file.name, "rb"), content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{quote(filename)}"'
            )
            response["Content-Length"] = len(pdf_bytes)

            admin_instance.message_user(
                request, f"✓ PDF heruntergeladen.", level="success"
            )

            logger.info(f"Invoice PDF downloaded: {filename}")
            return response

        except Invoice.DoesNotExist:
            admin_instance.message_user(
                request, "Rechnung nicht gefunden.", level="error"
            )
            return redirect(
                reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            admin_instance.message_user(request, f"❌ Fehler: {str(e)}", level="error")
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return redirect(
                reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
            )

    @staticmethod
    def download_storno_pdf(request, object_id, admin_instance):
        """✅ Generiert und lädt Storno-PDF herunter"""
        temp_file = None
        try:
            # ✅ NEUE IMPORT - nutzt invoices/pdf_service.py!
            from invoices.pdf_service import InvoicePdfServiceFactory

            invoice = Invoice.objects.get(pk=object_id)

            # Prüfe ob Storno möglich ist
            if invoice.status != "cancelled":
                admin_instance.message_user(
                    request, "Diese Rechnung ist nicht storniert.", level="warning"
                )
                return redirect(
                    reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
                )

            filename = f"Storno_{invoice.invoice_number}.pdf"

            # ✅ 1. GENERIERE STORNO-PDF
            service = InvoicePdfServiceFactory.create()
            try:
                # ✅ CORRECT METHOD - generate_cancellation() existiert!
                pdf_bytes = service.generate_cancellation(invoice)
                logger.info(f"Cancellation PDF generated: {len(pdf_bytes)} bytes")
            except Exception as gen_error:
                logger.error(
                    f"Storno PDF generation failed: {gen_error}", exc_info=True
                )
                admin_instance.message_user(
                    request,
                    f"❌ Storno-PDF-Generierung fehlgeschlagen: {str(gen_error)}",
                    level="error",
                )
                return redirect(
                    reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
                )

            # ✅ 2. VALIDIERE PDF
            if not pdf_bytes or len(pdf_bytes) == 0:
                logger.error("Storno PDF bytes are empty!")
                admin_instance.message_user(
                    request,
                    "❌ Storno-PDF ist leer - Template oder Rendering Problem",
                    level="error",
                )
                return redirect(
                    reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
                )

            # ✅ 3. SPEICHERE TEMPORÄR
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file.write(pdf_bytes)
            temp_file.close()
            logger.info(f"Temporary file created: {temp_file.name}")

            # ✅ 4. DOWNLOAD
            response = FileResponse(
                open(temp_file.name, "rb"), content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{quote(filename)}"'
            )
            response["Content-Length"] = len(pdf_bytes)

            admin_instance.message_user(
                request, f"✓ Storno-PDF heruntergeladen.", level="success"
            )

            logger.info(
                f"Cancellation PDF downloaded: {filename} ({len(pdf_bytes)} bytes)"
            )
            return response

        except Invoice.DoesNotExist:
            admin_instance.message_user(
                request, "Rechnung nicht gefunden.", level="error"
            )
            return redirect(
                reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            admin_instance.message_user(request, f"❌ Fehler: {str(e)}", level="error")
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return redirect(
                reverse_lazy("admin:invoices_invoice_change", args=(object_id,))
            )

    @staticmethod
    def has_download_storno_pdf_permission(object_id, request):
        """Prüft ob Storno-PDF Download erlaubt ist"""
        if not request.user.has_perm("invoices.view_invoice"):
            return False

        if not object_id:
            return False

        try:
            obj_id = int(object_id) if isinstance(object_id, str) else object_id
            invoice = Invoice.objects.get(pk=obj_id)
            return invoice.status == "cancelled"
        except (Invoice.DoesNotExist, ValueError, TypeError):
            return False
