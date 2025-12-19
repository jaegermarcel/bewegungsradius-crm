# ==================== FEHLENDE GENERATOR-KLASSEN ====================
# Diese müssen in courses/admin_services.py hinzugefügt werden

import csv
import io
import logging
from datetime import datetime

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

logger = logging.getLogger(__name__)


class AttendanceListPDFGenerator:
    """Generiert PDF-Anwesenheitslisten für Kurse"""

    def generate(self, queryset):
        """
        Generiert PDF für mehrere Kurse

        Args:
            queryset: QuerySet von Course-Objekten

        Returns:
            HttpResponse mit PDF
        """
        # Erstelle PDF-Buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            topMargin=1 * cm,
            bottomMargin=1 * cm,
            leftMargin=1 * cm,
            rightMargin=1 * cm,
            title="Anwesenheitsliste",
        )

        # Sammle alle Stories (Tabellen für jeden Kurs)
        stories = []

        for course in queryset:
            # Kurs-Info
            info_text = self._build_course_info_text(course)
            stories.append(Paragraph(info_text, getSampleStyleSheet()["Heading2"]))
            stories.append(Spacer(1, 0.3 * cm))

            # Teilnehmer-Daten
            participants = self._get_participants_data(course)
            table_data = self._build_table_data(course, participants)
            col_widths = self._calculate_col_widths(course, participants)

            # Erstelle Tabelle
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            stories.append(table)
            stories.append(PageBreak())

        # Baue PDF
        doc.build(stories)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="anwesenheitsliste_{datetime.now().strftime("%Y%m%d")}.pdf"'
        )

        return response

    def _build_course_info_text(self, course):
        """Erstellt Info-Text für einen Kurs"""
        start = course.start_date.strftime("%d.%m.%Y") if course.start_date else "-"
        end = course.end_date.strftime("%d.%m.%Y") if course.end_date else "-"

        return f"""
        <b>Kurs:</b> {course.title}<br/>
        <b>Zeitraum:</b> {start} bis {end}<br/>
        <b>Standort:</b> {course.location.name if course.location else 'Online'}
        """

    def _get_participants_data(self, course):
        """Sammelt Teilnehmer-Daten"""
        participants = []

        # In-Person Teilnehmer
        for idx, participant in enumerate(course.participants_inperson.all(), 1):
            participants.append(
                {
                    "number": idx,
                    "name": participant.get_full_name(),
                    "email": participant.email,
                    "type": "Präsenz",
                }
            )

        # Online Teilnehmer
        for idx, participant in enumerate(course.participants_online.all(), 1):
            participants.append(
                {
                    "number": len(course.participants_inperson.all()) + idx,
                    "name": participant.get_full_name(),
                    "email": participant.email,
                    "type": "Online",
                }
            )

        return participants

    def _build_table_data(self, course, participants):
        """Erstellt Tabellen-Daten"""
        data = [["Nr.", "Name", "Email", "Typ", "Unterschrift"]]

        for p in participants:
            data.append(
                [
                    str(p["number"]),
                    p["name"],
                    p["email"],
                    p["type"],
                    "",  # Unterschrift-Spalte
                ]
            )

        return data

    def _calculate_col_widths(self, course, participants):
        """Berechnet Spaltenbreiten"""
        return [1 * cm, 5 * cm, 5 * cm, 2 * cm, 4 * cm]


class AttendanceListCSVGenerator:
    """Generiert CSV-Anwesenheitslisten für Kurse"""

    def generate(self, queryset):
        """
        Generiert CSV für mehrere Kurse

        Args:
            queryset: QuerySet von Course-Objekten

        Returns:
            HttpResponse mit CSV
        """
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        for course in queryset:
            # Kurs-Header
            writer.writerow([])
            writer.writerow([f"Kurs: {course.title}"])
            writer.writerow([f"Zeitraum: {course.start_date} bis {course.end_date}"])
            writer.writerow([])

            # Spalten-Header
            writer.writerow(["Nr.", "Name", "Email", "Typ"])

            # Teilnehmer
            participants = self._get_participants_data(course)
            for p in participants:
                writer.writerow([p["number"], p["name"], p["email"], p["type"]])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="anwesenheitsliste_{datetime.now().strftime("%Y%m%d")}.csv"'
        )

        return response

    def _get_participants_data(self, course):
        """Sammelt Teilnehmer-Daten"""
        participants = []

        # In-Person Teilnehmer
        for idx, participant in enumerate(course.participants_inperson.all(), 1):
            participants.append(
                {
                    "number": idx,
                    "name": participant.get_full_name(),
                    "email": participant.email,
                    "type": "Präsenz",
                }
            )

        # Online Teilnehmer
        for idx, participant in enumerate(course.participants_online.all(), 1):
            participants.append(
                {
                    "number": len(course.participants_inperson.all()) + idx,
                    "name": participant.get_full_name(),
                    "email": participant.email,
                    "type": "Online",
                }
            )

        return participants
