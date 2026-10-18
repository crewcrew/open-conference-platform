"""Event setup: details, publishing, sessions, ticket types, questions and coupons
(EVT-01 to EVT-07, TKT-01, ATT-01, CPN-01 to CPN-08)."""

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from ocp.accounts import audit
from ocp.events.models import Event, Question, Session, TicketType
from ocp.ticketing.models import Coupon, Redemption

from ocp.organizer.context import page
from ocp.organizer.decorators import organizer_view
from .forms import EventForm, QuestionForm, SessionForm, TicketTypeForm
from ocp.ticketing.forms import CouponForm
from ocp.core.forms import unique_slug


def _event_redirect(request, name, **kwargs):
    return redirect(f"organizer:{name}", org_slug=request.org.slug, event_id=request.event.pk, **kwargs)


@organizer_view("manage_events")
def event_create(request):
    form = EventForm(request.POST or None, initial={"contact_email": request.org.contact_email})
    if request.method == "POST":
        tz_name = request.POST.get("timezone") or "UTC"
        try:
            with timezone.override(tz_name):
                valid = form.is_valid()
        except Exception:
            valid = form.is_valid()
        if valid:
            event = form.save(commit=False)
            event.organization = request.org
            event.save()
            audit.record(request.org, request.user, "event.created", f"Created {event.name}.", event=event, obj=event)
            messages.success(request, "Event created. Add sessions and ticket types, then publish when you're ready.")
            return redirect("organizer:dashboard", org_slug=request.org.slug, event_id=event.pk)
    return page(request, "organizer/event_form.html", {"form": form, "creating": True})


@organizer_view("manage_events")
def event_edit(request):
    event = request.event
    form = EventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        changes = audit.diff(event, form)
        form.save()
        if changes:
            audit.record(request.org, request.user, "event.updated", f"Updated {event.name} settings.", event=event, obj=event, changes=changes)
        messages.success(request, "Saved.")
        return _event_redirect(request, "event_edit")
    return page(request, "organizer/event_form.html", {"form": form, "creating": False})


@organizer_view("manage_events")
@require_POST
def event_status(request):
    """Publish, unpublish or cancel (EVT-01)."""
    event = request.event
    action = request.POST.get("action")
    if action == "publish":
        if not event.ticket_types.filter(is_active=True).exists():
            messages.error(request, "Add at least one ticket type before publishing.")
            return _event_redirect(request, "dashboard")
        event.status = Event.Status.PUBLISHED
        event.published_at = event.published_at or timezone.now()
        summary = f"Published {event.name}."
    elif action == "unpublish":
        event.status = Event.Status.DRAFT
        summary = f"Unpublished {event.name}."
    elif action == "cancel":
        event.status = Event.Status.CANCELLED
        summary = f"Cancelled {event.name}. Ticket sales stopped."
    else:
        return _event_redirect(request, "dashboard")
    event.save(update_fields=["status", "published_at", "updated_at"])
    audit.record(request.org, request.user, f"event.{action}", summary, event=event, obj=event)
    messages.success(request, summary)
    return _event_redirect(request, "dashboard")


@organizer_view("manage_events")
@require_POST
def event_duplicate(request):
    """Copy setup into a new draft. Orders and attendees stay with the original (EVT-06)."""
    source = request.event
    with transaction.atomic():
        copy = Event.objects.get(pk=source.pk)
        copy.pk = None
        copy._state.adding = True
        copy.name = f"{source.name} (copy)"
        copy.slug = unique_slug(Event, f"{source.slug}-copy")
        copy.status = Event.Status.DRAFT
        copy.published_at = None
        copy.save()
        session_map = {}
        for session in source.sessions.all():
            old_pk = session.pk
            session.pk = None
            session._state.adding = True
            session.event = copy
            session.reserved = 0
            session.save()
            session_map[old_pk] = session
        for ticket_type in source.ticket_types.all():
            sessions = [session_map[s.pk] for s in ticket_type.sessions.all() if s.pk in session_map]
            ticket_type.pk = None
            ticket_type._state.adding = True
            ticket_type.event = copy
            ticket_type.reserved = 0
            ticket_type.save()
            ticket_type.sessions.set(sessions)
        for question in source.questions.all():
            question.pk = None
            question._state.adding = True
            question.event = copy
            question.save()
        audit.record(request.org, request.user, "event.duplicated", f"Copied {source.name} into a new draft.", event=copy, obj=copy)
    messages.success(request, "Copied. This draft has the same setup and no orders or attendees.")
    return redirect("organizer:event_edit", org_slug=request.org.slug, event_id=copy.pk)


# Sessions ----------------------------------------------------------------------------


@organizer_view("manage_events")
def sessions(request):
    event = request.event
    editing = None
    if request.GET.get("edit"):
        editing = get_object_or_404(Session, pk=request.GET["edit"], event=event)
    show_form = editing is not None or "new" in request.GET or request.method == "POST"
    if request.method == "POST":
        if request.POST.get("id"):
            editing = get_object_or_404(Session, pk=request.POST["id"], event=event)
        if request.POST.get("action") == "delete" and editing:
            if editing.attendees.exists():
                messages.error(request, "People have chosen this session, so it can't be deleted.")
            else:
                audit.record(request.org, request.user, "session.deleted", f"Deleted session {editing.title}.", event=event)
                editing.delete()
                messages.success(request, "Session deleted.")
            return _event_redirect(request, "sessions")
    form = SessionForm(request.POST or None, instance=editing) if show_form else None
    if request.method == "POST" and form.is_valid():
        changes = audit.diff(editing, form) if editing else {}
        session = form.save(commit=False)
        session.event = event
        session.save()
        audit.record(
            request.org, request.user, "session.saved",
            f"{'Updated' if editing else 'Added'} session {session.title}.", event=event, obj=session, changes=changes,
        )
        messages.success(request, "Session saved.")
        return _event_redirect(request, "sessions")
    days = {}
    for session in event.sessions.order_by("starts_at"):
        days.setdefault(event.local(session.starts_at).date(), []).append(session)
    return page(request, "organizer/sessions.html", {"days": days.items(), "form": form, "editing": editing})


# Ticket types ------------------------------------------------------------------------


@organizer_view("manage_events")
def tickets(request):
    event = request.event
    editing = None
    if request.GET.get("edit"):
        editing = get_object_or_404(TicketType, pk=request.GET["edit"], event=event)
    if request.method == "POST" and request.POST.get("id"):
        editing = get_object_or_404(TicketType, pk=request.POST["id"], event=event)
    show_form = editing is not None or "new" in request.GET or request.method == "POST"
    form = TicketTypeForm(request.POST or None, instance=editing, event=event) if show_form else None
    if request.method == "POST" and form.is_valid():
        changes = audit.diff(editing, form) if editing else {}
        ticket_type = form.save(commit=False)
        ticket_type.event = event
        ticket_type.save()
        form.save_m2m()
        audit.record(
            request.org, request.user, "ticket_type.saved",
            f"{'Updated' if editing else 'Added'} ticket type {ticket_type.name}.", event=event, obj=ticket_type, changes=changes,
        )
        messages.success(request, f"{ticket_type.name} saved.")
        return _event_redirect(request, "tickets")
    history = []
    if editing:
        history = event.audit_logs.filter(object_type="TicketType", object_id=str(editing.pk))[:5]
    ticket_types = event.ticket_types.all()
    totals = {
        "capacity": sum(t.quantity for t in ticket_types),
        "reserved": sum(t.reserved for t in ticket_types),
    }
    return page(
        request,
        "organizer/tickets.html",
        {"ticket_types": ticket_types, "form": form, "editing": editing, "history": history, "totals": totals},
    )


# Registration questions -------------------------------------------------------------------


@organizer_view("manage_events")
def questions(request):
    event = request.event
    editing = None
    if request.GET.get("edit"):
        editing = get_object_or_404(Question, pk=request.GET["edit"], event=event)
    if request.method == "POST" and request.POST.get("id"):
        editing = get_object_or_404(Question, pk=request.POST["id"], event=event)
    if request.method == "POST" and request.POST.get("action") == "delete" and editing:
        audit.record(request.org, request.user, "question.deleted", f"Removed the question “{editing.label}”.", event=event)
        editing.delete()
        messages.success(request, "Question removed. Answers already given stay on attendee records.")
        return _event_redirect(request, "questions")
    show_form = editing is not None or "new" in request.GET or request.method == "POST"
    form = QuestionForm(request.POST or None, instance=editing) if show_form else None
    if request.method == "POST" and form.is_valid():
        question = form.save(commit=False)
        question.event = event
        question.save()
        audit.record(request.org, request.user, "question.saved", f"Saved the question “{question.label}”.", event=event, obj=question)
        messages.success(request, "Question saved.")
        return _event_redirect(request, "questions")
    return page(request, "organizer/questions.html", {"questions": event.questions.all(), "form": form, "editing": editing})


# Coupons ----------------------------------------------------------------------------------


@organizer_view("manage_events")
def coupons(request):
    event = request.event
    editing = None
    if request.GET.get("edit"):
        editing = get_object_or_404(Coupon, pk=request.GET["edit"], event=event)
    if request.method == "POST" and request.POST.get("id"):
        editing = get_object_or_404(Coupon, pk=request.POST["id"], event=event)

    if request.method == "POST" and request.POST.get("action") in ("disable", "enable") and editing:
        enable = request.POST["action"] == "enable"
        editing.is_active = enable
        editing.disabled_at = None if enable else timezone.now()
        editing.save(update_fields=["is_active", "disabled_at"])
        verb = "Turned on" if enable else "Disabled"
        audit.record(request.org, request.user, f"coupon.{request.POST['action']}", f"{verb} coupon {editing.code}.", event=event, obj=editing)
        messages.success(request, f"{verb} {editing.code}. Its history stays in your reports.")
        return redirect(f"{request.path}?edit={editing.pk}")

    show_form = editing is not None or "new" in request.GET or request.method == "POST"
    form = CouponForm(request.POST or None, instance=editing, event=event) if show_form else None
    if request.method == "POST" and form.is_valid():
        changes = audit.diff(editing, form) if editing else {}
        coupon = form.save(commit=False)
        coupon.event = event
        coupon.save()
        form.save_m2m()
        audit.record(
            request.org, request.user, "coupon.saved", f"{'Updated' if editing else 'Created'} coupon {coupon.code}.",
            event=event, obj=coupon, changes=changes,
        )
        messages.success(request, f"{coupon.code} saved.")
        return redirect(f"{request.path}?edit={coupon.pk}")

    now = timezone.now()
    all_coupons = [(c, c.state(now)) for c in event.coupons.prefetch_related("ticket_types")]
    redemptions = Redemption.objects.filter(coupon=editing).select_related("order") if editing else []
    summary = {
        "orders": Redemption.objects.filter(coupon__event=event).count(),
        "discount": sum((r.discount_amount for r in Redemption.objects.filter(coupon__event=event)), 0),
        "active": sum(1 for _, state in all_coupons if state == "active"),
        "total": len(all_coupons),
    }
    return page(
        request,
        "organizer/coupons.html",
        {"coupons": all_coupons, "form": form, "editing": editing, "redemptions": redemptions, "summary": summary},
    )
