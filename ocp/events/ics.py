"""Calendar file for an event (API-05)."""

from datetime import timezone as dt_timezone

from django.utils import timezone


def _escape(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _stamp(value):
    return value.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def event_ics(event, url):
    location = ", ".join(part for part in [event.venue_name, event.venue_address.replace("\n", ", ")] if part)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Open Conference Platform//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:event-{event.pk}@open-conference-platform",
        f"DTSTAMP:{_stamp(timezone.now())}",
        f"DTSTART:{_stamp(event.starts_at)}",
        f"DTEND:{_stamp(event.ends_at)}",
        f"SUMMARY:{_escape(event.name)}",
        f"DESCRIPTION:{_escape((event.summary + chr(10) + url).strip())}",
        f"LOCATION:{_escape(location)}",
        f"URL:{url}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
