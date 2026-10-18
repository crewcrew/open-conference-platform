function safeTz(tz: string | undefined): string {
  if (!tz) return "UTC";
  try {
    new Intl.DateTimeFormat("en", { timeZone: tz });
    return tz;
  } catch {
    return "UTC";
  }
}

export function formatInTz(iso: string, tz: string, opts: Intl.DateTimeFormatOptions): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", { timeZone: safeTz(tz), ...opts }).format(d);
}

export function formatTime(iso: string, tz: string) {
  return formatInTz(iso, tz, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
}

export function formatDate(iso: string, tz: string) {
  return formatInTz(iso, tz, { weekday: "short", day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string | null | undefined, tz = "UTC") {
  if (!iso) return "—";
  return formatInTz(iso, tz, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
}

export function tzAbbrev(iso: string, tz: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return tz;
  const part = new Intl.DateTimeFormat("en-GB", { timeZone: safeTz(tz), timeZoneName: "short" })
    .formatToParts(d)
    .find((p) => p.type === "timeZoneName");
  return part?.value ?? tz;
}

/** Calendar day key (YYYY-MM-DD) in the event's timezone. */
export function dayKey(iso: string, tz: string) {
  return formatInTz(iso, tz, { year: "numeric", month: "2-digit", day: "2-digit" })
    .split("/")
    .reverse()
    .join("-");
}

export function formatEventDates(startsAt: string, endsAt: string, tz: string) {
  if (dayKey(startsAt, tz) === dayKey(endsAt, tz)) {
    return `${formatDate(startsAt, tz)} · ${formatTime(startsAt, tz)}–${formatTime(endsAt, tz)} ${tzAbbrev(startsAt, tz)}`;
  }
  return `${formatDate(startsAt, tz)} – ${formatDate(endsAt, tz)}`;
}

/** Decimal amounts arrive as JSON strings. */
export function formatMoney(amount: string | null | undefined, currency: string) {
  if (amount === null || amount === undefined || amount === "") return "—";
  const n = Number(amount);
  if (!Number.isFinite(n)) return amount;
  try {
    return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(n);
  } catch {
    return `${n.toFixed(2)} ${currency}`;
  }
}

export function isZero(amount: string | null | undefined) {
  return amount !== null && amount !== undefined && Number(amount) === 0;
}

export function humanize(value: string) {
  const s = value.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

