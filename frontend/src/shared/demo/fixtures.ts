/**
 * SAMPLE DATA for the clearly labeled preview mode only. Never used in live mode.
 * All values are fictional and must not be presented as real metrics.
 */
import type {
  Attendee,
  Communication,
  Dashboard,
  EventSummary,
  EventDetail,
  OrgEvent,
  Paginated,
  Session,
} from "../api/types";
import { ApiError } from "../api/client";

export type DemoPersona = "owner" | "volunteer";
const PERSONA_KEY = "ocp-demo-persona"; // demo role choice only — never credentials

export function getDemoPersona(): DemoPersona | null {
  if (typeof window === "undefined") return null;
  const v = window.sessionStorage.getItem(PERSONA_KEY);
  return v === "owner" || v === "volunteer" ? v : null;
}

export function setDemoPersona(p: DemoPersona | null) {
  if (typeof window === "undefined") return;
  if (p) window.sessionStorage.setItem(PERSONA_KEY, p);
  else window.sessionStorage.removeItem(PERSONA_KEY);
}

export function demoSession(persona: DemoPersona | null = getDemoPersona()): Session {
  const volunteerOrg = { slug: "sample-volunteers", name: "Harbour Volunteers (sample)", role: "volunteer" };
  return {
    authenticated: persona !== null,
    csrf_token: "demo",
    user:
      persona === "owner"
        ? { name: "Demo organizer (owner)", email: "owner@demo.example" }
        : persona === "volunteer"
          ? { name: "Demo door volunteer", email: "volunteer@demo.example" }
          : null,
    organizations:
      persona === "owner"
        ? [{ slug: "sample-collective", name: "Northwind Collective (sample)", role: "owner" }, volunteerOrg]
        : persona === "volunteer"
          ? [volunteerOrg]
          : [],
  };
}

function eventDetails(): EventDetail[] {
  return [
    {
      id: 101,
      name: "Northwind Developer Summit",
      slug: "northwind-developer-summit",
      summary: "Two days of talks and workshops on building calm, durable software. (Sample event)",
      starts_at: "2026-11-19T09:00:00Z",
      ends_at: "2026-11-20T17:30:00Z",
      timezone: "Europe/London",
      venue_name: "Example Hall",
      status: "published",
      currency: "GBP",
      public_url: "",
      description:
        "This is a sample event in the Open Conference Platform demo.\n\nTwo days of talks and hands-on workshops across two rooms, with a closing panel on maintaining software for the long run.",
      venue_address: "1 Example Street, London",
      accessibility_info: "Step-free access to all rooms. Quiet room available on level 1.",
      refund_policy: "Sample policy: refunds available up to 14 days before the event.",
      booking_fee: "1.50",
      tax_name: "VAT",
      tax_rate: "20.00",
      prices_include_tax: true,
      contact_email: "hello@example.com",
      ticket_types: [
        { id: 1, name: "Standard", description: "Both days, all talks.", price: "180.00", available: 42, sale_state: "on_sale" },
        { id: 2, name: "Student", description: "Valid student ID required at entry.", price: "60.00", available: 0, sale_state: "sold_out" },
        { id: 3, name: "Community", description: "Free tickets for community volunteers.", price: "0.00", available: null, sale_state: "not_yet_on_sale" },
      ],
      sessions: [
        { id: 1, title: "Opening remarks", kind: "keynote", speakers: ["Sample Speaker"], room: "Main hall", starts_at: "2026-11-19T09:00:00Z", ends_at: "2026-11-19T09:30:00Z", description: "" },
        { id: 2, title: "Designing calm software", kind: "talk", speakers: ["A. Example", "B. Example"], room: "Main hall", starts_at: "2026-11-19T09:45:00Z", ends_at: "2026-11-19T10:30:00Z", description: "A placeholder talk description." },
        { id: 3, title: "Hands-on accessibility audit", kind: "workshop", speakers: ["C. Example"], room: "Room 2", starts_at: "2026-11-19T11:00:00Z", ends_at: "2026-11-19T12:30:00Z", description: "" },
        { id: 4, title: "Lunch", kind: "break", speakers: [], room: "Foyer", starts_at: "2026-11-19T12:30:00Z", ends_at: "2026-11-19T13:30:00Z", description: "" },
        { id: 5, title: "Closing panel", kind: "panel", speakers: ["D. Example", "E. Example"], room: "Main hall", starts_at: "2026-11-20T16:00:00Z", ends_at: "2026-11-20T17:00:00Z", description: "" },
      ],
    },
    {
      id: 102,
      name: "Civic Data Day",
      slug: "civic-data-day",
      summary: "A one-day gathering on open data in local government. (Sample event)",
      starts_at: "2026-12-05T15:00:00Z",
      ends_at: "2026-12-05T23:00:00Z",
      timezone: "America/Chicago",
      venue_name: "Example Library",
      status: "published",
      currency: "USD",
      public_url: "",
      description: "This is a sample event in the Open Conference Platform demo.",
      venue_address: "100 Sample Ave, Chicago",
      accessibility_info: "",
      refund_policy: "",
      booking_fee: "0.00",
      tax_name: "",
      tax_rate: "0.00",
      prices_include_tax: false,
      contact_email: "civic@example.com",
      ticket_types: [
        { id: 4, name: "General admission", description: "", price: "25.00", available: 120, sale_state: "on_sale" },
      ],
      sessions: [
        { id: 6, title: "Welcome", kind: "talk", speakers: ["Sample Host"], room: "Auditorium", starts_at: "2026-12-05T15:00:00Z", ends_at: "2026-12-05T15:20:00Z", description: "" },
      ],
    },
  ];
}

export function demoPublicEvents() {
  return {
    results: eventDetails().map(
      ({ id, name, slug, summary, starts_at, ends_at, timezone, venue_name, status, currency, public_url }) => ({
        id, name, slug, summary, starts_at, ends_at, timezone, venue_name, status, currency, public_url,
      }),
    ),
  };
}

export function demoEventDetail(slug: string): EventDetail {
  const found = eventDetails().find((e) => e.slug === slug);
  if (!found) throw new ApiError(404, "This event isn't available.", "not_found");
  return found;
}

export function demoOrgEvents(org: string): { results: OrgEvent[] } {
  const [a, b] = demoPublicEvents().results as [EventSummary, EventSummary];
  if (org === "sample-volunteers") {
    return { results: [{ ...b, capabilities: ["check_in"], manage_url: "", scanner_url: "" }] };
  }
  return {
    results: [
      {
        ...a,
        capabilities: ["manage_org", "manage_team", "manage_events", "view_attendees", "edit_attendees", "send_comms", "view_reports", "refund", "check_in"],
        manage_url: "",
        scanner_url: "",
      },
      { ...b, status: "draft", capabilities: ["manage_events", "view_attendees", "check_in"], manage_url: "", scanner_url: "" },
    ],
  };
}

export function demoDashboard(eventId: string): Dashboard {
  return {
    event_id: eventId,
    currency: "GBP",
    tickets_issued: 128,
    checked_in: 0,
    money: { revenue: "21600.00", discounts: "540.00", fees: "192.00", collected: "21252.00", refunds: "360.00", net: "20892.00", tax: "3482.00" },
  };
}

function paginate<T>(rows: T[], page: number): Paginated<T> {
  const size = 50;
  const start = (page - 1) * size;
  return { results: rows.slice(start, start + size), count: rows.length, page, page_size: size, has_next: start + size < rows.length };
}

const FIRST = ["Alex", "Sam", "Jordan", "Riley", "Casey", "Morgan", "Taylor", "Jamie"];
const LAST = ["Example", "Sample", "Placeholder", "Demo"];

export function demoOrders(page: number, status?: string) {
  const statuses = ["paid", "paid", "paid", "pending", "refunded", "paid", "cancelled"];
  const rows = Array.from({ length: 64 }, (_, i) => ({
    id: 5000 + i,
    number: `S-${(1000 + i).toString()}`,
    purchaser_first_name: FIRST[i % FIRST.length]!,
    purchaser_last_name: LAST[i % LAST.length]!,
    purchaser_email: `buyer${i + 1}@example.com`,
    status: statuses[i % statuses.length]!,
    total: i % 5 === 0 ? "60.00" : "180.00",
    refunded_total: statuses[i % statuses.length] === "refunded" ? "180.00" : "0.00",
    currency: "GBP",
    created_at: new Date(Date.UTC(2026, 8, 1 + (i % 28), 10, i % 60)).toISOString(),
  }));
  return paginate(status ? rows.filter((r) => r.status === status) : rows, page);
}

export function demoAttendees(page: number, q?: string): Paginated<Attendee> {
  const rows: Attendee[] = Array.from({ length: 72 }, (_, i) => ({
    id: 9000 + i,
    first_name: FIRST[i % FIRST.length]!,
    last_name: LAST[(i + 1) % LAST.length]!,
    email: `attendee${i + 1}@example.com`,
    ticket_type__name: i % 5 === 0 ? "Student" : "Standard",
    order__number: `S-${1000 + Math.floor(i / 1.2)}`,
    ticket__status: "valid",
    ticket__checked_in_at: null,
  }));
  const needle = q?.trim().toLowerCase();
  const filtered = needle
    ? rows.filter((r) => `${r.first_name} ${r.last_name} ${r.email} ${r.order__number}`.toLowerCase().includes(needle))
    : rows;
  return paginate(filtered, page);
}

export function demoCommunications(page: number): Paginated<Communication> {
  return paginate(
    [
      { id: 1, subject: "Your ticket for Northwind Developer Summit", kind: "confirmation", status: "sent", scheduled_for: null, sent_at: "2026-09-02T09:00:00Z", recipient_count: 128 },
      { id: 2, subject: "Venue and travel information", kind: "announcement", status: "scheduled", scheduled_for: "2026-11-12T09:00:00Z", sent_at: null, recipient_count: 128 },
      { id: 3, subject: "Speaker briefing", kind: "announcement", status: "draft", scheduled_for: null, sent_at: null, recipient_count: 0 },
    ],
    page,
  );
}

