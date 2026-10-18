import zoneinfo
from django import forms
from django.utils import timezone
from django.utils.text import slugify
from .models import Event, Question, Session, TicketType
from ocp.core.forms import DATETIME_WIDGET, DATE_WIDGET, unique_slug

def timezone_choices():
    zones = sorted(z for z in zoneinfo.available_timezones() if "/" in z and not z.startswith(("Etc/", "SystemV/")))
    return [(z, z.replace("_", " ")) for z in zones] + [("UTC", "UTC")]

class EventForm(forms.ModelForm):
    timezone = forms.ChoiceField(choices=timezone_choices, initial="Pacific/Auckland", label="Time zone")

    class Meta:
        model = Event
        fields = [
            "name", "slug", "summary", "description", "timezone", "starts_at", "ends_at",
            "venue_name", "venue_address", "online_url", "accessibility_info", "contact_email", "visibility",
            "currency", "tax_name", "tax_rate", "prices_include_tax", "booking_fee",
            "refund_policy", "full_refund_until", "partial_refund_until", "partial_refund_percent",
            "order_prefix", "hold_minutes", "retention_days",
        ]
        widgets = {
            "starts_at": DATETIME_WIDGET,
            "ends_at": DATETIME_WIDGET,
            "full_refund_until": DATE_WIDGET,
            "partial_refund_until": DATE_WIDGET,
            "description": forms.Textarea(attrs={"rows": 6}),
            "venue_address": forms.Textarea(attrs={"rows": 2}),
            "accessibility_info": forms.Textarea(attrs={"rows": 3}),
            "refund_policy": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "starts_at": "Starts",
            "ends_at": "Ends",
            "online_url": "Online link",
            "prices_include_tax": "Ticket prices include tax",
            "full_refund_until": "Full refund until",
            "partial_refund_until": "Part refund until",
            "partial_refund_percent": "Part refund (%)",
            "hold_minutes": "Checkout hold (minutes)",
            "retention_days": "Keep personal data for (days after the event)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["slug"].help_text = "The end of the public link. Leave empty to make one from the name."

    def clean_currency(self):
        return self.cleaned_data["currency"].upper()

    def clean_order_prefix(self):
        return slugify(self.cleaned_data["order_prefix"]).upper().replace("-", "")[:8] or "ORD"

    def clean(self):
        data = super().clean()
        tz_name = data.get("timezone")
        if tz_name:
            # Datetime inputs were read in the page's time zone; re-read them in the chosen one.
            current = timezone.get_current_timezone()
            event_tz = zoneinfo.ZoneInfo(tz_name)
            for field in ("starts_at", "ends_at"):
                if data.get(field):
                    data[field] = timezone.make_aware(timezone.make_naive(data[field], current), event_tz)
        if data.get("starts_at") and data.get("ends_at") and data["ends_at"] <= data["starts_at"]:
            self.add_error("ends_at", "The end must be after the start.")
        if not data.get("slug") and data.get("name"):
            data["slug"] = unique_slug(Event, data["name"])
        elif data.get("slug"):
            clash = Event.objects.filter(slug=data["slug"]).exclude(pk=self.instance.pk).exists()
            if clash:
                self.add_error("slug", "Another event already uses this link.")
        if not data.get("venue_name") and not data.get("online_url"):
            self.add_error("venue_name", "Add a venue or an online link.")
        return data

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ["title", "kind", "speakers", "room", "starts_at", "ends_at", "capacity", "choice_group", "description"]
        widgets = {"starts_at": DATETIME_WIDGET, "ends_at": DATETIME_WIDGET, "description": forms.Textarea(attrs={"rows": 3})}
        labels = {"choice_group": "Pick-one group", "starts_at": "Starts", "ends_at": "Ends"}
        help_texts = {"capacity": "Places are held when attendees choose this session at checkout."}

    def clean(self):
        data = super().clean()
        if data.get("starts_at") and data.get("ends_at") and data["ends_at"] <= data["starts_at"]:
            self.add_error("ends_at", "The end must be after the start.")
        capacity = data.get("capacity")
        if capacity is not None and self.instance.pk and capacity < self.instance.reserved:
            self.add_error("capacity", f"{self.instance.reserved} people have chosen this session, so capacity can't go below that.")
        return data

class TicketTypeForm(forms.ModelForm):
    class Meta:
        model = TicketType
        fields = [
            "name", "description", "price", "quantity", "sale_starts", "sale_ends",
            "min_per_order", "max_per_order", "sessions", "visibility", "access_code", "position", "is_active",
        ]
        widgets = {
            "sale_starts": DATETIME_WIDGET,
            "sale_ends": DATETIME_WIDGET,
            "sessions": forms.CheckboxSelectMultiple,
            "visibility": forms.RadioSelect,
        }
        labels = {
            "price": "Price",
            "sale_starts": "Sale starts",
            "sale_ends": "Sale ends",
            "min_per_order": "Min per order",
            "max_per_order": "Max per order",
            "sessions": "Gives access to",
            "position": "Order on the page",
            "is_active": "On sale (untick to hide and stop sales)",
        }

    def __init__(self, *args, event, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields["sessions"].queryset = event.sessions.order_by("starts_at")
        self.fields["sessions"].required = False
        self.fields["visibility"].choices = TicketType.Visibility.choices

    def clean(self):
        data = super().clean()
        quantity = data.get("quantity")
        if quantity is not None and self.instance.pk and quantity < self.instance.reserved:
            self.add_error("quantity", f"{self.instance.reserved} sold or held, so quantity can't go below that.")
        if data.get("min_per_order") and data.get("max_per_order") and data["min_per_order"] > data["max_per_order"]:
            self.add_error("max_per_order", "Max must be at least the min.")
        if data.get("price") is not None and data["price"] < 0:
            self.add_error("price", "Price can't be negative.")
        if data.get("visibility") == TicketType.Visibility.HIDDEN and not data.get("access_code"):
            self.add_error("access_code", "Hidden tickets need an access code.")
        if data.get("sale_starts") and data.get("sale_ends") and data["sale_ends"] <= data["sale_starts"]:
            self.add_error("sale_ends", "Sales must end after they start.")
        return data

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["label", "kind", "options", "required", "applies_to", "help_text", "position"]
        widgets = {"options": forms.Textarea(attrs={"rows": 4}), "applies_to": forms.RadioSelect}
        labels = {"label": "Question", "required": "Required", "applies_to": "Ask"}

    def clean(self):
        data = super().clean()
        if data.get("kind") == Question.Kind.SELECT and not [o for o in (data.get("options") or "").splitlines() if o.strip()]:
            self.add_error("options", "Add at least one option, one per line.")
        return data
