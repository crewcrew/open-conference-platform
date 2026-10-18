import { createFileRoute } from "@tanstack/react-router";

import { ManageGate } from "@/features/organizations/ManageGate";

// Session lives in Django cookies on the backend origin, so the workspace renders client-side only.
export const Route = createFileRoute("/manage")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Organizer workspace — Open Conference Platform" },
      { name: "description", content: "Manage events, orders, attendees and communications." },
      { property: "og:title", content: "Organizer workspace — Open Conference Platform" },
      { property: "og:description", content: "Manage events, orders, attendees and communications." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ManageGate,
});

