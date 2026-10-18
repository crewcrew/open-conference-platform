"""Updates, reminders and delivery problems (COM-02 to COM-05, acceptance 10)."""

from datetime import timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from ocp.accounts import audit
from ocp.comms.models import Communication, Delivery
from ocp.comms.services import MERGE_FIELDS, build_message, deliver, recipients, send_communication
from ocp.events.formatting import date_time

from ocp.organizer.context import page
from ocp.organizer.decorators import organizer_view
from .forms import ComposeForm

REMINDER_PRESETS = {
    "week": (timedelta(days=7), "One week to go: {event}"),
    "day": (timedelta(days=1), "See you tomorrow at {event}"),
}


@organizer_view("send_comms")
def emails(request):
    event = request.event
    communications = event.communications.all()
    failed = Delivery.objects.filter(event=event, status=Delivery.Status.FAILED).select_related("attendee", "order")
    return page(request, "organizer/emails.html", {"communications": communications, "failed": failed})


@organizer_view("send_comms")
def compose(request):
    event = request.event
    initial = {}
    preset = REMINDER_PRESETS.get(request.GET.get("reminder", ""))
    if preset:
        offset, subject = preset
        initial = {
            "subject": subject.format(event=event.name),
            "body": "Hi {first name},\n\nA reminder that " + event.name + " starts soon. Bring your ticket QR code to the door.\n\nYour booking: {booking link}",
            "when": "schedule",
            "scheduled_for": event.local(event.starts_at - offset).replace(tzinfo=None),
        }
    form = ComposeForm(request.POST or None, event=event, initial=initial)
    preview = None
    count = None
    if form.is_bound and form.is_valid():
        draft = Communication(event=event, kind=form.cleaned_data["kind"], subject=form.cleaned_data["subject"],
                              body=form.cleaned_data["body"], audience=form.audience())
        people = recipients(draft)
        count = len(people)
        sample = people[0] if people else None
        if sample:
            subject, body = build_message(draft, *sample)
            preview = {"to": sample[0], "subject": subject, "body": body}
        action = request.POST.get("action")
        if action == "test":
            if sample:
                subject, body = build_message(draft, *sample)
            else:
                subject, body = draft.subject, draft.body
            deliver(Delivery.Kind.UPDATE, request.user.email, f"[Test] {subject}", body, event=event)
            messages.success(request, f"Test sent to {request.user.email}.")
        elif action == "send":
            if not people:
                messages.error(request, "Nobody matches this group, so there's no one to send to.")
            else:
                draft.created_by = request.user
                draft.is_reminder = bool(request.POST.get("is_reminder"))
                if form.cleaned_data["when"] == "schedule":
                    draft.status = Communication.Status.SCHEDULED
                    draft.scheduled_for = form.cleaned_data["scheduled_for"]
                    draft.recipient_count = count
                    draft.save()
                    audit.record(request.org, request.user, "comms.scheduled",
                                 f"Scheduled “{draft.subject}” for {date_time(event.local(draft.scheduled_for))}.", event=event, obj=draft)
                    messages.success(request, f"Scheduled for {date_time(event.local(draft.scheduled_for))}. It goes to whoever matches the group at that time.")
                else:
                    draft.save()
                    sent = send_communication(draft)
                    audit.record(request.org, request.user, "comms.sent", f"Sent “{draft.subject}” to {sent} people.", event=event, obj=draft)
                    messages.success(request, f"Sent to {sent} people.")
                return redirect("organizer:email_detail", org_slug=request.org.slug, event_id=event.pk, communication_id=draft.pk)
    else:
        draft = Communication(event=event, kind="update", subject="", body="", audience={})
        count = len(recipients(draft))
    opted_in = len(recipients(Communication(event=event, kind="marketing", subject="", body="", audience={})))
    return page(
        request,
        "organizer/compose.html",
        {"form": form, "preview": preview, "count": count, "merge_fields": MERGE_FIELDS, "opted_in": opted_in, "is_reminder": bool(preset)},
    )


@organizer_view("send_comms")
def email_detail(request, communication_id):
    event = request.event
    communication = get_object_or_404(Communication, pk=communication_id, event=event)
    if request.method == "POST" and request.POST.get("action") == "cancel" and communication.status == Communication.Status.SCHEDULED:
        communication.status = Communication.Status.CANCELLED
        communication.save(update_fields=["status"])
        audit.record(request.org, request.user, "comms.cancelled", f"Cancelled the scheduled email “{communication.subject}”.", event=event)
        messages.success(request, "Cancelled. Nothing was sent.")
        return redirect("organizer:emails", org_slug=request.org.slug, event_id=event.pk)
    deliveries = communication.deliveries.select_related("attendee")
    stats = {
        "sent": deliveries.filter(status=Delivery.Status.SENT).count(),
        "failed": deliveries.filter(status=Delivery.Status.FAILED).count(),
    }
    return page(request, "organizer/email_detail.html", {"communication": communication, "deliveries": deliveries[:200], "stats": stats})
