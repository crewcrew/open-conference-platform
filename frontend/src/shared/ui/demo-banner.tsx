import { useMode } from "../mode";

export function DemoBanner() {
  const mode = useMode();
  if (mode !== "demo") return null;
  return (
    <div role="note" className="border-b bg-notice text-notice-foreground">
      <p className="mx-auto max-w-7xl px-4 py-2 text-sm">
        <strong>Interactive demo</strong> of open-source, self-hosted conference software. All events, people and figures are
        sample data — nothing is bought, sent or saved.
      </p>
    </div>
  );
}

