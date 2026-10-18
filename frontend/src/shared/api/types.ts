export type Capability =
  | "manage_org"
  | "manage_team"
  | "manage_events"
  | "view_attendees"
  | "edit_attendees"
  | "send_comms"
  | "view_reports"
  | "refund"
  | "check_in";

export interface OrgMembership {
  slug: string;
  name: string;
  role: string;
}

export interface Session {
  authenticated: boolean;
  csrf_token: string;
  user: { name: string; email: string } | null;
  organizations: OrgMembership[];
}

export type Id = number | string;

export interface EventSummary {
  id: Id;
  name: string;
  slug: string;
  summary: string;
  starts_at: string;
  ends_at: string;
  timezone: string;
  venue_name: string;
  status: string;
  currency: string;
  public_url: string;
}

export interface TicketType {
  id: Id;
  name: string;
  description: string;
  price: string;
  available: number | boolean | null;
  sale_state: string;
}

export interface ScheduleSession {
  id: Id;
  title: string;
  kind: string;
  speakers: string[] | string;
  room: string;
  starts_at: string;
  ends_at: string;
  description: string;
}

export interface EventDetail extends EventSummary {
  description: string;
  venue_address: string;
  accessibility_info: string;
  refund_policy: string;
  booking_fee: string;
  tax_name: string;
  tax_rate: string;
  prices_include_tax: boolean;
  contact_email: string;
  ticket_types: TicketType[];
  sessions: ScheduleSession[];
}

export interface OrgEvent extends EventSummary {
  capabilities: Capability[];
  manage_url: string;
  scanner_url: string;
}

export interface Dashboard {
  event_id: Id;
  currency: string;
  tickets_issued?: number;
  checked_in?: number;
  money?: Partial<Record<"revenue" | "discounts" | "fees" | "collected" | "refunds" | "net" | "tax", string>>;
}

export interface Paginated<T> {
  results: T[];
  count: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface Order {
  id: Id;
  number: string;
  purchaser_first_name: string;
  purchaser_last_name: string;
  purchaser_email: string;
  status: string;
  total: string;
  refunded_total: string;
  currency: string;
  created_at: string;
}

export interface Attendee {
  id: Id;
  first_name: string;
  last_name: string;
  email: string;
  ticket_type__name: string;
  order__number: string;
  ticket__status: string;
  ticket__checked_in_at: string | null;
}

export interface Communication {
  id: Id;
  subject: string;
  kind: string;
  status: string;
  scheduled_for: string | null;
  sent_at: string | null;
  recipient_count: number;
}

