import segno
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from ocp.events import formatting

register = template.Library()


@register.filter
def local(value, event):
    """Convert a UTC datetime to the event's time zone."""
    return event.local(value) if value and event else value


@register.filter
def long_date(value):
    return formatting.long_date(value)


@register.filter
def short_date(value):
    return formatting.short_date(value)


@register.filter
def day_heading(value):
    return formatting.day_heading(value)


@register.filter
def time24(value):
    return formatting.time_24(value)


@register.filter
def date_time(value):
    return formatting.date_time(value)


@register.filter
def amount(value):
    return formatting.amount(value)


@register.filter
def money(value, currency):
    return formatting.money(value, currency)


@register.simple_tag
def event_dates(event):
    return formatting.date_range(event.local(event.starts_at), event.local(event.ends_at))


@register.simple_tag
def compact_dates(event):
    return formatting.compact_range(event.local(event.starts_at), event.local(event.ends_at))


@register.simple_tag
def qr_svg(data, label=""):
    """Inline SVG QR code. Error correction M survives scuffed phone screens."""
    qr = segno.make(data, error="m")
    svg = qr.svg_inline(scale=6, border=2, dark="#14161A", light="#FFFFFF", omitsize=True, svgclass="qr", lineclass=None)
    label = escape(label or "Ticket QR code")
    svg = svg.replace("<svg ", f'<svg role="img" aria-label="{label}" ', 1)
    return mark_safe(svg)


@register.filter
def get_item(mapping, key):
    return mapping.get(key) if mapping else None


@register.filter
def percent_of(part, whole):
    try:
        return round(100 * part / whole) if whole else 0
    except (TypeError, ZeroDivisionError):
        return 0
