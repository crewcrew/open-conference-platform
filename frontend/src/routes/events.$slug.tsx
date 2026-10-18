import { createFileRoute } from "@tanstack/react-router";

import { EventDetailPage } from "@/features/events/EventDetailPage";

export const Route = createFileRoute("/events/$slug")({
  head: () => ({
    meta: [
      { title: "Event details — Open Conference Platform" },
      { name: "description", content: "Event schedule, venue, accessibility information and tickets." },
      { property: "og:title", content: "Event details — Open Conference Platform" },
      { property: "og:description", content: "Event schedule, venue, accessibility information and tickets." },
    ],
  }),
  component: EventRoute,
});

function EventRoute() {
  const { slug } = Route.useParams();
  return <EventDetailPage slug={slug} />;
}

