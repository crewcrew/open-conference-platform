import { QueryClient } from "@tanstack/react-query";
import { createRouter, rootRouteId } from "@tanstack/react-router";
import { describe, expect, it } from "vitest";

import { routeTree } from "@/routeTree.gen";

describe("App routing", () => {
  const router = createRouter({ routeTree, context: { queryClient: new QueryClient() } });
  it.each([
    ["/", "/"],
    ["/events/x", "/events/$slug"],
    ["/login", "/login"],
    ["/manage/acme/events/1/orders", "/manage/$orgSlug/events/$eventId/orders"],
    ["/manage/acme/events/1/checkin", "/manage/$orgSlug/events/$eventId/checkin"],
  ])("matches %s", (path, id) => {
    const last = router.matchRoutes(path).at(-1)?.routeId;
    expect(last).not.toBe(rootRouteId);
    expect(last?.replace(/\/$/, "") || "/").toBe(id);
  });
});


