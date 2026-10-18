import { createFileRoute } from "@tanstack/react-router";

import { OrgEventsPage } from "@/features/organizations/OrgEventsPage";

export const Route = createFileRoute("/manage/$orgSlug/")({
  component: OrgEventsRoute,
});

function OrgEventsRoute() {
  const { orgSlug } = Route.useParams();
  return <OrgEventsPage orgSlug={orgSlug} />;
}

