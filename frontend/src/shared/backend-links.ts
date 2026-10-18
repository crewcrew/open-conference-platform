import { getBackendOrigin } from "./config";
import type { Capability, Id } from "./api/types";

const e = encodeURIComponent;

/** Django server page paths. These are full-page navigations on the backend origin. */
export const djangoPaths = {
  manageHome: () => "/manage/",
  newOrganization: () => "/manage/new/",
  orgSettings: (org: string) => `/manage/${e(org)}/settings/`,
  orgTeam: (org: string) => `/manage/${e(org)}/team/`,
  newEvent: (org: string) => `/manage/${e(org)}/events/new/`,
  eventDashboard: (org: string, id: Id) => `/manage/${e(org)}/e/${e(String(id))}/`,
  eventSection: (org: string, id: Id, section: string) =>
    `/manage/${e(org)}/e/${e(String(id))}/${section}/`,
  order: (org: string, id: Id, orderId: Id) =>
    `/manage/${e(org)}/e/${e(String(id))}/orders/${e(String(orderId))}/`,
  checkin: (id: Id) => `/checkin/${e(String(id))}/`,
  signup: () => "/accounts/signup/",
  bookingLookup: () => "/booking/",
};

/** Absolute URL on the backend, or null when no backend is configured. */
export function backendUrl(pathOrUrl: string | null | undefined): string | null {
  if (!pathOrUrl) return null;
  if (/^https?:\/\//.test(pathOrUrl)) return pathOrUrl;
  const origin = getBackendOrigin();
  if (!origin) return null;
  return `${origin}${pathOrUrl.startsWith("/") ? "" : "/"}${pathOrUrl}`;
}

export interface ManagementSection {
  section: string | null;
  label: string;
  description: string;
  /** Visible when the event grants ANY of these capabilities. */
  anyOf: Capability[];
}

export const MANAGEMENT_SECTIONS: ManagementSection[] = [
  { section: null, label: "Event dashboard", description: "Full management overview", anyOf: ["manage_events", "view_reports"] },
  { section: "edit", label: "Edit event details", description: "Name, dates, venue, policies", anyOf: ["manage_events"] },
  { section: "sessions", label: "Sessions & schedule", description: "Add or change sessions", anyOf: ["manage_events"] },
  { section: "tickets", label: "Ticket types", description: "Prices, quantities, sale windows", anyOf: ["manage_events"] },
  { section: "questions", label: "Registration questions", description: "Checkout questions", anyOf: ["manage_events"] },
  { section: "coupons", label: "Coupons", description: "Discount codes", anyOf: ["manage_events"] },
  { section: "orders", label: "Orders & refunds", description: "Order detail and refunds", anyOf: ["view_attendees", "refund"] },
  { section: "attendees", label: "Attendees", description: "Edit attendee details", anyOf: ["edit_attendees"] },
  { section: "emails", label: "Emails", description: "Compose and schedule messages", anyOf: ["send_comms"] },
  { section: "reports", label: "Reports & exports", description: "Financial and attendance reports", anyOf: ["view_reports"] },
  { section: "history", label: "History", description: "Audit log of changes", anyOf: ["manage_events"] },
];

export function hasAny(caps: readonly Capability[], anyOf: readonly Capability[]) {
  return anyOf.some((c) => caps.includes(c));
}

export function managementSectionsFor(caps: readonly Capability[]) {
  return MANAGEMENT_SECTIONS.filter((s) => hasAny(caps, s.anyOf));
}

