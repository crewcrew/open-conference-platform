from django import forms
from django.utils import timezone
from ocp.core.forms import DATETIME_WIDGET

class ComposeForm(forms.Form):
    kind = forms.ChoiceField(
        choices=[("update", "Event update"), ("marketing", "News or promotion")], widget=forms.RadioSelect, initial="update", label="What kind of message"
    )
    ticket_type = forms.ChoiceField(required=False, label="Ticket type")
    session = forms.ChoiceField(required=False, label="Session")
    attendance = forms.ChoiceField(
        required=False,
        choices=[("", "Anyone"), ("checked_in", "Checked in"), ("not_checked_in", "Not checked in")],
        label="Attendance",
    )
    subject = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 9}), label="Message")
    when = forms.ChoiceField(choices=[("now", "Send now"), ("schedule", "Schedule")], widget=forms.RadioSelect, initial="now")
    scheduled_for = forms.DateTimeField(required=False, widget=DATETIME_WIDGET, label="Send at")

    def __init__(self, *args, event, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ticket_type"].choices = [("", "All types")] + [(str(t.pk), t.name) for t in event.ticket_types.all()]
        self.fields["session"].choices = [("", "All sessions")] + [
            (str(s.pk), f"{s.choice_group + ': ' if s.choice_group else ''}{s.title}") for s in event.sessions.all()
        ]

    def clean(self):
        data = super().clean()
        if data.get("when") == "schedule":
            when = data.get("scheduled_for")
            if not when:
                self.add_error("scheduled_for", "Choose when to send it.")
            elif when <= timezone.now():
                self.add_error("scheduled_for", "Choose a time in the future.")
        return data

    def audience(self):
        data = self.cleaned_data
        return {key: data[key] for key in ("ticket_type", "session", "attendance") if data.get(key)}
