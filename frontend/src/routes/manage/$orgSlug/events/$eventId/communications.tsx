import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { CommunicationsPage } from "@/features/communications/CommunicationsPage";
import { parsePage } from "@/shared/search";

export const Route = createFileRoute("/manage/$orgSlug/events/$eventId/communications")({
  validateSearch: (s: Record<string, unknown>): { page?: number | undefined } => ({ page: parsePage(s["page"]) }),
  component: CommsRoute,
});

function CommsRoute() {
  const { orgSlug, eventId } = Route.useParams();
  const { page } = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });
  return <CommunicationsPage orgSlug={orgSlug} eventId={eventId} page={page ?? 1} onPage={(p) => navigate({ search: { page: p } })} />;
}

