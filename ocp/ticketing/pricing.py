"""Order totals: ticket prices, coupon discount, booking fee and tax (TKT-09, CPN-04)."""

from decimal import ROUND_HALF_UP, Decimal

from .models import ZERO, Attendee, Coupon

CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def price_order(order):
    """Recalculate every attendee line and the order totals, then save them."""
    event = order.event
    attendees = list(order.attendees.select_related("ticket_type").order_by("position"))
    coupon = order.coupon

    for attendee in attendees:
        attendee.discount = ZERO

    if coupon is not None:
        eligible_ids = set(coupon.ticket_types.values_list("id", flat=True))
        eligible = [a for a in attendees if a.ticket_type_id in eligible_ids and a.unit_price > 0]
        if coupon.kind == Coupon.Kind.PERCENT:
            for attendee in eligible:
                attendee.discount = min(money(attendee.unit_price * coupon.amount / 100), attendee.unit_price)
        else:
            remaining = min(coupon.amount, sum((a.unit_price for a in eligible), ZERO))
            for attendee in eligible:
                share = min(remaining, attendee.unit_price)
                attendee.discount = money(share)
                remaining -= share

    for attendee in attendees:
        attendee.fee = money(event.booking_fee) if attendee.paid_price > 0 else ZERO

    Attendee.objects.bulk_update(attendees, ["discount", "fee"])

    subtotal = sum((a.unit_price for a in attendees), ZERO)
    discount = sum((a.discount for a in attendees), ZERO)
    fees = sum((a.fee for a in attendees), ZERO)
    total = subtotal - discount + fees
    rate = event.tax_rate
    if event.prices_include_tax:
        tax = money(total * rate / (100 + rate)) if rate else ZERO
    else:
        tax = money(total * rate / 100) if rate else ZERO
        total += tax

    order.subtotal = money(subtotal)
    order.discount_total = money(discount)
    order.fee_total = money(fees)
    order.tax_total = tax
    order.total = money(total)
    order.save(update_fields=["subtotal", "discount_total", "fee_total", "tax_total", "total", "updated_at"])
    return order


def tax_included_in(amount, event):
    """Tax inside an amount that already includes it (order totals always do)."""
    if not event.tax_rate:
        return ZERO
    return money(amount * event.tax_rate / (100 + event.tax_rate))
