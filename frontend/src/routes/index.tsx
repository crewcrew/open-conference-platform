import { createFileRoute } from "@tanstack/react-router";

import { EventsIndexPage } from "@/features/events/EventsIndexPage";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Open Conference Platform — open-source, self-hosted conference software" },
      { name: "description", content: "MIT-licensed, self-hosted conference software. Explore the attendee and organizer experience in an interactive demo." },
      { property: "og:title", content: "Open Conference Platform — open-source, self-hosted conference software" },
      { property: "og:description", content: "MIT-licensed, self-hosted conference software. Explore the attendee and organizer experience in an interactive demo." },
    ],
  }),
  component: EventsIndexPage,
});

