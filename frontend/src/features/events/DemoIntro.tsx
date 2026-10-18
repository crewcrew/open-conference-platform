import { Link } from "@tanstack/react-router";

import { buttonVariants } from "@/components/ui/button";
import { SourceLinks } from "@/shared/ui/source-links";

export function DemoIntro() {
  return (
    <section aria-labelledby="intro" className="border-b bg-card">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-14 md:grid-cols-[1.4fr_1fr] md:items-end">
        <div>
          <p className="eyebrow">Open source · MIT · Self-hosted</p>
          <h1 id="intro" className="mt-3 text-4xl font-semibold md:text-5xl">Run your own conferences, on your own server.</h1>
          <p className="mt-4 max-w-xl text-lg text-muted-foreground">
            Open Conference Platform is free conference software you host yourself: public event pages, tickets and schedules
            for attendees, plus a calm workspace for organizers and door volunteers. Try both sides below.
          </p>
        </div>
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <a href="#events" className={buttonVariants({ variant: "outline" })}>Browse sample events</a>
            <Link to="/login" className={buttonVariants()}>Explore organizer demo</Link>
          </div>
          <SourceLinks />
        </div>
      </div>
    </section>
  );
}

