import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { OrdersPage, type OrdersSearch } from "@/features/ticketing/OrdersPage";
import { parsePage } from "@/shared/search";

export const Route = createFileRoute("/manage/$orgSlug/events/$eventId/orders")({
  validateSearch: (s: Record<string, unknown>): OrdersSearch => ({
    page: parsePage(s["page"]),
    status: typeof s["status"] === "string" && s["status"] ? s["status"] : undefined,
  }),
  component: OrdersRoute,
});

function OrdersRoute() {
  const { orgSlug, eventId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });
  return <OrdersPage orgSlug={orgSlug} eventId={eventId} search={search} onSearch={(next) => navigate({ search: next })} />;
}

