import { useNavigate } from "@tanstack/react-router";

import { disableDemoMode, useMode } from "../mode";
import { setDemoSignedIn } from "../demo/fixtures";
import { isDemoEnvEnabled } from "../config";

export function DemoBanner() {
  const mode = useMode();
  const navigate = useNavigate();
  if (mode !== "demo") return null;
  return (
    <div role="note" className="border-b bg-notice text-notice-foreground">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-2 text-sm">
        <p>
          <strong>Preview mode.</strong> Everything shown is sample data. Nothing can be bought, changed or checked in, and
          no figures are real.
        </p>
        {!isDemoEnvEnabled() && (
          <button
            type="button"
            className="underline underline-offset-2"
            onClick={() => {
              setDemoSignedIn(false);
              disableDemoMode();
              navigate({ to: "/" });
            }}
          >
            Exit preview
          </button>
        )}
      </div>
    </div>
  );
}

