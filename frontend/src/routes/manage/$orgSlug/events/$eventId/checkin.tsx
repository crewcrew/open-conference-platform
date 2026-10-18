import { createFileRoute } from "@tanstack/react-router";

import { CheckinPage } from "@/features/checkin/CheckinPage";

export const Route = createFileRoute("/manage/$orgSlug/events/$eventId/checkin")({
  component: CheckinRoute,
});

function CheckinRoute() {
  const { orgSlug, eventId } = Route.useParams();
  return <CheckinPage orgSlug={orgSlug} eventId={eventId} />;
}

