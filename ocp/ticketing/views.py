"""Orders, refunds and attendee records (TKT-05, TKT-08, ATT-04 to ATT-06)."""

import csv

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from ocp.accounts import audit
from ocp.comms.models import Delivery
from ocp.comms.services import latest_delivery_by_attendee, retry_delivery, send_attendee_ticket, send_order_confirmation
from ocp.events.formatting import time_24
from ocp.ticketing import inventory
from ocp.ticketing.models import Attendee, Order, Refund, RefundRequest, Ticket
from ocp.ticketing.refunds import RefundError, cancel_and_refund, decline_request, send_refund_to_provider, suggest_refund

from ocp.organizer.context import page
from ocp.organizer.decorators import organizer_view
from .forms import AttendeeEditForm, RefundForm


def _csv_response(filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")
    return response, csv.writer(response)


def _local(event, value):
    return event.local(value).strftime("%Y-%m-%d %H:%M") if value else ""


# Orders ---------------------------------------------------------------------------------


def filtered_orders(event, params):
    orders = Order.objects.filter(event=event).exclude(status=Order.Status.PENDING, details_complete=False)
    q = (params.get("q") or "").strip()
    if q:
        orders = orders.filter(
            Q(number__icontains=q) | Q(purchaser_email__icontains=q) | Q(purchaser_first_name__icontains=q)
            | Q(purchaser_last_name__icontains=q) | Q(purchaser_organisation__icontains=q)
        )
    if params.get("status"):
        orders = orders.filter(status=params["status"])
    if params.get("ticket_type"):
        orders = orders.filter(attendees__ticket_type_id=params["ticket_type"]).distinct()
    if params.get("from"):
        orders = orders.filter(created_at__date__gte=params["from"])
    if params.get("to"):
        orders = orders.filter(created_at__date__lte=params["to"])
    return orders.annotate(ticket_count=Count("attendees", distinct=True)).order_by("-created_at")


@organizer_view("view_attendees")
def orders(request):
    event = request.event
    orders = filtered_orders(event, request.GET)
    if request.GET.get("export") == "csv":
        response, writer = _csv_response(f"{event.slug}-orders.csv")
        writer.writerow([
            "Order", "Status", f"Created ({event.tz_label})", f"Paid ({event.tz_label})", "Purchaser", "Email", "Organisation",
            "Tickets", "Currency", "Subtotal", "Discount", "Coupon", "Booking fees", "Tax included", "Total", "Refunded",
            "Payment provider", "Payment reference",
        ])
        for order in orders.select_related("coupon"):
            writer.writerow([
                order.number, order.get_status_display(), _local(event, order.created_at), _local(event, order.paid_at),
                order.purchaser_name, order.purchaser_email, order.purchaser_organisation, order.ticket_count,
                order.currency, order.subtotal, order.discount_total, order.coupon.code if order.coupon else "",
                order.fee_total, order.tax_total, order.total, order.refunded_total, order.payment_provider, order.payment_ref,
            ])
        return response
    page_obj = Paginator(orders, 50).get_page(request.GET.get("page"))
    requests = RefundRequest.objects.filter(order__event=event, status=RefundRequest.Status.OPEN).select_related("order")
    failed_refunds = Refund.objects.filter(order__event=event, status=Refund.Status.FAILED).select_related("order")
    return page(
        request,
        "organizer/orders.html",
        {
            "page_obj": page_obj,
            "statuses": Order.Status.choices,
            "params": request.GET,
            "open_requests": requests,
            "failed_refunds": failed_refunds,
        },
    )


@organizer_view("view_attendees")
def order_detail(request, order_id):
    event = request.event
    order = get_object_or_404(Order.objects.select_related("coupon"), pk=order_id, event=event)
    tickets = list(order.tickets.select_related("attendee", "ticket_type").order_by("attendee__position"))
    valid_tickets = [t for t in tickets if t.is_valid]
    open_request = order.refund_requests.filter(status=RefundRequest.Status.OPEN).prefetch_related("tickets").first()
    can_refund = "refund" in request.caps and order.is_confirmed and valid_tickets

    initial_tickets = [str(t.pk) for t in open_request.tickets.all() if t.is_valid] if open_request else []
    form = None
    confirm = None
    if can_refund:
        form = RefundForm(request.POST or None, tickets=valid_tickets, initial={"tickets": initial_tickets, "notify": True})
    action = request.POST.get("action") if request.method == "POST" else None

    if action in ("review", "confirm") and can_refund and form.is_valid():
        chosen = form.chosen_tickets()
        suggestion = suggest_refund(order, chosen, as_of=open_request.created_at if open_request else None)
        choice = form.cleaned_data["amount_choice"]
        amount = {
            "policy": suggestion["amount"],
            "full": min(suggestion["base"], order.refundable_balance),
            "custom": form.cleaned_data.get("custom_amount"),
            "none": 0,
        }[choice]
        if action == "review":
            confirm = {"tickets": chosen, "amount": amount}
        else:
            try:
                cancel_and_refund(
                    order, chosen, amount, request.user,
                    note=form.cleaned_data["note"], notify=form.cleaned_data["notify"], request=open_request,
                )
            except RefundError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Done. The tickets are cancelled" + (" and the refund is on its way." if amount else "."))
                return redirect("organizer:order_detail", org_slug=request.org.slug, event_id=event.pk, order_id=order.pk)
    elif action == "decline" and "refund" in request.caps and open_request:
        decline_request(open_request, request.user, note=request.POST.get("note", ""))
        messages.success(request, "Request declined. Let the purchaser know why.")
        return redirect("organizer:order_detail", org_slug=request.org.slug, event_id=event.pk, order_id=order.pk)
    elif action == "resend" and "edit_attendees" in request.caps and order.is_confirmed:
        send_order_confirmation(order)
        messages.success(request, "Confirmation and tickets sent again. No new tickets were issued.")
        return redirect("organizer:order_detail", org_slug=request.org.slug, event_id=event.pk, order_id=order.pk)
    elif action == "retry_refund" and "refund" in request.caps:
        refund = get_object_or_404(Refund, pk=request.POST.get("refund"), order=order, status=Refund.Status.FAILED)
        send_refund_to_provider(refund)
        messages.info(request, f"Refund {refund.number}: {refund.get_status_display()}.")
        return redirect("organizer:order_detail", org_slug=request.org.slug, event_id=event.pk, order_id=order.pk)

    suggestion = None
    if can_refund:
        basis = [t for t in valid_tickets if str(t.pk) in (form.data.getlist("tickets") if form.is_bound else initial_tickets)]
        suggestion = suggest_refund(order, basis or valid_tickets[:1], as_of=open_request.created_at if open_request else None)

    history = list(order.event.audit_logs.filter(object_type="Order", object_id=str(order.pk)))
    return page(
        request,
        "organizer/order_detail.html",
        {
            "order": order,
            "tickets": tickets,
            "form": form,
            "confirm": confirm,
            "open_request": open_request,
            "suggestion": suggestion,
            "refunds": order.refunds.prefetch_related("tickets"),
            "deliveries": order.deliveries.order_by("-created_at")[:10],
            "history": history,
        },
    )


# Attendees -----------------------------------------------------------------------------------


def filtered_attendees(event, params):
    attendees = Attendee.objects.filter(order__event=event, ticket__isnull=False).select_related("order", "ticket_type", "ticket")
    q = (params.get("q") or "").strip()
    if q:
        attendees = attendees.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
            | Q(order__number__icontains=q) | Q(ticket__display_id__icontains=q)
        )
    if params.get("ticket_type"):
        attendees = attendees.filter(ticket_type_id=params["ticket_type"])
    if params.get("session"):
        attendees = attendees.filter(sessions__id=params["session"])
    if params.get("status"):
        attendees = attendees.filter(order__status=params["status"])
    attendance = params.get("attendance")
    if attendance == "checked_in":
        attendees = attendees.filter(ticket__checked_in_at__isnull=False)
    elif attendance == "not_checked_in":
        attendees = attendees.filter(ticket__checked_in_at__isnull=True, ticket__status=Ticket.Status.VALID)
    elif attendance == "cancelled":
        attendees = attendees.filter(ticket__status=Ticket.Status.CANCELLED)
    return attendees.distinct().order_by("last_name", "first_name", "pk")


@organizer_view("view_attendees")
def attendees(request):
    event = request.event
    attendees = filtered_attendees(event, request.GET)
    if request.GET.get("export") == "csv":
        return _attendee_csv(event, attendees)
    page_obj = Paginator(attendees.prefetch_related("sessions"), 50).get_page(request.GET.get("page"))
    deliveries = latest_delivery_by_attendee(event)
    rows = [(a, deliveries.get(a.pk)) for a in page_obj]
    selected = None
    if request.GET.get("a"):
        selected = Attendee.objects.filter(pk=request.GET["a"], order__event=event).select_related("order", "ticket", "ticket_type").first()
    active_filters = [key for key in ("q", "ticket_type", "session", "status", "attendance") if request.GET.get(key)]
    return page(
        request,
        "organizer/attendees.html",
        {
            "page_obj": page_obj,
            "rows": rows,
            "params": request.GET,
            "selected": selected,
            "selected_history": event.audit_logs.filter(object_type="Attendee", object_id=str(selected.pk)) if selected else [],
            "selected_failed": Delivery.objects.filter(
                Q(attendee=selected) | Q(attendee__isnull=True, order=selected.order, to_email__iexact=selected.email),
                status=Delivery.Status.FAILED,
            ) if selected else [],
            "ticket_types": event.ticket_types.all(),
            "sessions": event.sessions.all(),
            "statuses": Order.Status.choices,
            "active_filters": active_filters,
            "total": Attendee.objects.filter(order__event=event, ticket__isnull=False).count(),
            "checked_in": Ticket.objects.filter(event=event, checked_in_at__isnull=False).count(),
            "failed_emails": Delivery.objects.filter(event=event, status=Delivery.Status.FAILED).count(),
            "query_string": request.GET.urlencode(),
        },
    )


def _attendee_csv(event, attendees):
    response, writer = _csv_response(f"{event.slug}-attendees.csv")
    questions = list(event.questions.filter(applies_to="attendee"))
    writer.writerow(
        ["Ticket ID", "First name", "Last name", "Email", "Ticket type", "Sessions chosen", "Ticket status",
         f"Checked in ({event.tz_label})", "Check-in lane", "Order", "Order status", "Purchaser", "Purchaser email"]
        + [q.label for q in questions]
    )
    for attendee in attendees.prefetch_related("sessions"):
        ticket = attendee.ticket
        writer.writerow(
            [ticket.display_id, attendee.first_name, attendee.last_name, attendee.email, attendee.ticket_type.name,
             "; ".join(s.title for s in attendee.sessions.all()), ticket.get_status_display(),
             _local(event, ticket.checked_in_at), ticket.checked_in_lane, attendee.order.number,
             attendee.order.get_status_display(), attendee.order.purchaser_name, attendee.order.purchaser_email]
            + [attendee.answers.get(q.label, "") for q in questions]
        )
    return response


@organizer_view("view_attendees")
def attendee_edit(request, attendee_id):
    """ATT-04: edit with an audit trail."""
    event = request.event
    attendee = get_object_or_404(Attendee.objects.select_related("order", "ticket", "ticket_type"), pk=attendee_id, order__event=event)
    groups = attendee.ticket_type.choice_groups()
    chosen = {s.choice_group: s.pk for s in attendee.sessions.all()}
    questions = list(event.questions.filter(applies_to="attendee"))
    form = AttendeeEditForm(
        request.POST or None,
        initial={"first_name": attendee.first_name, "last_name": attendee.last_name, "email": attendee.email},
    )
    if request.method == "POST" and "edit_attendees" not in request.caps:
        return redirect("organizer:attendees", org_slug=request.org.slug, event_id=event.pk)

    if request.method == "POST" and form.is_valid():
        changes = {}
        for field in ("first_name", "last_name", "email"):
            old, new = getattr(attendee, field), form.cleaned_data[field]
            if old != new:
                changes[field] = [old, new]
                setattr(attendee, field, new)
        answers = dict(attendee.answers)
        for question in questions:
            value = request.POST.get(question.field_name, "")
            if question.kind == "checkbox":
                value = bool(value)
            if answers.get(question.label) != value:
                changes[question.label] = [str(answers.get(question.label, "")), str(value)]
                answers[question.label] = value
        attendee.answers = answers
        try:
            with transaction.atomic():
                new_sessions = set()
                for group, options in groups.items():
                    value = request.POST.get(f"group_{group}")
                    if value and int(value) in {s.pk for s in options}:
                        new_sessions.add(int(value))
                    elif chosen.get(group):
                        new_sessions.add(chosen[group])
                old_sessions = set(attendee.sessions.values_list("id", flat=True))
                if attendee.ticket.is_valid:
                    for session_id in new_sessions - old_sessions:
                        if not inventory.reserve_session(session_id):
                            raise RefundError("That session is full.")
                    for session_id in old_sessions - new_sessions:
                        inventory.release_session(session_id)
                if new_sessions != old_sessions:
                    changes["sessions"] = [
                        ", ".join(event.sessions.filter(pk__in=old_sessions).values_list("title", flat=True)),
                        ", ".join(event.sessions.filter(pk__in=new_sessions).values_list("title", flat=True)),
                    ]
                    attendee.sessions.set(new_sessions)
                attendee.save()
                if changes:
                    audit.record(
                        request.org, request.user, "attendee.updated",
                        f"Edited {attendee.full_name} ({', '.join(changes)}).", event=event, obj=attendee, changes=changes,
                    )
        except RefundError as error:
            messages.error(request, str(error))
        else:
            if "email" in changes and request.POST.get("resend"):
                send_attendee_ticket(attendee)
                messages.success(request, "Saved, and the ticket was sent to the new address.")
            else:
                messages.success(request, "Saved.")
            return redirect(f"/manage/{request.org.slug}/e/{event.pk}/attendees/?a={attendee.pk}")
    return page(
        request,
        "organizer/attendee_form.html",
        {
            "attendee": attendee,
            "form": form,
            "groups": [(g, opts, chosen.get(g)) for g, opts in groups.items()],
            "questions": [(q, attendee.answers.get(q.label, "")) for q in questions],
            "history": event.audit_logs.filter(object_type="Attendee", object_id=str(attendee.pk)),
        },
    )


@organizer_view("edit_attendees")
@require_POST
def attendee_resend(request, attendee_id):
    attendee = get_object_or_404(Attendee, pk=attendee_id, order__event=request.event, ticket__isnull=False)
    if not attendee.email:
        messages.error(request, "This attendee has no email address.")
    else:
        delivery = send_attendee_ticket(attendee)
        if delivery.status == Delivery.Status.SENT:
            messages.success(request, f"Ticket sent to {attendee.email}. No new ticket was issued.")
        else:
            messages.error(request, f"Couldn't send to {attendee.email}: {delivery.error}")
    return redirect(f"/manage/{request.org.slug}/e/{request.event.pk}/attendees/?a={attendee.pk}")


@organizer_view("edit_attendees")
@require_POST
def delivery_retry(request, delivery_id):
    """Acceptance 10: fix the address if needed and send the same email again."""
    delivery = get_object_or_404(Delivery, pk=delivery_id, event=request.event)
    new_email = (request.POST.get("email") or "").strip()
    if new_email and new_email != delivery.to_email:
        if delivery.attendee:
            old = delivery.attendee.email
            delivery.attendee.email = new_email
            delivery.attendee.save(update_fields=["email"])
            audit.record(
                request.org, request.user, "attendee.updated", f"Changed {delivery.attendee.full_name}'s email to resend a bounced email.",
                event=request.event, obj=delivery.attendee, changes={"email": [old, new_email]},
            )
        elif delivery.order and delivery.order.purchaser_email.lower() == delivery.to_email.lower():
            old = delivery.order.purchaser_email
            delivery.order.purchaser_email = new_email
            delivery.order.save(update_fields=["purchaser_email"])
            audit.record(
                request.org, request.user, "order.updated", f"Changed the purchaser email on {delivery.order.number}.",
                event=request.event, obj=delivery.order, changes={"purchaser_email": [old, new_email]},
            )
    retry_delivery(delivery, new_email=new_email or None)
    if delivery.status == Delivery.Status.SENT:
        messages.success(request, f"Sent to {delivery.to_email}.")
    else:
        messages.error(request, f"Still failing: {delivery.error}")
    return redirect(request.POST.get("next") or f"/manage/{request.org.slug}/e/{request.event.pk}/emails/")


@organizer_view("check_in")
@require_POST
def manual_check_in(request, attendee_id):
    from ocp.checkin.models import CheckInEvent
    from ocp.checkin.services import check_in

    attendee = get_object_or_404(Attendee, pk=attendee_id, order__event=request.event, ticket__isnull=False)
    record = check_in(request.event, request.user, ticket=attendee.ticket, lane="Desk", method=CheckInEvent.Method.SEARCH)
    if record.result == CheckInEvent.Result.ADMITTED:
        messages.success(request, f"{attendee.full_name} checked in at {time_24(request.event.local(record.scanned_at))}.")
    else:
        messages.error(request, f"{record.get_result_display()}. {record.reason}")
    return redirect(f"/manage/{request.org.slug}/e/{request.event.pk}/attendees/?a={attendee.pk}")


def now_local(event):
    return event.local(timezone.now())
