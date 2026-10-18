import time

from django.core.management.base import BaseCommand

from ocp.comms.services import process_due


class Command(BaseCommand):
    help = "Send scheduled emails that are due and release expired checkout holds. Run every minute."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Keep running, checking every 60 seconds.")

    def handle(self, *args, **options):
        while True:
            sent = process_due()
            if sent or not options["loop"]:
                self.stdout.write(f"Sent {sent} scheduled email(s).")
            if not options["loop"]:
                return
            time.sleep(60)
