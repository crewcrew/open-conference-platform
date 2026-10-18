from decimal import Decimal
from django import forms
from .models import Coupon
from ocp.core.forms import DATETIME_WIDGET

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ["code", "kind", "amount", "ticket_types", "starts_at", "ends_at", "max_redemptions"]
        widgets = {
            "kind": forms.RadioSelect,
            "ticket_types": forms.CheckboxSelectMultiple,
            "starts_at": DATETIME_WIDGET,
            "ends_at": DATETIME_WIDGET,
        }
        labels = {
            "kind": "Discount",
            "amount": "Amount",
            "ticket_types": "Ticket types",
            "starts_at": "Starts",
            "ends_at": "Ends",
            "max_redemptions": "Use limit (orders)",
        }
        help_texts = {
            "code": "Letters and numbers. Not case sensitive.",
            "amount": "A percentage comes off each eligible ticket. A fixed amount comes off the order once.",
        }

    def __init__(self, *args, event, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields["ticket_types"].queryset = event.ticket_types.filter(price__gt=0)
        self.fields["kind"].choices = Coupon.Kind.choices

    def clean_code(self):
        code = "".join(self.cleaned_data["code"].split()).upper()
        if not code.replace("-", "").replace("_", "").isalnum():
            raise forms.ValidationError("Use letters, numbers, - or _ only.")
        if Coupon.objects.filter(event=self.event, code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This event already has a coupon with that code.")
        return code

    def clean(self):
        data = super().clean()
        amount = data.get("amount")
        if amount is not None:
            if amount <= 0:
                self.add_error("amount", "The discount must be more than zero.")
            elif data.get("kind") == Coupon.Kind.PERCENT and amount > Decimal("100"):
                self.add_error("amount", "A percentage can't be more than 100.")
        limit = data.get("max_redemptions")
        if limit is not None and self.instance.pk and limit < self.instance.used_count:
            self.add_error("max_redemptions", f"Already used {self.instance.used_count} times, so the limit can't go below that.")
        if data.get("starts_at") and data.get("ends_at") and data["ends_at"] <= data["starts_at"]:
            self.add_error("ends_at", "The end must be after the start.")
        return data

class RefundForm(forms.Form):
    AMOUNT_CHOICES = [
        ("policy", "As the refund policy says"),
        ("full", "Full ticket price"),
        ("custom", "Another amount"),
        ("none", "Cancel without a refund"),
    ]
    tickets = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, label="Tickets to cancel")
    amount_choice = forms.ChoiceField(choices=AMOUNT_CHOICES, widget=forms.RadioSelect, initial="policy", label="Refund amount")
    custom_amount = forms.DecimalField(required=False, min_value=0, decimal_places=2, label="Amount")
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Note (team only, kept in history)")
    notify = forms.BooleanField(required=False, initial=True, label="Email the purchaser and attendees to say it's done")

    def __init__(self, *args, tickets=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.ticket_objects = {str(t.pk): t for t in tickets}
        self.fields["tickets"].choices = [
            (str(t.pk), f"{t.attendee.full_name} · {t.ticket_type.name} · {t.attendee.paid_price:.2f}") for t in tickets
        ]

    def clean(self):
        data = super().clean()
        if data.get("amount_choice") == "custom" and data.get("custom_amount") is None:
            self.add_error("custom_amount", "Enter the amount to refund.")
        return data

    def chosen_tickets(self):
        return [self.ticket_objects[pk] for pk in self.cleaned_data["tickets"]]

class AttendeeEditForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
