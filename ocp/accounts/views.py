"""Sign-up, organizations and team roles (ORG-01 to ORG-05)."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from ocp.accounts import audit
from ocp.accounts.models import Invitation, Membership, Organization, Role
from ocp.comms.services import absolute, deliver
from ocp.comms.models import Delivery
from ocp.ticketing.models import Ticket

from ocp.organizer.context import page
from ocp.organizer.decorators import organizer_view
from .forms import InviteForm, MembershipForm, OrganizationForm, SignupForm
from ocp.core.forms import unique_slug


def signup(request):
    if request.user.is_authenticated:
        return redirect("organizer:home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.create_user()
            organization = Organization.objects.create(
                name=form.cleaned_data["organization"],
                slug=unique_slug(Organization, form.cleaned_data["organization"]),
                contact_email=user.email,
            )
            Membership.objects.create(user=user, organization=organization, role=Role.OWNER)
            audit.record(organization, user, "org.created", f"{user.get_full_name()} created {organization.name}.")
        login(request, user)
        messages.success(request, f"Welcome. {organization.name} is ready for its first event.")
        return redirect("organizer:org", org_slug=organization.slug)
    return render(request, "registration/signup.html", {"form": form})


@login_required
def home(request):
    memberships = list(request.user.memberships.select_related("organization"))
    if len(memberships) == 1:
        membership = memberships[0]
        if membership.role == Role.VOLUNTEER:
            return redirect("organizer:volunteer", org_slug=membership.organization.slug)
        return redirect("organizer:org", org_slug=membership.organization.slug)
    return render(request, "organizer/home.html", {"memberships": memberships})


@login_required
def org_create(request):
    form = OrganizationForm(request.POST or None, initial={"contact_email": request.user.email})
    if request.method == "POST" and form.is_valid():
        organization = form.save(commit=False)
        organization.slug = unique_slug(Organization, organization.name)
        organization.save()
        Membership.objects.create(user=request.user, organization=organization, role=Role.OWNER)
        audit.record(organization, request.user, "org.created", f"{request.user.get_full_name()} created {organization.name}.")
        return redirect("organizer:org", org_slug=organization.slug)
    return render(request, "organizer/org_form.html", {"form": form, "creating": True})


@organizer_view()
def org_home(request):
    if request.membership.role == Role.VOLUNTEER:
        return redirect("organizer:volunteer", org_slug=request.org.slug)
    events = request.org.events.annotate(
        issued=Count("tickets", filter=Q(tickets__status=Ticket.Status.VALID))
    ).order_by("-starts_at")
    return page(request, "organizer/events.html", {"events": events})


@organizer_view("check_in")
def volunteer_home(request):
    if request.membership.role == Role.VOLUNTEER:
        events = request.membership.events.order_by("starts_at")
    else:
        events = request.org.events.order_by("-starts_at")
    return page(request, "organizer/volunteer.html", {"events": events})


@organizer_view("manage_org")
def org_settings(request):
    form = OrganizationForm(request.POST or None, instance=request.org)
    if request.method == "POST" and form.is_valid():
        changes = audit.diff(request.org, form)
        form.save()
        if changes:
            audit.record(request.org, request.user, "org.updated", "Updated organisation details.", obj=request.org, changes=changes)
        messages.success(request, "Saved.")
        return redirect("organizer:org_settings", org_slug=request.org.slug)
    return page(request, "organizer/org_form.html", {"form": form, "creating": False})


@organizer_view("manage_team")
def team(request):
    invite_form = InviteForm(
        request.POST or None, organization=request.org, inviter_role=request.membership.role, prefix="invite"
    )
    if request.method == "POST" and invite_form.is_valid():
        invitation = invite_form.save(commit=False)
        invitation.organization = request.org
        invitation.invited_by = request.user
        invitation.email = invitation.email.lower()
        invitation.save()
        invite_form.save_m2m()
        url = absolute(reverse("accept_invite", args=[invitation.token]))
        deliver(
            Delivery.Kind.INVITATION,
            invitation.email,
            f"You're invited to {request.org.name}",
            f"{request.user.get_full_name()} invited you to help run events for {request.org.name} "
            f"as {invitation.get_role_display().lower()}.\n\nAccept the invitation: {url}\n",
        )
        audit.record(
            request.org, request.user, "team.invited",
            f"Invited {invitation.email} as {invitation.get_role_display()}.", obj=invitation,
        )
        messages.success(request, f"Invitation sent to {invitation.email}. They can also use this link: {url}")
        return redirect("organizer:team", org_slug=request.org.slug)
    members = request.org.memberships.select_related("user").prefetch_related("events").order_by("role", "user__first_name")
    invitations = request.org.invitations.filter(accepted_at__isnull=True)
    return page(request, "organizer/team.html", {"members": members, "invitations": invitations, "invite_form": invite_form})


@organizer_view("manage_team")
def member_edit(request, member_id):
    member = get_object_or_404(Membership, pk=member_id, organization=request.org)
    if member.role == Role.OWNER and request.membership.role != Role.OWNER:
        raise PermissionDenied
    form = MembershipForm(request.POST or None, instance=member, organization=request.org, editor_role=request.membership.role)
    if request.method == "POST":
        if request.POST.get("action") == "remove":
            if member.role == Role.OWNER and request.org.memberships.filter(role=Role.OWNER).count() == 1:
                messages.error(request, "Every organisation needs at least one owner.")
                return redirect("organizer:team", org_slug=request.org.slug)
            audit.record(request.org, request.user, "team.removed", f"Removed {member.user.email} from the team.")
            member.delete()
            messages.success(request, "Removed from the team.")
            return redirect("organizer:team", org_slug=request.org.slug)
        if form.is_valid():
            if (
                member.role == Role.OWNER
                and form.cleaned_data["role"] != Role.OWNER
                and request.org.memberships.filter(role=Role.OWNER).count() == 1
            ):
                form.add_error("role", "Every organisation needs at least one owner.")
            else:
                changes = audit.diff(member, form)
                form.save()
                audit.record(
                    request.org, request.user, "team.role_changed",
                    f"Changed {member.user.email} to {member.get_role_display()}.", obj=member, changes=changes,
                )
                messages.success(request, "Saved.")
                return redirect("organizer:team", org_slug=request.org.slug)
    return page(request, "organizer/member_form.html", {"member": member, "form": form})


@organizer_view("manage_team")
@require_POST
def invite_revoke(request, invite_id):
    invitation = get_object_or_404(Invitation, pk=invite_id, organization=request.org, accepted_at__isnull=True)
    audit.record(request.org, request.user, "team.invite_revoked", f"Withdrew the invitation to {invitation.email}.")
    invitation.delete()
    messages.success(request, "Invitation withdrawn.")
    return redirect("organizer:team", org_slug=request.org.slug)


def accept_invite(request, token):
    invitation = get_object_or_404(Invitation, token=token)
    if invitation.accepted_at:
        messages.info(request, "This invitation has already been used. Sign in to continue.")
        return redirect("login")

    if request.user.is_authenticated:
        if request.user.email.lower() != invitation.email.lower():
            raise Http404
        if request.method == "POST":
            _join(invitation, request.user)
            return redirect("organizer:home")
        return render(request, "registration/accept_invite.html", {"invitation": invitation, "form": None})

    form = SignupForm(request.POST or None, initial={"email": invitation.email}, require_org=False)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["email"] != invitation.email.lower():
            form.add_error("email", "Use the email address the invitation was sent to.")
        else:
            with transaction.atomic():
                user = form.create_user()
                _join(invitation, user)
            login(request, user)
            return redirect("organizer:home")
    return render(request, "registration/accept_invite.html", {"invitation": invitation, "form": form})


def _join(invitation, user):
    membership, _ = Membership.objects.get_or_create(
        user=user, organization=invitation.organization, defaults={"role": invitation.role}
    )
    membership.events.add(*invitation.events.all())
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    audit.record(invitation.organization, user, "team.joined", f"{user.email} joined as {membership.get_role_display()}.")
