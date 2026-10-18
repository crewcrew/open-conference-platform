import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { AttendeesPage, type AttendeesSearch } from "@/features/attendees/AttendeesPage";
import { parsePage } from "@/shared/search";

export const Route = createFileRoute("/manage/$orgSlug/events/$eventId/attendees")({
  validateSearch: (s: Record<string, unknown>): AttendeesSearch => ({
    page: parsePage(s["page"]),
    q: typeof s["q"] === "string" && s["q"] ? s["q"] : undefined,
  }),
  component: AttendeesRoute,
});

function AttendeesRoute() {
  const { orgSlug, eventId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });
  return <AttendeesPage orgSlug={orgSlug} eventId={eventId} search={search} onSearch={(next) => navigate({ search: next })} />;
}

