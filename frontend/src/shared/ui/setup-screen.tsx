import { PlugZap } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { enableDemoMode } from "../mode";

export function SetupScreen() {
  return (
    <section aria-labelledby="setup-title" className="mx-auto max-w-2xl px-4 py-20">
      <div className="mb-6 inline-flex size-11 items-center justify-center rounded-full bg-accent text-accent-foreground" aria-hidden>
        <PlugZap className="size-5" />
      </div>
      <p className="eyebrow">Open Conference Platform</p>
      <h1 id="setup-title" className="mt-2 text-4xl font-semibold">Backend connection required</h1>
      <p className="mt-4 text-lg text-muted-foreground">
        This site shows conference events and organizer tools from a conference server that hasn't been connected yet.
        Event listings, tickets and organizer dashboards will appear here once it is.
      </p>

      <div className="panel mt-8 p-6">
        <h2 className="text-lg font-semibold">For the site operator</h2>
        <p className="mt-2 text-muted-foreground">
          Set the backend origin (without <code>/api/v1</code>) and rebuild:
        </p>
        <pre className="mt-3 overflow-x-auto rounded-md bg-muted p-3 text-sm"><code>VITE_OCP_API_URL=https://api.example.com</code></pre>
        <p className="mt-3 text-sm text-muted-foreground">
          The backend must allow this site's origin for CORS with credentials. See the README for cookie and domain setup.
        </p>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <button type="button" className={buttonVariants({ variant: "outline" })} onClick={() => enableDemoMode()}>
          Explore a preview with sample data
        </button>
        <span className="text-sm text-muted-foreground">Clearly labeled; nothing in the preview is real or actionable.</span>
      </div>
    </section>
  );
}

