import { describe, expect, it } from "vitest";

import { djangoPaths, managementSectionsFor } from "../backend-links";
import { eventNavFor, orgCan } from "../capabilities";
import { ORDER_STATUSES } from "@/features/ticketing/api";
import { normalizeOrigin } from "../config";
import { formatMoney, formatTime } from "../format";

describe("roles and capabilities", () => {
  it("volunteers with only check_in see only overview and check-in", () => {
    expect(eventNavFor(["check_in"]).map((n) => n.key)).toEqual(["overview", "checkin"]);
  });
  it("volunteers get no finance, attendee or report management links", () => {
    expect(managementSectionsFor(["check_in"])).toEqual([]);
  });
  it("refund capability alone exposes the orders section", () => {
    expect(managementSectionsFor(["refund"]).map((s) => s.section)).toEqual(["orders"]);
  });
});

describe("organization role permissions", () => {
  const r = (role: string) => ({ role });
  it("manage_org is owner only", () => {
    expect(["owner", "admin", "event_manager", "volunteer"].filter((x) => orgCan(r(x), "manage_org"))).toEqual(["owner"]);
  });
  it("manage_team is owner or admin", () => {
    expect(["owner", "admin", "event_manager", "volunteer"].filter((x) => orgCan(r(x), "manage_team"))).toEqual(["owner", "admin"]);
  });
  it("manage_events is owner, admin or event_manager", () => {
    expect(["owner", "admin", "event_manager", "volunteer"].filter((x) => orgCan(r(x), "manage_events"))).toEqual(["owner", "admin", "event_manager"]);
  });
  it("no membership grants nothing", () => {
    expect(orgCan(undefined, "manage_events")).toBe(false);
  });
});

describe("order statuses", () => {
  it("filter offers the full Django status set", () => {
    expect([...ORDER_STATUSES]).toEqual(["pending", "paid", "failed", "expired", "cancelled", "partially_refunded", "refunded"]);
  });
});

describe("configuration and paths", () => {
  it("strips trailing slashes and a mistaken /api/v1 suffix", () => {
    expect(normalizeOrigin("https://api.example.com/api/v1/")).toBe("https://api.example.com");
  });
  it("Django paths keep trailing slashes", () => {
    expect(djangoPaths.order("acme", 7, 42)).toBe("/manage/acme/e/7/orders/42/");
    expect(djangoPaths.checkin(7)).toBe("/checkin/7/");
  });
});

describe("formatting", () => {
  it("formats session times in the event timezone", () => {
    expect(formatTime("2026-05-12T08:00:00Z", "Europe/London")).toBe("09:00");
  });
  it("formats decimal strings as currency", () => {
    expect(formatMoney("12.50", "EUR")).toContain("12.50");
  });
});

