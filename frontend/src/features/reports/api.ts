import { queryOptions } from "@tanstack/react-query";

import { load } from "@/shared/api/client";
import type { Dashboard } from "@/shared/api/types";
import { demoDashboard } from "@/shared/demo/fixtures";
import type { AppMode } from "@/shared/mode";
import { orgApiBase } from "@/features/organizations/api";

export function dashboardQuery(mode: AppMode, org: string, eventId: string, enabled: boolean) {
  return queryOptions({
    queryKey: [mode, "org", org, "event", eventId, "dashboard"],
    queryFn: () => load<Dashboard>(`${orgApiBase(org, eventId)}/dashboard/`, () => demoDashboard(eventId)),
    enabled,
  });
}

