"""Payment providers (TKT-10, TKT-11).

Card details never touch this platform: buyers pay on the provider's own page
and the provider tells us the result. Deployments pick a provider with
OCP_PAYMENT_PROVIDER. Two ship with the project:

- `test`: a built-in page with Pay and Decline buttons, for development and demos.
- `stripe`: Stripe Checkout, using Stripe's HTTP API directly.
"""

import hashlib
import hmac
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils import timezone

from ocp.observability import log_event

from .models import Order, PaymentWebhook, Refund

ZERO_DECIMAL_CURRENCIES = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}


class PaymentError(Exception):
    pass


@dataclass
class CheckoutSession:
    url: str
    ref: str


@dataclass
class RefundResult:
    status: str  # "succeeded", "pending" or "failed"
    ref: str = ""
    error: str = ""


@dataclass
class ProviderEvent:
    event_id: str
    kind: str  # "paid", "failed", "expired", "refund_succeeded", "refund_failed" or "ignored"
    payment_ref: str = ""
    amount: Decimal | None = None
    payment_intent: str = ""
    refund_ref: str = ""
    payload: dict = field(default_factory=dict)


def to_minor_units(amount, currency):
    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        return int(Decimal(amount).quantize(Decimal("1")))
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


def from_minor_units(value, currency):
    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        return Decimal(value).quantize(Decimal("0.01"))
    return (Decimal(value) / 100).quantize(Decimal("0.01"))


class PaymentProvider:
    name = ""
    label = ""

    def create_checkout(self, order, success_url, cancel_url):
        raise NotImplementedError

    def parse_webhook(self, request):
        raise NotImplementedError

    def refund(self, order, amount, reference):
        raise NotImplementedError


class TestProvider(PaymentProvider):
    """No real money moves. The test page sends the result straight back."""

    name = "test"
    label = "Test payments"

    def create_checkout(self, order, success_url, cancel_url):
        ref = f"test_{secrets.token_urlsafe(12)}"
        return CheckoutSession(url=reverse("public:test_payment", args=[ref]), ref=ref)

    def parse_webhook(self, request):
        return []

    def refund(self, order, amount, reference):
        return RefundResult(status="succeeded", ref=f"test_rf_{secrets.token_urlsafe(8)}")


class StripeProvider(PaymentProvider):
    """Stripe Checkout. Needs OCP_STRIPE_SECRET_KEY and OCP_STRIPE_WEBHOOK_SECRET.

    Point a Stripe webhook at /payments/webhook/stripe/ with the events
    checkout.session.completed, checkout.session.async_payment_succeeded,
    checkout.session.async_payment_failed, checkout.session.expired and refund.updated.
    """

    name = "stripe"
    label = "Stripe"
    api_base = "https://api.stripe.com/v1"

    def __init__(self, secret_key, webhook_secret):
        if not secret_key or not webhook_secret:
            raise ImproperlyConfigured("Stripe needs OCP_STRIPE_SECRET_KEY and OCP_STRIPE_WEBHOOK_SECRET.")
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret

    def _post(self, path, fields, idempotency_key):
        body = urllib.parse.urlencode(fields).encode()
        request = urllib.request.Request(
            f"{self.api_base}{path}",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.secret_key}",
                "Idempotency-Key": idempotency_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            try:
                message = json.loads(error.read()).get("error", {}).get("message", str(error))
            except ValueError:
                message = str(error)
            raise PaymentError(message) from error
        except urllib.error.URLError as error:
            raise PaymentError(f"Couldn't reach Stripe: {error.reason}") from error

    def create_checkout(self, order, success_url, cancel_url):
        event = order.event
        # Stripe sessions last at least 30 minutes; a payment that lands after
        # our hold expires is handled in checkout.confirm_paid.
        expires_at = int(time.time()) + 31 * 60
        fields = [
            ("mode", "payment"),
            ("success_url", success_url),
            ("cancel_url", cancel_url),
            ("client_reference_id", order.number),
            ("metadata[order_number]", order.number),
            ("expires_at", str(expires_at)),
            ("line_items[0][quantity]", "1"),
            ("line_items[0][price_data][currency]", order.currency.lower()),
            ("line_items[0][price_data][unit_amount]", str(to_minor_units(order.total, order.currency))),
            ("line_items[0][price_data][product_data][name]", f"{event.name}: order {order.number}"),
        ]
        if order.purchaser_email:
            fields.append(("customer_email", order.purchaser_email))
        data = self._post("/checkout/sessions", fields, idempotency_key=f"checkout-{order.number}-{order.total}")
        return CheckoutSession(url=data["url"], ref=data["id"])

    def parse_webhook(self, request):
        payload = request.body
        if not verify_stripe_signature(payload, request.headers.get("Stripe-Signature", ""), self.webhook_secret):
            raise PaymentError("Invalid Stripe signature.")
        data = json.loads(payload)
        obj = data.get("data", {}).get("object", {})
        kind = data.get("type", "")
        if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            if obj.get("payment_status") != "paid":
                return [ProviderEvent(event_id=data["id"], kind="ignored", payload=data)]
            return [
                ProviderEvent(
                    event_id=data["id"],
                    kind="paid",
                    payment_ref=obj["id"],
                    amount=from_minor_units(obj.get("amount_total", 0), obj.get("currency", "")),
                    payment_intent=obj.get("payment_intent") or "",
                    payload=data,
                )
            ]
        if kind == "checkout.session.async_payment_failed":
            return [ProviderEvent(event_id=data["id"], kind="failed", payment_ref=obj["id"], payload=data)]
        if kind == "checkout.session.expired":
            return [ProviderEvent(event_id=data["id"], kind="expired", payment_ref=obj["id"], payload=data)]
        if kind == "refund.updated":
            status = obj.get("status")
            if status in ("succeeded", "failed", "canceled"):
                outcome = "refund_succeeded" if status == "succeeded" else "refund_failed"
                return [ProviderEvent(event_id=data["id"], kind=outcome, refund_ref=obj["id"], payload=data)]
        return [ProviderEvent(event_id=data.get("id", ""), kind="ignored", payload=data)]

    def refund(self, order, amount, reference):
        if not order.payment_intent:
            return RefundResult(status="failed", error="This order has no Stripe payment to refund.")
        fields = [
            ("payment_intent", order.payment_intent),
            ("amount", str(to_minor_units(amount, order.currency))),
            ("metadata[order_number]", order.number),
            ("metadata[refund]", reference),
        ]
        try:
            data = self._post("/refunds", fields, idempotency_key=f"refund-{reference}")
        except PaymentError as error:
            return RefundResult(status="failed", error=str(error))
        status = {"succeeded": "succeeded", "failed": "failed", "canceled": "failed"}.get(data.get("status"), "pending")
        return RefundResult(status=status, ref=data.get("id", ""))


def verify_stripe_signature(payload, header, secret, tolerance=300, now=None):
    try:
        parts = dict(item.split("=", 1) for item in header.split(",") if "=" in item)
        timestamp = int(parts["t"])
    except (KeyError, ValueError):
        return False
    now = now if now is not None else time.time()
    if abs(now - timestamp) > tolerance:
        return False
    signed = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    signatures = [value for key, value in (item.split("=", 1) for item in header.split(",") if "=" in item) if key == "v1"]
    return any(hmac.compare_digest(expected, signature) for signature in signatures)


def get_provider(name=None):
    name = name or settings.OCP_PAYMENT_PROVIDER
    if name == "test":
        return TestProvider()
    if name == "stripe":
        return StripeProvider(settings.OCP_STRIPE_SECRET_KEY, settings.OCP_STRIPE_WEBHOOK_SECRET)
    raise ImproperlyConfigured(f"Unknown payment provider: {name}")


def process_provider_event(provider_name, event):
    """Apply one provider callback. Each provider event id is applied once."""
    from .checkout import confirm_paid, mark_failed

    stored, created = PaymentWebhook.objects.get_or_create(
        provider=provider_name, event_id=event.event_id, defaults={"kind": event.kind, "payload": event.payload}
    )
    if not created and stored.processed_at:
        return
    try:
        if event.kind == "paid":
            order = Order.objects.get(payment_ref=event.payment_ref)
            confirm_paid(order.pk, provider=provider_name, payment_ref=event.payment_ref, amount=event.amount, payment_intent=event.payment_intent)
        elif event.kind in ("failed", "expired"):
            order = Order.objects.filter(payment_ref=event.payment_ref).first()
            if order:
                mark_failed(order, "Payment didn't go through." if event.kind == "failed" else "Payment page expired.")
        elif event.kind in ("refund_succeeded", "refund_failed"):
            refund = Refund.objects.filter(provider_ref=event.refund_ref).first()
            if refund:
                refund.status = Refund.Status.SUCCEEDED if event.kind == "refund_succeeded" else Refund.Status.FAILED
                refund.completed_at = timezone.now()
                refund.save(update_fields=["status", "completed_at"])
        stored.processed_at = timezone.now()
        stored.save(update_fields=["processed_at"])
    except Exception as error:  # recorded for organizers and retried by the provider
        stored.error = str(error)
        stored.save(update_fields=["error"])
        log_event("payment.webhook_error", provider=provider_name, event_id=event.event_id, error=error)
        raise
