from django.contrib import admin

from .models import Event, Question, Session, TicketType


class SessionInline(admin.TabularInline):
    model = Session
    extra = 0


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    extra = 0
    readonly_fields = ["reserved"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "starts_at", "status", "visibility"]
    list_filter = ["status", "organization"]
    inlines = [TicketTypeInline, SessionInline]


admin.site.register(Question)
