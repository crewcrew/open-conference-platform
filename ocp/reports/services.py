from django.db.models import Sum
from ocp.ticketing.models import ZERO, Order, Refund
from ocp.ticketing.pricing import tax_included_in


def money_summary(orders, event):
    """RPT-02: revenue, discounts, fees, refunds, tax and net for confirmed orders."""
    confirmed = orders.filter(status__in=Order.CONFIRMED_STATUSES)
    totals = confirmed.aggregate(
        revenue=Sum("subtotal"), discounts=Sum("discount_total"), fees=Sum("fee_total"), collected=Sum("total")
    )
    refunds = (
        Refund.objects.filter(order__in=confirmed).exclude(status=Refund.Status.FAILED).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    revenue = totals["revenue"] or ZERO
    discounts = totals["discounts"] or ZERO
    fees = totals["fees"] or ZERO
    collected = totals["collected"] or ZERO
    net = collected - refunds
    return {
        "revenue": revenue,
        "discounts": discounts,
        "fees": fees,
        "refunds": refunds,
        "collected": collected,
        "tax": tax_included_in(net, event),
        "net": net,
        "orders": confirmed.count(),
    }
