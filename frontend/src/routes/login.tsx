import { createFileRoute } from "@tanstack/react-router";

import { LoginPage } from "@/features/auth/LoginPage";

export const Route = createFileRoute("/login")({
  ssr: false,
  validateSearch: (s: Record<string, unknown>): { redirect?: string | undefined } => ({
    redirect: typeof s["redirect"] === "string" ? s["redirect"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Organizer workspace — Open Conference Platform" },
      { name: "description", content: "Enter the organizer workspace to manage events, orders, attendees and check-in." },
      { property: "og:title", content: "Organizer workspace — Open Conference Platform" },
      { property: "og:description", content: "Enter the organizer workspace to manage events, orders, attendees and check-in." },
    ],
  }),
  component: LoginRoute,
});

function LoginRoute() {
  const { redirect } = Route.useSearch();
  return <LoginPage redirect={redirect} />;
}

