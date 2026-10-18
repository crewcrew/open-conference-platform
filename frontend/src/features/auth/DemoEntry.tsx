import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { Building2, ScanLine } from "lucide-react";

import type { DemoPersona } from "@/shared/demo/fixtures";
import { useMode } from "@/shared/mode";
import { PublicShell } from "@/shared/ui/public-shell";
import { enterDemo, sessionQuery } from "./api";

const PERSONAS: { id: DemoPersona; title: string; body: string; icon: typeof Building2 }[] = [
  {
    id: "owner",
    title: "Organization owner",
    body: "See event figures, orders, attendees, emails and every management area an owner can reach.",
    icon: Building2,
  },
  {
    id: "volunteer",
    title: "Door volunteer",
    body: "See exactly what a check-in volunteer gets: only their assigned event and the check-in station.",
    icon: ScanLine,
  },
];

export function DemoEntry({ target }: { target: string }) {
  const mode = useMode();
  const qc = useQueryClient();
  const navigate = useNavigate();

  function choose(p: DemoPersona) {
    qc.setQueryData(sessionQuery(mode).queryKey, enterDemo(p));
    if (target !== "/manage") navigate({ to: target, replace: true });
    else navigate({ to: "/manage/$orgSlug", params: { orgSlug: p === "owner" ? "sample-collective" : "sample-volunteers" }, replace: true });
  }

  return (
    <PublicShell>
      <div className="mx-auto max-w-3xl px-4 py-16">
        <p className="eyebrow">Organizer demo</p>
        <h1 className="mt-2 text-3xl font-semibold md:text-4xl">Enter organizer demo</h1>
        <p className="mt-3 max-w-xl text-lg text-muted-foreground">
          Pick a role to explore. There's no account to create and nothing to type — you'll look around a sample workspace.
        </p>
        <ul className="mt-8 grid gap-4 sm:grid-cols-2">
          {PERSONAS.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => choose(p.id)}
                className="panel flex h-full w-full flex-col items-start p-6 text-left transition-colors hover:border-primary/50 focus-visible:border-primary"
              >
                <p.icon className="size-5 text-primary" aria-hidden />
                <span className="mt-3 font-display text-xl font-semibold">Explore as {p.title.toLowerCase()}</span>
                <span className="mt-2 text-sm text-muted-foreground">{p.body}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-8 text-sm text-muted-foreground">
          In a self-hosted install, organizers sign in with their own account and changes like refunds, emails and check-ins
          are saved on your server. The demo shows the screens without doing any of that.{" "}
          <Link to="/" className="underline underline-offset-2">Back to events</Link>
        </p>
      </div>
    </PublicShell>
  );
}

