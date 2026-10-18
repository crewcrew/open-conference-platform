import secrets

from django.conf import settings
from django.db import models


class Organization(models.Model):
    """A team that runs one or more events (ORG-01, ORG-02)."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    contact_email = models.EmailField()
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Administrator"
    EVENT_MANAGER = "event_manager", "Event manager"
    VOLUNTEER = "volunteer", "Check-in volunteer"


class Membership(models.Model):
    """A person's role in an organization (ORG-03, ORG-04).

    Check-in volunteers only reach the events listed in `events` (CHK-05).
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices)
    events = models.ManyToManyField("events.Event", blank=True, related_name="volunteer_memberships")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "organization"], name="one_membership_per_org")]
        ordering = ["organization__name"]

    def __str__(self):
        return f"{self.user} · {self.organization} · {self.get_role_display()}"


def _invite_token():
    return secrets.token_urlsafe(24)


class Invitation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=Role.choices)
    events = models.ManyToManyField("events.Event", blank=True)
    token = models.CharField(max_length=64, unique=True, default=_invite_token)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class AuditLog(models.Model):
    """Append-only record of consequential changes (ORG-06, ATT-04)."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="audit_logs")
    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=60)
    object_type = models.CharField(max_length=60, blank=True)
    object_id = models.CharField(max_length=40, blank=True)
    summary = models.TextField()
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.summary
