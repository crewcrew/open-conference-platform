import type { Capability, OrgEvent, OrgMembership } from "./api/types";

export type EventNavKey = "overview" | "orders" | "attendees" | "communications" | "checkin";

export const EVENT_NAV: { key: EventNavKey; label: string; requires: Capability | null }[] = [
  { key: "overview", label: "Overview", requires: null },
  { key: "orders", label: "Orders", requires: "view_attendees" },
  { key: "attendees", label: "Attendees", requires: "view_attendees" },
  { key: "communications", label: "Communications", requires: "send_comms" },
  { key: "checkin", label: "Check-in", requires: "check_in" },
];

export function eventNavFor(caps: readonly Capability[]) {
  return EVENT_NAV.filter((n) => n.requires === null || caps.includes(n.requires));
}

export function can(event: Pick<OrgEvent, "capabilities"> | undefined, cap: Capability) {
  return !!event && event.capabilities.includes(cap);
}

export type OrgCapability = Extract<Capability, "manage_org" | "manage_team" | "manage_events">;

/** Exact Django org role permissions. Event-specific UI uses event.capabilities instead. */
export const ORG_ROLE_CAPABILITIES: Record<string, readonly OrgCapability[]> = {
  owner: ["manage_org", "manage_team", "manage_events"],
  admin: ["manage_team", "manage_events"],
  event_manager: ["manage_events"],
  volunteer: [],
};

export function orgCan(membership: Pick<OrgMembership, "role"> | undefined, cap: OrgCapability) {
  if (!membership) return false;
  return (ORG_ROLE_CAPABILITIES[membership.role.toLowerCase()] ?? []).includes(cap);
}

