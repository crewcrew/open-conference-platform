import { ScanLine } from "lucide-react";

import { EventGate } from "@/features/organizations/EventGate";
import { djangoPaths } from "@/shared/backend-links";
import { ManagementLink } from "@/shared/ui/management-link";

export function CheckinPage({ orgSlug, eventId }: { orgSlug: string; eventId: string }) {
  return (
    <EventGate orgSlug={orgSlug} eventId={eventId} requires="check_in" title="Check-in">
      {(event) => (
        <div className="panel max-w-2xl p-8">
          <div className="mb-4 inline-flex size-11 items-center justify-center rounded-full bg-accent text-accent-foreground" aria-hidden>
            <ScanLine className="size-5" />
          </div>
          <h2 className="text-2xl font-semibold">Check-in station</h2>
          <p className="mt-2 text-muted-foreground">
            Scanning tickets and admitting attendees happens on the check-in station, which records each check-in on the
            conference server. Open it on the device you'll use at the door.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <ManagementLink variant="default" path={event.scanner_url || djangoPaths.checkin(event.id)}>Open check-in station</ManagementLink>
          </div>
        </div>
      )}
    </EventGate>
  );
}

