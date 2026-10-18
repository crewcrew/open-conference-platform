"""Orders, attendees, tickets, coupons and refunds.

Order, attendee, ticket, payment and check-in records are separate entities
(PRD section 7) so group purchases, partial refunds and attendance stay auditable.
"""

import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models

ZERO = Decimal("0.00")
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def random_code(length):
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def _access_token():
    return secrets.token_urlsafe(24)


def _ticket_code():
    return secrets.token_urlsafe(18)


def _display_id():
    return f"TKT-{random_code(4)}-{random_code(4)}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        PARTIALLY_REFUNDED = "partially_refunded", "Part refunded"
        REFUNDED = "refunded", "Refunded"

    CONFIRMED_STATUSES = (Status.PAID, Status.PARTIALLY_REFUNDED, Status.REFUNDED, Status.CANCELLED)

    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="orders")
    number = models.CharField(max_length=20, unique=True)
    access_token = models.CharField(max_length=64, unique=True, default=_access_token)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    purchaser_first_name = models.CharField(max_length=100, blank=True)
    purchaser_last_name = models.CharField(max_length=100, blank=True)
    purchaser_email = models.EmailField(blank=True, db_index=True)
    purchaser_organisation = models.CharField(max_length=200, blank=True)
    purchaser_answers = models.JSONField(default=dict, blank=True)
    marketing_consent = models.BooleanField(default=False)
    details_complete = models.BooleanField(default=False)

    currency = models.CharField(max_length=3)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    fee_total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    tax_total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    refunded_total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    coupon = models.ForeignKey("Coupon", null=True, blank=True, on_delete=models.PROTECT, related_name="orders")

    payment_provider = models.CharField(max_length=20, blank=True)
    payment_ref = models.CharField(max_length=200, blank=True, db_index=True)
    payment_intent = models.CharField(max_length=200, blank=True)
    failure_reason = models.CharField(max_length=300, blank=True)

    hold_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    @property
    def purchaser_name(self):
        return f"{self.purchaser_first_name} {self.purchaser_last_name}".strip()

    @property
    def is_confirmed(self):
        return self.status in self.CONFIRMED_STATUSES

    @property
    def refundable_balance(self):
        return self.total - self.refunded_total


class Attendee(models.Model):
    """The person attending, distinct from the purchaser (ATT-02)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="attendees")
    ticket_type = models.ForeignKey("events.TicketType", on_delete=models.PROTECT, related_name="attendees")
    position = models.PositiveSmallIntegerField(default=0)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True, db_index=True)
    answers = models.JSONField(default=dict, blank=True)
    sessions = models.ManyToManyField("events.Session", blank=True, related_name="attendees")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    is_purchaser = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "position"]

    def __str__(self):
        return self.full_name or f"Attendee {self.position + 1}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def paid_price(self):
        return self.unit_price - self.discount


class Ticket(models.Model):
    """The access credential (TKT-06). `code` is the secret in the QR code;
    `display_id` is the short reference people read out."""

    class Status(models.TextChoices):
        VALID = "valid", "Valid"
        CANCELLED = "cancelled", "Cancelled"

    attendee = models.OneToOneField(Attendee, on_delete=models.CASCADE, related_name="ticket")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")
    event = models.ForeignKey("events.Event", on_delete=models.PROTECT, related_name="tickets")
    ticket_type = models.ForeignKey("events.TicketType", on_delete=models.PROTECT, related_name="tickets")
    code = models.CharField(max_length=64, unique=True, default=_ticket_code)
    display_id = models.CharField(max_length=20, unique=True, default=_display_id)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.VALID, db_index=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    checked_in_lane = models.CharField(max_length=60, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "attendee__position"]

    def __str__(self):
        return self.display_id

    @property
    def is_valid(self):
        return self.status == self.Status.VALID


class Coupon(models.Model):
    """CPN-01 to CPN-08. A percentage comes off each eligible ticket. A fixed
    amount comes off the order once, split across its eligible tickets.
    `used_count` includes orders still in checkout."""

    class Kind(models.TextChoices):
        PERCENT = "percent", "Percentage"
        FIXED = "fixed", "Fixed amount off the order"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="coupons")
    code = models.CharField(max_length=40)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PERCENT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    ticket_types = models.ManyToManyField("events.TicketType", related_name="coupons")
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True, help_text="Orders. Leave empty for no limit.")
    used_count = models.PositiveIntegerField(default=0, editable=False)
    is_active = models.BooleanField(default=True)
    disabled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["event", "code"], name="unique_coupon_code_per_event")]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def describe(self):
        if self.kind == self.Kind.PERCENT:
            return f"{self.amount.normalize():f}% off"
        return f"{self.event.currency} {self.amount:.2f} off"

    def state(self, now):
        if not self.is_active:
            return "disabled"
        if self.starts_at and now < self.starts_at:
            return "scheduled"
        if self.ends_at and now > self.ends_at:
            return "expired"
        if self.max_redemptions is not None and self.used_count >= self.max_redemptions:
            return "used_up"
        return "active"


class Redemption(models.Model):
    """Immutable record of a coupon used on a paid order (CPN-05)."""

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name="redemptions")
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="redemption")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class RefundRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Waiting"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refund_requests")
    tickets = models.ManyToManyField(Ticket, related_name="refund_requests")
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]


class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending at provider"
        SUCCEEDED = "succeeded", "Refunded"
        FAILED = "failed", "Failed"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="refunds")
    number = models.CharField(max_length=24, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    tickets = models.ManyToManyField(Ticket, blank=True, related_name="refunds")
    note = models.TextField(blank=True)
    request = models.ForeignKey(RefundRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="refunds")
    provider = models.CharField(max_length=20, blank=True)
    provider_ref = models.CharField(max_length=200, blank=True)
    error = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class PaymentWebhook(models.Model):
    """Provider callbacks, stored once per provider event id so retries are harmless."""

    provider = models.CharField(max_length=20)
    event_id = models.CharField(max_length=200)
    kind = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["provider", "event_id"], name="unique_provider_event")]
