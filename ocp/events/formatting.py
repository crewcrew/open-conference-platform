"""Date, time and money formatting used everywhere (RPT-04): dates and times in
the event's time zone, 24-hour times, and amounts with the currency code."""

from decimal import Decimal


def long_date(value):
    """Thu 18 Mar 2027"""
    return f"{value:%a} {value.day} {value:%b %Y}" if value else ""


def short_date(value):
    """18 Mar"""
    return f"{value.day} {value:%b}" if value else ""


def day_heading(value):
    """Thursday 18 March"""
    return f"{value:%A} {value.day} {value:%B}" if value else ""


def time_24(value):
    """09:00"""
    return f"{value:%H:%M}" if value else ""


def date_time(value):
    """Thu 18 Mar 2027, 09:00"""
    return f"{long_date(value)}, {time_24(value)}" if value else ""


def date_range(start, end):
    """Thu 18 – Fri 19 March 2027, or Thu 18 March 2027 for one day."""
    if start.date() == end.date():
        return f"{start:%a} {start.day} {start:%B %Y}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start:%a} {start.day} – {end:%a} {end.day} {end:%B %Y}"
    if start.year == end.year:
        return f"{start:%a} {start.day} {start:%B} – {end:%a} {end.day} {end:%B %Y}"
    return f"{long_date(start)} – {long_date(end)}"


def compact_range(start, end):
    """18–19 Mar 2027, or 30 Mar – 2 Apr 2027."""
    if start.date() == end.date():
        return f"{start.day} {start:%b %Y}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}–{end.day} {end:%b %Y}"
    return f"{start.day} {start:%b} – {end.day} {end:%b %Y}"


def amount(value):
    """1,234.50"""
    if value is None:
        return ""
    return f"{Decimal(value):,.2f}"


def money(value, currency):
    """NZD 1,234.50"""
    return f"{currency} {amount(value)}"
