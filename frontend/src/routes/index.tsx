import { createFileRoute } from "@tanstack/react-router";

import { EventsIndexPage } from "@/features/events/EventsIndexPage";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Events — Open Conference Platform" },
      { name: "description", content: "Browse published conferences and events, read schedules and get tickets." },
      { property: "og:title", content: "Events — Open Conference Platform" },
      { property: "og:description", content: "Browse published conferences and events, read schedules and get tickets." },
    ],
  }),
  component: EventsIndexPage,
});

