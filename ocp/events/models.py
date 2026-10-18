from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import models
from django.utils import timezone


class Event(models.Model):
    """A conference (EVT-01 to EVT-07).

    Times are stored in UTC and always shown in the event's own time zone.
    """

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        UNLISTED = "unlisted", "Unlisted (only people with the link)"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="events")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True, help_text="Used in the public link: /e/<slug>/")
    summary = models.CharField(max_length=300, blank=True, help_text="One line shown under the event name.")
    description = models.TextField(blank=True)
    timezone = models.CharField(max_length=64, default="Pacific/Auckland")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    venue_name = models.CharField(max_length=200, blank=True)
    venue_address = models.TextField(blank=True)
    online_url = models.URLField(blank=True, help_text="For online events. Only shown to people with a ticket.")
    accessibility_info = models.TextField(blank=True)
    contact_email = models.EmailField()
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    currency = models.CharField(max_length=3, default="NZD")
    tax_name = models.CharField(max_length=20, default="GST")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"), help_text="Percent.")
    prices_include_tax = models.BooleanField(default=True)
    booking_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00"), help_text="Added to each paid ticket. Not refunded."
    )

    refund_policy = models.TextField(blank=True, help_text="Shown on the event page and at checkout.")
    full_refund_until = models.DateField(null=True, blank=True)
    partial_refund_until = models.DateField(null=True, blank=True)
    partial_refund_percent = models.PositiveSmallIntegerField(default=50)

    order_prefix = models.CharField(max_length=8, default="ORD", help_text="Start of every order number.")
    hold_minutes = models.PositiveSmallIntegerField(default=15, help_text="How long tickets are held during checkout.")
    retention_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Remove attendee personal data this many days after the event ends."
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return self.name

    @property
    def tz(self):
        return ZoneInfo(self.timezone)

    def local(self, value):
        return timezone.localtime(value, self.tz) if value else None

    @property
    def tz_label(self):
        """For example "NZDT (UTC+13)", using the offset at the event start."""
        local = self.local(self.starts_at)
        offset = local.utcoffset()
        hours, remainder = divmod(int(offset.total_seconds()), 3600)
        minutes = abs(remainder) // 60
        sign = "+" if hours >= 0 else "-"
        utc = f"UTC{sign}{abs(hours)}" + (f":{minutes:02d}" if minutes else "")
        return f"{local.tzname()} ({utc})"

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    def days(self):
        """Local dates the event runs on."""
        start = self.local(self.starts_at).date()
        end = self.local(self.ends_at).date()
        days, current = [], start
        while current <= end:
            days.append(current)
            current = current.fromordinal(current.toordinal() + 1)
        return days


class Session(models.Model):
    """A schedule item (EVT-05). Sessions in the same `choice_group` are
    alternatives: each attendee whose ticket includes them picks one."""

    class Kind(models.TextChoices):
        TALK = "talk", "Talk"
        KEYNOTE = "keynote", "Keynote"
        WORKSHOP = "workshop", "Workshop"
        PANEL = "panel", "Panel"
        BREAK = "break", "Break"
        OTHER = "other", "Other"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.TALK)
    description = models.TextField(blank=True)
    speakers = models.CharField(max_length=300, blank=True)
    room = models.CharField(max_length=100, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Leave empty for no limit.")
    reserved = models.PositiveIntegerField(default=0, editable=False)
    choice_group = models.CharField(
        max_length=100, blank=True, help_text='Sessions sharing a group name, e.g. "Friday workshop", are a pick-one choice.'
    )

    class Meta:
        ordering = ["starts_at", "room", "title"]

    def __str__(self):
        return self.title

    @property
    def places_left(self):
        if self.capacity is None:
            return None
        return max(self.capacity - self.reserved, 0)

    @property
    def is_full(self):
        return self.capacity is not None and self.reserved >= self.capacity


class TicketType(models.Model):
    """TKT-01. `reserved` counts tickets held in checkout plus tickets sold,
    and is only changed by conditional updates in ticketing.inventory."""

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public on the event page"
        HIDDEN = "hidden", "Hidden, unlocked with an access code"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_types")
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    quantity = models.PositiveIntegerField()
    reserved = models.PositiveIntegerField(default=0, editable=False)
    sale_starts = models.DateTimeField(null=True, blank=True)
    sale_ends = models.DateTimeField(null=True, blank=True)
    min_per_order = models.PositiveSmallIntegerField(default=1)
    max_per_order = models.PositiveSmallIntegerField(default=10)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    access_code = models.CharField(max_length=60, blank=True)
    sessions = models.ManyToManyField(Session, blank=True, related_name="ticket_types", help_text="Sessions this ticket gives access to.")
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "price", "name"]

    def __str__(self):
        return self.name

    @property
    def is_free(self):
        return self.price == 0

    @property
    def available(self):
        return max(self.quantity - self.reserved, 0)

    def sale_state(self, now=None):
        now = now or timezone.now()
        if not self.is_active:
            return "closed"
        if self.sale_starts and now < self.sale_starts:
            return "not_started"
        if self.sale_ends and now > self.sale_ends:
            return "ended"
        if self.available <= 0:
            return "sold_out"
        return "on_sale"

    def choice_groups(self):
        """{group name: [sessions]} for the pick-one groups this ticket includes."""
        groups = {}
        for session in self.sessions.exclude(choice_group="").order_by("starts_at", "title"):
            groups.setdefault(session.choice_group, []).append(session)
        return groups


class Question(models.Model):
    """Organizer-configured registration field (ATT-01)."""

    class Kind(models.TextChoices):
        TEXT = "text", "Short text"
        TEXTAREA = "textarea", "Long text"
        SELECT = "select", "Pick one from a list"
        CHECKBOX = "checkbox", "Tick box"

    class AppliesTo(models.TextChoices):
        ATTENDEE = "attendee", "Each attendee"
        PURCHASER = "purchaser", "The purchaser"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="questions")
    label = models.CharField(max_length=200)
    help_text = models.CharField(max_length=300, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.TEXT)
    options = models.TextField(blank=True, help_text="For a list: one option per line.")
    required = models.BooleanField(default=False)
    applies_to = models.CharField(max_length=10, choices=AppliesTo.choices, default=AppliesTo.ATTENDEE)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.label

    @property
    def option_list(self):
        return [line.strip() for line in self.options.splitlines() if line.strip()]

    @property
    def field_name(self):
        return f"q{self.pk}"
