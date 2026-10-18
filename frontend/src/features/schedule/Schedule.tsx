import type { ScheduleSession } from "@/shared/api/types";
import { dayKey, formatDate, formatTime, humanize, tzAbbrev } from "@/shared/format";

export function groupByDay(sessions: ScheduleSession[], tz: string) {
  const sorted = [...sessions].sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  const groups = new Map<string, ScheduleSession[]>();
  for (const s of sorted) {
    const key = dayKey(s.starts_at, tz);
    groups.set(key, [...(groups.get(key) ?? []), s]);
  }
  return [...groups.entries()];
}

function speakersOf(s: ScheduleSession) {
  return Array.isArray(s.speakers) ? s.speakers.join(", ") : s.speakers;
}

export function Schedule({ sessions, timezone }: { sessions: ScheduleSession[]; timezone: string }) {
  if (sessions.length === 0) {
    return <p className="text-muted-foreground">The schedule hasn't been published yet.</p>;
  }
  const days = groupByDay(sessions, timezone);
  return (
    <div className="space-y-10">
      <p className="text-sm text-muted-foreground">
        Times shown in the event's local time ({timezone}, {tzAbbrev(sessions[0]!.starts_at, timezone)}).
      </p>
      {days.map(([key, items]) => (
        <section key={key} aria-labelledby={`day-${key}`}>
          <h3 id={`day-${key}`} className="mb-3 text-xl font-semibold">{formatDate(items[0]!.starts_at, timezone)}</h3>
          <ol className="panel divide-y">
            {items.map((s) => (
              <li key={s.id} className="grid gap-1 p-4 sm:grid-cols-[8rem_1fr] sm:gap-6">
                <p className="font-medium tabular-nums">
                  <time dateTime={s.starts_at}>{formatTime(s.starts_at, timezone)}</time>–
                  <time dateTime={s.ends_at}>{formatTime(s.ends_at, timezone)}</time>
                </p>
                <div>
                  <p className="font-semibold">{s.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {[humanize(s.kind || "session"), s.room, speakersOf(s)].filter(Boolean).join(" · ")}
                  </p>
                  {s.description && <p className="mt-1.5 text-sm">{s.description}</p>}
                </div>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

