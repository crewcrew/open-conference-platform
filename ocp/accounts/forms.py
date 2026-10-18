from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from .models import Invitation, Membership, Organization, Role

User = get_user_model()

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}))

    def clean(self):
        if self.cleaned_data.get("username"):
            self.cleaned_data["username"] = self.cleaned_data["username"].lower()
        return super().clean()

class SignupForm(forms.Form):
    """ORG-01: create an account and the organization it owns."""

    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"autocomplete": "given-name"}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"autocomplete": "family-name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), help_text="At least 10 characters.")
    organization = forms.CharField(max_length=200, label="Organisation name", required=False)

    def __init__(self, *args, require_org=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].required = require_org

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("There's already an account with this email. Sign in instead.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("password"):
            user = User(username=data.get("email", ""), email=data.get("email", ""), first_name=data.get("first_name", ""))
            try:
                password_validation.validate_password(data["password"], user)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return data

    def create_user(self):
        data = self.cleaned_data
        return User.objects.create_user(
            username=data["email"], email=data["email"], password=data["password"],
            first_name=data["first_name"], last_name=data["last_name"],
        )

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "contact_email", "website"]
        labels = {"name": "Organisation name", "contact_email": "Contact email"}

class InviteForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ["email", "role", "events"]
        widgets = {"events": forms.CheckboxSelectMultiple}
        help_texts = {"events": "Check-in volunteers can only scan tickets for the events ticked here."}

    def __init__(self, *args, organization, inviter_role, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["events"].queryset = organization.events.all()
        self.fields["events"].required = False
        if inviter_role != Role.OWNER:
            self.fields["role"].choices = [c for c in Role.choices if c[0] != Role.OWNER]

class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ["role", "events"]
        widgets = {"events": forms.CheckboxSelectMultiple}
        help_texts = {"events": "Only used for check-in volunteers."}

    def __init__(self, *args, organization, editor_role, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["events"].queryset = organization.events.all()
        self.fields["events"].required = False
        if editor_role != Role.OWNER:
            self.fields["role"].choices = [c for c in Role.choices if c[0] != Role.OWNER]
