"""Attendee-facing pages: event page, checkout, payment, booking (journeys A to B)."""

from collections import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ocp.accounts.permissions import can, membership_for
from ocp.comms.models import Unsubscribe
from ocp.comms.services import read_unsubscribe_token, send_booking_links
from ocp.events.ics import event_ics
from ocp.events.models import Event, Question, TicketType
from ocp.ticketing import checkout
from ocp.ticketing.checkout import CheckoutError
from ocp.ticketing.models import Order, RefundRequest, Ticket
from ocp.ticketing.payments import PaymentError, ProviderEvent, get_provider, process_provider_event

from .forms import AttendeeForm, BookingLookupForm, PurchaserForm, RefundRequestForm, answers_from, initial_answers


def home(request):
    if request.user.is_authenticated:
        return redirect("organizer:home")
    return render(request, "public/home.html")


def _visible_event(request, slug):
    event = get_object_or_404(Event.objects.select_related("organization"), slug=slug)
    if event.is_published or event.is_cancelled:
        return event, False
    membership = membership_for(request.user, event.organization)
    if can(membership, "manage_events"):
        return event, True
    raise Http404


def _schedule(event):
    days = OrderedDict((day, []) for day in event.days())
    rows = OrderedDict()
    for session in event.sessions.order_by("starts_at", "room", "title"):
        start = event.local(session.starts_at)
        rows.setdefault((start.date(), start.replace(second=0, microsecond=0)), []).append(session)
    for (day, start), sessions in rows.items():
        days.setdefault(day, []).append({"start": start, "sessions": sessions})
    return [(day, slots) for day, slots in days.items() if slots]


def event_page(request, slug):
    event, is_preview = _visible_event(request, slug)
    access_code = (request.POST.get("access_code") or request.GET.get("code") or "").strip()

    ticket_types = []
    for ticket_type in event.ticket_types.filter(is_active=True):
        if ticket_type.visibility == TicketType.Visibility.HIDDEN:
            if not access_code or access_code.lower() != ticket_type.access_code.lower():
                continue
        state = ticket_type.sale_state()
        limit = min(ticket_type.max_per_order, ticket_type.available) if state == "on_sale" else 0
        ticket_types.append({"type": ticket_type, "state": state, "choices": range(0, limit + 1)})

    if request.method == "POST":
        if event.is_cancelled:
            raise Http404
        quantities = {}
        for item in ticket_types:
            try:
                quantities[item["type"].pk] = int(request.POST.get(f"qty_{item['type'].pk}", "0") or 0)
            except ValueError:
                quantities[item["type"].pk] = 0
        try:
            order = checkout.start_order(event, quantities, access_code=access_code)
        except CheckoutError as error:
            messages.error(request, str(error))
            return redirect(request.get_full_path())
        return redirect("public:checkout", token=order.access_token)

    has_hidden = event.ticket_types.filter(visibility=TicketType.Visibility.HIDDEN, is_active=True).exists()
    prices = [t.price for t in event.ticket_types.filter(is_active=True, visibility=TicketType.Visibility.PUBLIC)]
    return render(
        request,
        "public/event.html",
        {
            "event": event,
            "is_preview": is_preview,
            "ticket_types": ticket_types,
            "schedule": _schedule(event),
            "access_code": access_code,
            "has_hidden": has_hidden,
            "lowest_price": min(prices) if prices else None,
        },
    )


def calendar(request, slug):
    event, _ = _visible_event(request, slug)
    url = request.build_absolute_uri(reverse("public:event", args=[event.slug]))
    response = HttpResponse(event_ics(event, url), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{event.slug}.ics"'
    return response


# Checkout -------------------------------------------------------------------------


def _checkout_forms(order, data=None, initial_only=False):
    event = order.event
    purchaser_questions = list(event.questions.filter(applies_to=Question.AppliesTo.PURCHASER))
    attendee_questions = list(event.questions.filter(applies_to=Question.AppliesTo.ATTENDEE))
    attendees = list(order.attendees.select_related("ticket_type").order_by("position"))

    if initial_only and data is not None:
        # Re-show what the buyer typed (after applying a coupon) without flagging errors yet.
        flat = {key: data.get(key) for key in data}
        purchaser = PurchaserForm(initial=_strip_prefix(flat, "p"), prefix="p", questions=purchaser_questions)
        forms = [
            AttendeeForm(
                initial=_strip_prefix(flat, f"a{a.pk}"),
                prefix=f"a{a.pk}",
                attendee=a,
                questions=attendee_questions,
                allow_self=(i == 0),
            )
            for i, a in enumerate(attendees)
        ]
        return purchaser, list(zip(attendees, forms))

    if data is None:
        purchaser_initial = {
            "first_name": order.purchaser_first_name,
            "last_name": order.purchaser_last_name,
            "email": order.purchaser_email,
            "organisation": order.purchaser_organisation,
            "marketing_consent": order.marketing_consent,
            **initial_answers(order.purchaser_answers, purchaser_questions),
        }
        purchaser = PurchaserForm(initial=purchaser_initial, prefix="p", questions=purchaser_questions)
    else:
        purchaser = PurchaserForm(data, prefix="p", questions=purchaser_questions)

    forms = []
    for index, attendee in enumerate(attendees):
        kwargs = {"prefix": f"a{attendee.pk}", "attendee": attendee, "questions": attendee_questions, "allow_self": index == 0}
        if data is None:
            initial = {
                "is_purchaser": attendee.is_purchaser or (index == 0 and not order.details_complete),
                "first_name": attendee.first_name,
                "last_name": attendee.last_name,
                "email": attendee.email,
                **initial_answers(attendee.answers, attendee_questions),
            }
            form = AttendeeForm(initial=initial, **kwargs)
        else:
            form = AttendeeForm(data, **kwargs)
        forms.append((attendee, form))
    return purchaser, forms


def _strip_prefix(flat, prefix):
    start = f"{prefix}-"
    values = {}
    for key, value in flat.items():
        if key.startswith(start):
            name = key[len(start):]
            values[name] = True if value == "on" else value
    return values


def checkout_page(request, token):
    order = get_object_or_404(Order.objects.select_related("event", "coupon"), access_token=token)
    event = order.event
    if order.is_confirmed:
        return redirect("public:booking", token=order.access_token)
    if not checkout.hold_is_live(order):
        checkout.release_expired_holds(event)
        messages.error(request, "Your hold on those tickets ran out, so they've gone back on sale. Please choose again.")
        return redirect("public:event", slug=event.slug)

    coupon_message = None
    if request.method == "POST":
        action = request.POST.get("action", "pay")
        if action == "apply_coupon":
            try:
                coupon = checkout.apply_coupon(order, request.POST.get("coupon_code", ""))
                coupon_message = ("ok", f"{coupon.code} applied: {coupon.describe()} eligible tickets. One code per order.")
            except CheckoutError as error:
                coupon_message = ("error", str(error))
            order.refresh_from_db()
            purchaser, forms = _checkout_forms(order, request.POST, initial_only=True)
        elif action == "remove_coupon":
            checkout.remove_coupon(order)
            order.refresh_from_db()
            purchaser, forms = _checkout_forms(order, request.POST, initial_only=True)
        else:
            purchaser, forms = _checkout_forms(order, request.POST)
            if purchaser.is_valid() and all(form.is_valid() for _, form in forms):
                p = purchaser.cleaned_data
                purchaser_data = {
                    "purchaser_first_name": p["first_name"],
                    "purchaser_last_name": p["last_name"],
                    "purchaser_email": p["email"],
                    "purchaser_organisation": p["organisation"],
                    "marketing_consent": p["marketing_consent"],
                    "answers": answers_from(purchaser, purchaser.questions),
                }
                attendees_data = {}
                for attendee, form in forms:
                    d = form.cleaned_data
                    is_self = bool(d.get("is_purchaser"))
                    attendees_data[attendee.pk] = {
                        "first_name": p["first_name"] if is_self else d["first_name"],
                        "last_name": p["last_name"] if is_self else d["last_name"],
                        "email": p["email"] if is_self else d["email"],
                        "is_purchaser": is_self,
                        "answers": answers_from(form, form.questions),
                        "session_ids": form.session_ids(),
                    }
                try:
                    checkout.save_details(order, purchaser_data, attendees_data)
                    success = request.build_absolute_uri(reverse("public:booking", args=[order.access_token]))
                    cancel = request.build_absolute_uri(reverse("public:checkout", args=[order.access_token]))
                    return redirect(checkout.begin_payment(order, success_url=success, cancel_url=cancel))
                except (CheckoutError, PaymentError) as error:
                    messages.error(request, str(error))
                    order.refresh_from_db()
            else:
                messages.error(request, "Some details need fixing. They're marked below.")
    else:
        purchaser, forms = _checkout_forms(order)

    return render(
        request,
        "public/checkout.html",
        {
            "event": event,
            "order": order,
            "purchaser": purchaser,
            "attendee_forms": forms,
            "coupon_message": coupon_message,
            "has_coupons": event.coupons.filter(is_active=True).exists(),
            "count": len(forms),
            "lines": _order_lines(order),
        },
    )


def _order_lines(order):
    lines = OrderedDict()
    for attendee in order.attendees.select_related("ticket_type"):
        line = lines.setdefault(attendee.ticket_type_id, {"name": attendee.ticket_type.name, "count": 0, "amount": 0, "fee": 0})
        line["count"] += 1
        line["amount"] += attendee.unit_price
        line["fee"] += attendee.fee
    return list(lines.values())


@require_POST
def checkout_cancel(request, token):
    order = get_object_or_404(Order, access_token=token)
    checkout.cancel_checkout(order)
    messages.info(request, "We've released those tickets.")
    return redirect("public:event", slug=order.event.slug)


# Payment ---------------------------------------------------------------------------


def test_payment(request, ref):
    """The built-in test provider's payment page. Only exists when the test provider is on."""
    if settings.OCP_PAYMENT_PROVIDER != "test":
        raise Http404
    order = get_object_or_404(Order.objects.select_related("event"), payment_ref=ref, payment_provider="test")
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "pay":
            process_provider_event("test", ProviderEvent(event_id=f"{ref}:paid", kind="paid", payment_ref=ref, amount=order.total))
            return redirect("public:booking", token=order.access_token)
        if action == "decline":
            process_provider_event("test", ProviderEvent(event_id=f"{ref}:declined", kind="failed", payment_ref=ref))
            messages.error(request, "The payment was declined, so we released those tickets. You haven't been charged.")
            return redirect("public:event", slug=order.event.slug)
        return redirect("public:checkout", token=order.access_token)
    return render(request, "public/test_payment.html", {"order": order, "event": order.event})


@csrf_exempt
@require_POST
def payment_webhook(request, provider):
    try:
        handler = get_provider(provider)
    except Exception:
        raise Http404
    try:
        events = handler.parse_webhook(request)
    except PaymentError as error:
        return HttpResponseBadRequest(str(error))
    for event in events:
        process_provider_event(provider, event)
    return HttpResponse("ok")


# Booking ---------------------------------------------------------------------------


def booking(request, token):
    order = get_object_or_404(Order.objects.select_related("event"), access_token=token)
    event = order.event
    if order.status == Order.Status.PENDING and not order.payment_ref:
        return redirect("public:checkout", token=order.access_token)

    tickets = list(order.tickets.select_related("attendee", "ticket_type").order_by("attendee__position"))
    requestable = [t for t in tickets if t.is_valid and not t.checked_in_at and not t.refund_requests.filter(status=RefundRequest.Status.OPEN).exists()]
    form = RefundRequestForm(request.POST or None, tickets=requestable)
    if request.method == "POST" and order.is_confirmed and form.is_valid():
        chosen = [t for t in requestable if str(t.pk) in form.cleaned_data["tickets"]]
        refund_request = RefundRequest.objects.create(order=order, reason=form.cleaned_data["reason"])
        refund_request.tickets.set(chosen)
        messages.success(request, "We've sent your request to the organisers. They'll email you once it's handled.")
        return redirect("public:booking", token=order.access_token)

    return render(
        request,
        "public/booking.html",
        {
            "order": order,
            "event": event,
            "tickets": tickets,
            "waiting": order.status == Order.Status.PENDING,
            "refund_form": form if requestable and order.is_confirmed else None,
            "open_requests": order.refund_requests.filter(status=RefundRequest.Status.OPEN),
        },
    )


def ticket(request, code):
    ticket = get_object_or_404(Ticket.objects.select_related("attendee", "ticket_type", "order", "event"), code=code)
    return render(request, "public/ticket.html", {"ticket": ticket, "event": ticket.event, "order": ticket.order})


def booking_lookup(request):
    form = BookingLookupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        send_booking_links(form.cleaned_data["email"])
        messages.success(request, "If we have bookings for that email, a link to each one is on its way.")
        return redirect("public:booking_lookup")
    return render(request, "public/booking_lookup.html", {"form": form})


def unsubscribe(request, token):
    try:
        data = read_unsubscribe_token(token)
    except signing.BadSignature:
        raise Http404
    if request.method == "POST":
        Unsubscribe.objects.get_or_create(organization_id=data["o"], email=data["e"])
        return render(request, "public/unsubscribe.html", {"done": True, "email": data["e"]})
    return render(request, "public/unsubscribe.html", {"done": False, "email": data["e"]})
