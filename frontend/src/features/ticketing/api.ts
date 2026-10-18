import { keepPreviousData, queryOptions } from "@tanstack/react-query";

import { load } from "@/shared/api/client";
import type { Order, Paginated } from "@/shared/api/types";
import { demoOrders } from "@/shared/demo/fixtures";
import type { AppMode } from "@/shared/mode";
import { orgApiBase } from "@/features/organizations/api";

export const ORDER_STATUSES = ["pending", "paid", "failed", "expired", "cancelled", "partially_refunded", "refunded"] as const;

export function ordersQuery(mode: AppMode, org: string, eventId: string, page: number, status?: string) {
  const params = new URLSearchParams({ page: String(page) });
  if (status) params.set("status", status);
  return queryOptions({
    queryKey: [mode, "org", org, "event", eventId, "orders", page, status ?? ""],
    queryFn: () => load<Paginated<Order>>(`${orgApiBase(org, eventId)}/orders/?${params}`, () => demoOrders(page, status)),
    placeholderData: keepPreviousData,
  });
}

