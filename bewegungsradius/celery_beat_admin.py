"""
CELERY BEAT ADMIN - UNFOLD STYLE
=================================
Moderne Darstellung für Periodic Tasks
"""

from django.contrib import admin
from django.utils.html import format_html
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from unfold.admin import ModelAdmin
from unfold.decorators import display

# ✅ Deregistriere die Standard-Admins von django_celery_beat
try:
    admin.site.unregister(PeriodicTask)
    admin.site.unregister(IntervalSchedule)
    admin.site.unregister(CrontabSchedule)
    admin.site.unregister(SolarSchedule)
    admin.site.unregister(ClockedSchedule)
except admin.sites.NotRegistered:
    pass


# ========================================
# PERIODIC TASKS ADMIN
# ========================================


@admin.register(PeriodicTask)
class PeriodicTaskAdmin(ModelAdmin):

    list_display = [
        "task_name",
        "task_type",
        "schedule_info",
        "status",
        "last_run",
        "total_runs",
    ]

    list_display_links = ["task_name"]

    list_filter = [
        "enabled",
        "one_off",
        "task",
        "last_run_at",
    ]

    search_fields = [
        "name",
        "task",
        "description",
    ]

    readonly_fields = ["last_run_at", "total_run_count", "date_changed"]

    list_per_page = 50

    fieldsets = (
        ("Aufgaben-Details", {"fields": ("name", "task", "description", "enabled")}),
        (
            "Zeitplan",
            {
                "fields": (
                    "interval",
                    "crontab",
                    "solar",
                    "clocked",
                    "one_off",
                    "start_time",
                    "expires",
                )
            },
        ),
        ("Argumente", {"fields": ("args", "kwargs"), "classes": ("collapse",)}),
        (
            "Statistiken",
            {
                "fields": ("last_run_at", "total_run_count", "date_changed"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Aufgabe", ordering="name")
    def task_name(self, obj):
        if obj.description:
            return format_html(
                "<strong>{}</strong><br>" '<small style="color: #6b7280;">{}</small>',
                obj.name,
                (
                    obj.description[:50] + "..."
                    if len(obj.description) > 50
                    else obj.description
                ),
            )
        return format_html("<strong>{}</strong>", obj.name)

    @display(description="Typ", ordering="task")
    def task_type(self, obj):
        task = obj.task.split(".")[-1] if obj.task else "Unbekannt"

        return format_html(
            '<span style="display: inline-block; padding: 3px 10px; background: #dbeafe; '
            'color: #1e40af; border-radius: 6px; font-size: 0.875rem; font-weight: 500;">{}</span>',
            task,
        )

    @display(description="Zeitplan")
    def schedule_info(self, obj):
        if obj.interval:
            every = obj.interval.every
            period = obj.interval.period
            return format_html(
                '<span style="color: #10b981;">Alle {} {}</span>', every, period
            )
        elif obj.crontab:
            return format_html(
                '<span style="color: #8b5cf6;">{}</span>', str(obj.crontab)
            )
        elif obj.solar:
            return format_html(
                '<span style="color: #f59e0b;">{}</span>', str(obj.solar)
            )
        elif obj.clocked:
            return format_html(
                '<span style="color: #ec4899;">{}</span>',
                obj.clocked.clocked_time.strftime("%d.%m.%Y %H:%M"),
            )
        return "-"

    @display(description="Status", ordering="enabled")
    def status(self, obj):
        if obj.enabled:
            if obj.one_off:
                return format_html(
                    '<span style="display: inline-block; padding: 3px 10px; background: #fef3c7; '
                    'color: #92400e; border-radius: 6px; font-size: 0.875rem; font-weight: 500;">Einmalig</span>'
                )
            else:
                return format_html(
                    '<span style="display: inline-block; padding: 3px 10px; background: #dcfce7; '
                    'color: #166534; border-radius: 6px; font-size: 0.875rem; font-weight: 500;">Aktiv</span>'
                )
        else:
            return format_html(
                '<span style="display: inline-block; padding: 3px 10px; background: #f3f4f6; '
                'color: #4b5563; border-radius: 6px; font-size: 0.875rem; font-weight: 500;">Inaktiv</span>'
            )

    @display(description="Letzte Ausführung", ordering="last_run_at")
    def last_run(self, obj):
        if obj.last_run_at:
            return obj.last_run_at.strftime("%d.%m.%Y %H:%M:%S")
        return format_html('<span style="color: #9ca3af;">Noch nie</span>')

    @display(description="Läufe", ordering="total_run_count")
    def total_runs(self, obj):
        count = obj.total_run_count or 0
        return format_html("<strong>{}</strong>", count)


# ========================================
# INTERVAL SCHEDULE ADMIN
# ========================================


@admin.register(IntervalSchedule)
class IntervalScheduleAdmin(ModelAdmin):

    list_display = ["interval_display", "usage_count"]

    list_display_links = ["interval_display"]

    search_fields = ["every"]

    list_filter = ["period"]

    list_per_page = 50

    fieldsets = (("Intervall", {"fields": ("every", "period")}),)

    @display(description="Intervall", ordering="every")
    def interval_display(self, obj):
        return format_html("<strong>Alle {} {}</strong>", obj.every, obj.period)

    @display(description="Verwendung")
    def usage_count(self, obj):
        count = obj.periodictask_set.count()

        if count == 0:
            return format_html('<span style="color: #9ca3af;">Nicht verwendet</span>')

        return format_html(
            '<strong>{}</strong> <small style="color: #6b7280;">Task(s)</small>', count
        )


# ========================================
# CRONTAB SCHEDULE ADMIN
# ========================================


@admin.register(CrontabSchedule)
class CrontabScheduleAdmin(ModelAdmin):

    list_display = ["crontab_display", "timezone_display", "usage_count"]

    list_display_links = ["crontab_display"]

    search_fields = ["minute", "hour", "day_of_week", "day_of_month", "month_of_year"]

    list_per_page = 50

    fieldsets = (
        (
            "Zeitplan",
            {
                "fields": (
                    "minute",
                    "hour",
                    "day_of_week",
                    "day_of_month",
                    "month_of_year",
                    "timezone",
                )
            },
        ),
    )

    @display(description="Crontab", ordering="hour")
    def crontab_display(self, obj):
        return format_html(
            '<code style="background: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-size: 0.875rem;">{}</code>',
            str(obj),
        )

    @display(description="Zeitzone")
    def timezone_display(self, obj):
        return obj.timezone or "UTC"

    @display(description="Verwendung")
    def usage_count(self, obj):
        count = obj.periodictask_set.count()

        if count == 0:
            return format_html('<span style="color: #9ca3af;">Nicht verwendet</span>')

        return format_html(
            '<strong>{}</strong> <small style="color: #6b7280;">Task(s)</small>', count
        )


# ========================================
# CLOCKED SCHEDULE ADMIN (KORRIGIERT)
# ========================================


@admin.register(ClockedSchedule)
class ClockedScheduleAdmin(ModelAdmin):

    list_display = ["clocked_time", "schedule_status", "task_usage"]

    list_display_links = ["clocked_time"]

    list_per_page = 50

    fieldsets = (("Zeitpunkt", {"fields": ("clocked_time",)}),)

    @display(description="Status")
    def schedule_status(self, obj):
        from datetime import datetime

        from django.utils import timezone as tz

        now = datetime.now(tz.utc)
        is_past = obj.clocked_time < now

        if is_past:
            return format_html(
                '<span style="display: inline-block; padding: 3px 10px; background: #fef3c7; '
                'color: #92400e; border-radius: 6px; font-size: 0.875rem; font-weight: 500;">Abgelaufen</span>'
            )
        else:
            return format_html(
                '<span style="display: inline-block; padding: 3px 10px; background: #dcfce7; '
                'color: #166534; border-radius: 6px; font-size: 0.875rem; font-weight: 500;">Geplant</span>'
            )

    @display(description="Verwendung")
    def task_usage(self, obj):
        count = obj.periodictask_set.count()

        if count == 0:
            return format_html('<span style="color: #9ca3af;">Nicht verwendet</span>')

        return format_html(
            '<strong>{}</strong> <small style="color: #6b7280;">Task(s)</small>', count
        )


# ========================================
# SOLAR SCHEDULE ADMIN
# ========================================


@admin.register(SolarSchedule)
class SolarScheduleAdmin(ModelAdmin):
    list_display = ["event", "latitude", "longitude"]
    list_filter = ["event"]
