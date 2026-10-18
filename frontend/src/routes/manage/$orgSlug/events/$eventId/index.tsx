import { createFileRoute } from "@tanstack/react-router";

import { EventOverviewPage } from "@/features/reports/EventOverviewPage";

export const Route = createFileRoute("/manage/$orgSlug/events/$eventId/")({
  component: OverviewRoute,
});

function OverviewRoute() {
  const { orgSlug, eventId } = Route.useParams();
  return <EventOverviewPage orgSlug={orgSlug} eventId={eventId} />;
}

