from django import forms
from django.utils.text import slugify

from ocp.events.models import Question


def question_field(question):
    common = {"label": question.label, "help_text": question.help_text, "required": question.required}
    if question.kind == Question.Kind.TEXTAREA:
        return forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), max_length=2000, **common)
    if question.kind == Question.Kind.SELECT:
        choices = [("", "Choose…")] + [(option, option) for option in question.option_list]
        return forms.ChoiceField(choices=choices, **common)
    if question.kind == Question.Kind.CHECKBOX:
        return forms.BooleanField(**common)
    return forms.CharField(max_length=500, **common)


def add_questions(form, questions):
    for question in questions:
        form.fields[question.field_name] = question_field(question)


def answers_from(form, questions):
    return {question.label: form.cleaned_data.get(question.field_name) for question in questions}


def initial_answers(answers, questions):
    by_label = answers or {}
    return {q.field_name: by_label.get(q.label) for q in questions if q.label in by_label}


class PurchaserForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"autocomplete": "given-name"}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"autocomplete": "family-name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    organisation = forms.CharField(
        max_length=200, required=False, label="Organisation", widget=forms.TextInput(attrs={"autocomplete": "organization"})
    )
    marketing_consent = forms.BooleanField(required=False)

    def __init__(self, *args, questions=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = list(questions)
        add_questions(self, self.questions)

    def question_fields(self):
        return [self[q.field_name] for q in self.questions]


class AttendeeForm(forms.Form):
    is_purchaser = forms.BooleanField(required=False)
    first_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=False)
    email = forms.EmailField(required=False)

    def __init__(self, *args, attendee, questions=(), allow_self=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.attendee = attendee
        self.allow_self = allow_self
        self.questions = list(questions)
        add_questions(self, self.questions)
        for name in ("first_name", "last_name", "email"):
            # Required unless "this ticket is for me" is ticked; checked in clean().
            self.fields[name].conditional = True
        if not allow_self:
            del self.fields["is_purchaser"]
        self.groups = []
        chosen = set(attendee.sessions.values_list("id", flat=True)) if attendee.pk else set()
        for group, sessions in attendee.ticket_type.choice_groups().items():
            name = f"group_{slugify(group) or 'sessions'}"
            self.fields[name] = forms.ChoiceField(
                choices=[(str(s.pk), s.title) for s in sessions],
                required=True,
                label=group,
                error_messages={"required": f"Choose one: {group}."},
            )
            options = [
                {"session": s, "value": str(s.pk), "full": s.is_full and s.pk not in chosen, "left": s.places_left}
                for s in sessions
            ]
            already = next((str(s.pk) for s in sessions if s.pk in chosen), None)
            if already and name not in self.initial:
                self.initial[name] = already
            current = self.data.get(self.add_prefix(name)) if self.is_bound else self.initial.get(name)
            self.groups.append(
                {"name": name, "html_name": self.add_prefix(name), "label": group, "options": options, "current": current}
            )

    def clean(self):
        data = super().clean()
        if not data.get("is_purchaser"):
            for field in ("first_name", "last_name", "email"):
                if not data.get(field):
                    self.add_error(field, "Required for each ticket.")
        for group in self.groups:
            value = data.get(group["name"])
            option = next((o for o in group["options"] if o["value"] == value), None)
            if option and option["full"]:
                self.add_error(group["name"], f"{option['session'].title} is full. Choose another.")
        return data

    def session_ids(self):
        return [int(self.cleaned_data[g["name"]]) for g in self.groups if self.cleaned_data.get(g["name"])]

    def group_errors(self, group):
        return self.errors.get(group["name"], [])

    def question_fields(self):
        return [self[q.field_name] for q in self.questions]


class BookingLookupForm(forms.Form):
    email = forms.EmailField(label="Email you booked with", widget=forms.EmailInput(attrs={"autocomplete": "email"}))


class RefundRequestForm(forms.Form):
    tickets = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, label="Tickets to cancel")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), max_length=1000, required=False, label="Reason")

    def __init__(self, *args, tickets=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tickets"].choices = [
            (str(t.pk), f"{t.attendee.full_name or t.display_id} · {t.ticket_type.name}") for t in tickets
        ]
