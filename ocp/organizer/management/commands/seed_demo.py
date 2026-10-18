"""Demo data: an organisation, a two-day conference and realistic orders.

Everything here is made up. Email addresses use reserved example domains.
"""

import os
import random
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings
from django.utils import timezone

from ocp.accounts.models import Membership, Organization, Role
from ocp.comms.models import Communication, Delivery
from ocp.events.models import Event, Question, Session, TicketType
from ocp.ticketing import checkout
from ocp.ticketing.models import Coupon, Order, RefundRequest, Ticket
from ocp.ticketing.refunds import cancel_and_refund

TZ = ZoneInfo("Pacific/Auckland")

NAMES = [
    "Mere Tipene", "Sam Okafor", "Aroha Paewai", "Daniel Moore", "Priya Nair", "Ben Loader", "Kiri Walker",
    "Lena Okoro", "Tom Fraser", "Hemi Walker", "Grace Liu", "Matiu Rangi", "Sophie Turner", "Nikau Hale",
    "Ana Hale", "Ruby Taufa", "Hamish Grant", "Lena Park", "Olivia Chen", "Jo Okakura", "Wiremu Parata",
    "Sione Fifita", "Emma Wilson", "Raj Patel", "Mia Thompson", "Isla Brown", "Noah Smith", "Charlotte Lee",
    "Leo Martin", "Hana Kim", "Te Aniwa Reid", "Fatima Hassan", "Lucas Silva", "Amelia Scott", "Jack Ryan",
    "Ngaio Bell", "Ravi Shankar", "Zoe Adams", "Ethan Clarke", "Maia Henare", "Oscar Wright", "Ella Morgan",
    "Anahera Ruru", "Felix Wong", "Sarah O'Neill", "Chloe Nguyen", "Arjun Mehta", "Kate Sinclair", "Tim Baker",
    "Leilani Faleolo", "Paora Smith", "Yuki Tanaka", "Harriet Cole", "Finn Gallagher", "Ruth Mbeki", "Ari Cohen",
    "Moana Tuhiwai", "Grace Huang", "Liam O'Connor", "Sina Tuala", "Nina Petrova", "Eli Brooks", "Tui Marino",
]
NAMED_IN_SCENARIOS = {
    "Mere Tipene", "Sam Okafor", "Matiu Rangi", "Grace Liu", "Nikau Hale", "Ana Hale", "Ruby Taufa",
    "Hamish Grant", "Daniel Moore",
}


def local(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=TZ)


class Command(BaseCommand):
    help = "Create the Fieldwork 2027 demo organisation, event and sample orders."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Password for the demo accounts. A random one is made if omitted.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo seeding is allowed only in local development with DEBUG enabled.")
        if Organization.objects.filter(slug="fieldwork").exists():
            self.stdout.write("Demo data already exists. Delete db.sqlite3 and run migrate to start again.")
            return
        password = options["password"] or os.environ.get("OCP_DEMO_PASSWORD") or secrets.token_urlsafe(10)
        self.password_given = bool(options["password"] or os.environ.get("OCP_DEMO_PASSWORD"))
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            self._seed(password)

    def _seed(self, password):
        rng = random.Random(2027)
        User = get_user_model()

        def user(email, first, last):
            return User.objects.create_user(username=email, email=email, password=password, first_name=first, last_name=last)

        owner = user("alex@fieldwork.example", "Alex", "Moana")
        admin = user("priya@fieldwork.example", "Priya", "Raman")
        manager = user("tomasi@fieldwork.example", "Tomasi", "Fifita")
        volunteer = user("jo@fieldwork.example", "Jo", "Lee")

        org = Organization.objects.create(name="Fieldwork Collective", slug="fieldwork", contact_email="hello@fieldwork.example")
        Membership.objects.create(user=owner, organization=org, role=Role.OWNER)
        Membership.objects.create(user=admin, organization=org, role=Role.ADMIN)
        Membership.objects.create(user=manager, organization=org, role=Role.EVENT_MANAGER)
        crew = Membership.objects.create(user=volunteer, organization=org, role=Role.VOLUNTEER)

        event = Event.objects.create(
            organization=org,
            name="Fieldwork 2027",
            slug="fieldwork-2027",
            summary="Two days of talks and hands-on workshops for the people who research, design and build digital products.",
            description=(
                "Fieldwork is a two-day conference run by volunteers. Day one is talks across two rooms. "
                "Day two starts with a half-day workshop of your choice, then talks in the afternoon.\n\n"
                "Lunch, morning and afternoon tea are included on both days. Every room has step-free access and a hearing loop."
            ),
            timezone="Pacific/Auckland",
            starts_at=local(2027, 3, 18, 8, 0),
            ends_at=local(2027, 3, 19, 17, 30),
            venue_name="Harbourside Centre",
            venue_address="[Street address]\nWellington",
            accessibility_info="Step-free access to every room.\nHearing loop in Hall A and Room 2.\nQuiet room on level 1.",
            contact_email="hello@fieldwork.example",
            status=Event.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(days=60),
            booking_fee=Decimal("6.00"),
            refund_policy="Full refund until Mon 15 Feb 2027. Half refund until Thu 11 Mar 2027. No refunds after that.",
            full_refund_until=local(2027, 2, 15).date(),
            partial_refund_until=local(2027, 3, 11).date(),
            partial_refund_percent=50,
            order_prefix="FW27",
            retention_days=365,
        )
        crew.events.add(event)

        def session(title, kind, start, end, room="", speakers="", capacity=None, group=""):
            return Session.objects.create(
                event=event, title=title, kind=kind, starts_at=start, ends_at=end, room=room,
                speakers=speakers, capacity=capacity, choice_group=group,
            )

        talks = [
            session("Registration, badges and coffee", "break", local(2027, 3, 18, 8), local(2027, 3, 18, 9), "Foyer"),
            session("Fewer features, better products", "keynote", local(2027, 3, 18, 9), local(2027, 3, 18, 10), "Hall A", "Hana Whitlock"),
            session("Research ops when there's only one of you", "talk", local(2027, 3, 18, 10, 15), local(2027, 3, 18, 11), "Hall A", "Tomasi Fifita"),
            session("Pricing pages that tell the truth", "talk", local(2027, 3, 18, 11, 30), local(2027, 3, 18, 12, 30), "Hall A", "Priya Raman"),
            session("Accessibility debt is just debt", "talk", local(2027, 3, 18, 11, 30), local(2027, 3, 18, 12, 30), "Room 2", "Callum Reid"),
            session("Lunch", "break", local(2027, 3, 18, 12, 30), local(2027, 3, 18, 13, 30), "Foyer and terrace"),
            session("What we'd tell ourselves five years ago", "panel", local(2027, 3, 18, 16, 30), local(2027, 3, 18, 17, 30), "Hall A", "Four speakers"),
            session("Afternoon talks: shipping, measuring, saying no", "talk", local(2027, 3, 19, 13, 30), local(2027, 3, 19, 16, 30), "Hall A", "Three speakers"),
        ]
        workshops = [
            session("Running a usability study in a week", "workshop", local(2027, 3, 19, 9), local(2027, 3, 19, 12, 30), "Room 2", capacity=40, group="Friday workshop"),
            session("Writing requirements engineers trust", "workshop", local(2027, 3, 19, 9), local(2027, 3, 19, 12, 30), "Room 3", capacity=30, group="Friday workshop"),
            session("Service blueprints for small teams", "workshop", local(2027, 3, 19, 9), local(2027, 3, 19, 12, 30), "Room 4", capacity=30, group="Friday workshop"),
        ]

        def ticket_type(name, price, quantity, position, **extra):
            t = TicketType.objects.create(event=event, name=name, price=Decimal(price), quantity=quantity, position=position, **extra)
            t.sessions.set(talks + workshops)
            return t

        early = ticket_type("Early bird", "395.00", 150, 1, description="Both days, one workshop, all catering",
                            sale_ends=local(2026, 11, 30, 23, 59))
        standard = ticket_type("Standard", "495.00", 300, 2, description="Both days, one workshop, all catering",
                               sale_ends=local(2027, 3, 17, 23, 59))
        student = ticket_type("Student", "145.00", 50, 3, description="Both days and one workshop. Bring student ID.",
                              max_per_order=2, sale_ends=local(2027, 3, 17, 23, 59))
        crew_tickets = ticket_type("Speaker and volunteer", "0.00", 40, 4, description="For speakers and the volunteer crew.",
                                   visibility=TicketType.Visibility.HIDDEN, access_code="CREW27", max_per_order=1)

        Question.objects.create(event=event, label="Dietary requirements", kind=Question.Kind.SELECT,
                                options="None\nVegetarian\nVegan\nGluten free\nOther (we'll be in touch)", required=True, position=1)
        Question.objects.create(event=event, label="Access needs", kind=Question.Kind.TEXT, required=False,
                                help_text="Anything that would make the day easier for you.", position=2)

        community = Coupon.objects.create(event=event, code="COMMUNITY20", kind=Coupon.Kind.PERCENT, amount=Decimal("20"), max_redemptions=40)
        community.ticket_types.set([standard])
        meetup = Coupon.objects.create(event=event, code="WELLYMEETUP", kind=Coupon.Kind.FIXED, amount=Decimal("99"), max_redemptions=10)
        meetup.ticket_types.set([standard])
        expired = Coupon.objects.create(event=event, code="EARLYCREW", kind=Coupon.Kind.FIXED, amount=Decimal("50"),
                                        ends_at=local(2026, 9, 30, 23, 59), max_redemptions=20)
        expired.ticket_types.set([standard])
        partner = Coupon.objects.create(event=event, code="PARTNER10", kind=Coupon.Kind.PERCENT, amount=Decimal("10"),
                                        is_active=False, disabled_at=timezone.now() - timedelta(days=20))
        partner.ticket_types.set([early, standard, student])

        names = [name for name in NAMES if name not in NAMED_IN_SCENARIOS]
        rng.shuffle(names)
        orders = []

        def email_for(name):
            return name.lower().replace(" ", ".").replace("'", "") + "@example.co.nz"

        def place(people, ticket, coupon=None, access_code="", days_ago=0):
            order = checkout.start_order(event, {ticket.pk: len(people)}, access_code=access_code)
            if coupon:
                checkout.apply_coupon(order, coupon)
            purchaser = people[0]
            first, last = purchaser.split(" ", 1)
            attendees = {}
            for index, attendee in enumerate(order.attendees.order_by("position")):
                a_first, a_last = people[index].split(" ", 1)
                open_workshops = [w for w in workshops if not Session.objects.get(pk=w.pk).is_full]
                attendees[attendee.pk] = {
                    "first_name": a_first, "last_name": a_last, "email": email_for(people[index]),
                    "is_purchaser": index == 0,
                    "answers": {"Dietary requirements": rng.choice(["None", "None", "Vegetarian", "Vegan", "Gluten free"]), "Access needs": ""},
                    "session_ids": [rng.choice(open_workshops).pk],
                }
            checkout.save_details(order, {
                "purchaser_first_name": first, "purchaser_last_name": last, "purchaser_email": email_for(purchaser),
                "purchaser_organisation": rng.choice(["", "", "Kererū Labs", "Te Ao Design Co", "Harbour Health", "Southern Software"]),
                "marketing_consent": rng.random() < 0.4, "answers": {},
            }, attendees)
            ref = f"test_seed_{order.number}"
            Order.objects.filter(pk=order.pk).update(payment_provider="test", payment_ref=ref)
            checkout.confirm_paid(order.pk, provider="test", payment_ref=ref)
            when = timezone.now() - timedelta(days=days_ago, hours=rng.randint(0, 20), minutes=rng.randint(0, 59))
            Order.objects.filter(pk=order.pk).update(created_at=when, paid_at=when + timedelta(minutes=3))
            Ticket.objects.filter(order=order).update(created_at=when + timedelta(minutes=3))
            order.refresh_from_db()
            orders.append(order)
            return order

        def take(n):
            group = [names.pop() for _ in range(n)]
            return group

        # Early bird surge after launch, then a steady trickle.
        for days_ago in [58, 57, 57, 56, 55, 54, 52, 50, 47, 44, 40, 36, 33, 29, 25, 21, 18, 14, 10, 7, 4, 2]:
            if len(names) < 3:
                break
            kind = rng.random()
            if days_ago > 30 or kind < 0.45:
                place(take(rng.choice([1, 1, 2, 3])), early, days_ago=days_ago)
            elif kind < 0.75:
                place(take(rng.choice([1, 2])), standard, coupon=rng.choice([None, "COMMUNITY20"]), days_ago=days_ago)
            else:
                place(take(1), student, days_ago=days_ago)

        mere = place(["Mere Tipene", "Sam Okafor"], standard, coupon="COMMUNITY20", days_ago=12)
        place(["Matiu Rangi", "Grace Liu"], standard, coupon="WELLYMEETUP", days_ago=9)
        nikau = place(["Nikau Hale", "Ana Hale"], standard, days_ago=20)
        ruby = place(["Ruby Taufa", "Hamish Grant"], standard, days_ago=16)
        dan = place(["Daniel Moore"], standard, days_ago=6)
        place(["Hana Whitlock"], crew_tickets, access_code="CREW27", days_ago=30)
        place(["Callum Reid"], crew_tickets, access_code="CREW27", days_ago=30)

        # A bounced confirmation email (acceptance scenario 10).
        dan_attendee = dan.attendees.first()
        dan_attendee.email = "dan.moore@exmaple.co.nz"
        dan_attendee.save(update_fields=["email"])
        Order.objects.filter(pk=dan.pk).update(purchaser_email="dan.moore@exmaple.co.nz")
        Delivery.objects.filter(order=dan).update(
            to_email="dan.moore@exmaple.co.nz", status=Delivery.Status.FAILED,
            error="550 5.1.1 <dan.moore@exmaple.co.nz>: Recipient address rejected: domain not found",
        )

        # An open cancellation request from a booking link.
        ana_ticket = nikau.tickets.get(attendee__first_name="Ana")
        request = RefundRequest.objects.create(order=nikau, reason="Ana can't travel any more.")
        request.tickets.set([ana_ticket])
        RefundRequest.objects.filter(pk=request.pk).update(created_at=local(2027, 3, 10, 20, 31) if timezone.now() > local(2027, 3, 10) else timezone.now() - timedelta(days=2))

        # A completed partial refund.
        hamish_ticket = ruby.tickets.get(attendee__first_name="Hamish")
        cancel_and_refund(ruby, [hamish_ticket], Decimal("495.00"), owner, note="Within policy: full refund.", notify=False)

        # Reminders.
        Communication.objects.create(
            event=event, kind=Communication.Kind.UPDATE, subject="One week to go: Fieldwork 2027",
            body="Hi {first name},\n\nFieldwork 2027 is a week away. Your workshop: {workshop}.\n\nYour booking: {booking link}",
            status=Communication.Status.SCHEDULED, scheduled_for=event.starts_at - timedelta(days=7), is_reminder=True, created_by=owner,
        )
        Communication.objects.create(
            event=event, kind=Communication.Kind.UPDATE, subject="See you tomorrow at Fieldwork 2027",
            body="Hi {first name},\n\nDoors open at 08:00. Bring your ticket QR code.\n\nYour booking: {booking link}",
            status=Communication.Status.SCHEDULED, scheduled_for=event.starts_at - timedelta(days=1), is_reminder=True, created_by=owner,
        )

        issued = Ticket.objects.filter(event=event, status=Ticket.Status.VALID).count()
        self.stdout.write(self.style.SUCCESS(f"Created Fieldwork 2027 with {len(orders)} orders and {issued} valid tickets."))
        self.stdout.write("")
        if self.password_given:
            self.stdout.write("Sign in at /accounts/login/ with any of these. The password is OCP_DEMO_PASSWORD from .env (or --password).")
        else:
            self.stdout.write("Sign in at /accounts/login/ with any of these. Password for all:")
            self.stdout.write(f"  {password}")
        self.stdout.write("  alex@fieldwork.example    Owner")
        self.stdout.write("  priya@fieldwork.example   Administrator")
        self.stdout.write("  tomasi@fieldwork.example  Event manager")
        self.stdout.write("  jo@fieldwork.example      Check-in volunteer")
        self.stdout.write("")
        self.stdout.write("Public event page: /e/fieldwork-2027/  (hidden crew tickets: ?code=CREW27)")
        self.stdout.write(f"Sample booking:   /booking/{mere.access_token}/")
