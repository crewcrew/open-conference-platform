from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ocp.accounts import audit
from ocp.checkin.models import CheckInEvent
from ocp.comms.models import Delivery
from ocp.events.models import Event
from ocp.ticketing.models import Attendee, Order


class Command(BaseCommand):
    help = (
        "Remove attendee personal data from events past their retention period (ATT-08). "
        "Counts, money and attendance totals are kept; names, emails and answers are removed."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()
        for event in Event.objects.filter(retention_days__isnull=False):
            if event.ends_at + timedelta(days=event.retention_days) > now:
                continue
            orders = Order.objects.filter(event=event).exclude(purchaser_email="")
            attendees = Attendee.objects.filter(order__event=event).exclude(email="", first_name="Removed")
            if not orders.exists() and not attendees.exists():
                continue
            self.stdout.write(f"{event.name}: {orders.count()} orders, {attendees.count()} attendees")
            if options["dry_run"]:
                continue
            with transaction.atomic():
                orders.update(
                    purchaser_first_name="Removed", purchaser_last_name="", purchaser_email="",
                    purchaser_organisation="", purchaser_answers={},
                )
                attendees.update(first_name="Removed", last_name="", email="", answers={})
                Delivery.objects.filter(event=event).update(to_email="removed@invalid", body="", subject="(removed)")
                CheckInEvent.objects.filter(event=event).update(scanned_code="")
                audit.record(event.organization, None, "data.purged", "Removed attendee personal data after the retention period.", event=event)
        self.stdout.write("Done.")
