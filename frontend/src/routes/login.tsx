import { createFileRoute } from "@tanstack/react-router";

import { LoginPage } from "@/features/auth/LoginPage";

export const Route = createFileRoute("/login")({
  ssr: false,
  validateSearch: (s: Record<string, unknown>): { redirect?: string | undefined } => ({
    redirect: typeof s["redirect"] === "string" ? s["redirect"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Organizer sign in — Open Conference Platform" },
      { name: "description", content: "Sign in to the organizer workspace to manage your events." },
      { property: "og:title", content: "Organizer sign in — Open Conference Platform" },
      { property: "og:description", content: "Sign in to the organizer workspace to manage your events." },
    ],
  }),
  component: LoginRoute,
});

function LoginRoute() {
  const { redirect } = Route.useSearch();
  return <LoginPage redirect={redirect} />;
}

