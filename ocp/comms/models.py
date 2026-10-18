from django.conf import settings
from django.db import models


class Communication(models.Model):
    """An update or reminder written by organizers (COM-02, COM-03).

    Event updates go to everyone in the audience. Marketing messages only go
    to purchasers who opted in and have not unsubscribed (COM-05).
    """

    class Kind(models.TextChoices):
        UPDATE = "update", "Event update"
        MARKETING = "marketing", "News or promotion"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        SENT = "sent", "Sent"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="communications")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.UPDATE)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.JSONField(default=dict, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    recipient_count = models.PositiveIntegerField(default=0)
    is_reminder = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject


class Delivery(models.Model):
    """One email to one address, with its outcome (COM-01, acceptance 10)."""

    class Kind(models.TextChoices):
        CONFIRMATION = "confirmation", "Order confirmation"
        TICKET = "ticket", "Ticket"
        CANCELLATION = "cancellation", "Cancellation"
        REFUND = "refund", "Refund"
        UPDATE = "update", "Event update"
        MARKETING = "marketing", "News"
        BOOKING_LINK = "booking_link", "Booking link"
        INVITATION = "invitation", "Team invitation"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.CASCADE, related_name="deliveries")
    communication = models.ForeignKey(Communication, null=True, blank=True, on_delete=models.CASCADE, related_name="deliveries")
    order = models.ForeignKey("ticketing.Order", null=True, blank=True, on_delete=models.CASCADE, related_name="deliveries")
    attendee = models.ForeignKey("ticketing.Attendee", null=True, blank=True, on_delete=models.CASCADE, related_name="deliveries")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    to_email = models.EmailField()
    subject = models.CharField(max_length=250)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED, db_index=True)
    error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "deliveries"

    def __str__(self):
        return f"{self.get_kind_display()} to {self.to_email}"


class Unsubscribe(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="unsubscribes")
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "email"], name="unique_unsubscribe")]
