from django.conf import settings
from django.db import models


class CheckInEvent(models.Model):
    """Append-only record of every scan or lookup (CHK-02, CHK-03).

    `client_scan_id` comes from the scanning device, so a scan synced twice
    after being offline is recorded once (CHK-07).
    """

    class Result(models.TextChoices):
        ADMITTED = "admitted", "Checked in"
        DUPLICATE = "duplicate", "Already checked in"
        INVALID = "invalid", "Not valid"

    class Method(models.TextChoices):
        SCAN = "scan", "QR scan"
        SEARCH = "search", "Name search"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="checkin_events")
    ticket = models.ForeignKey("ticketing.Ticket", null=True, blank=True, on_delete=models.SET_NULL, related_name="checkin_events")
    scanned_code = models.CharField(max_length=200, blank=True)
    result = models.CharField(max_length=10, choices=Result.choices)
    reason = models.CharField(max_length=200, blank=True)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.SCAN)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    lane = models.CharField(max_length=60, blank=True)
    device_id = models.CharField(max_length=80, blank=True)
    client_scan_id = models.CharField(max_length=80, null=True, blank=True, unique=True)
    was_offline = models.BooleanField(default=False)
    scanned_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scanned_at", "-id"]

    def __str__(self):
        return f"{self.get_result_display()} · {self.scanned_at:%H:%M:%S}"
