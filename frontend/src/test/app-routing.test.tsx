import { QueryClient } from "@tanstack/react-query";
import { createRouter, rootRouteId } from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { routeTree } from "@/routeTree.gen";
import { SetupScreen } from "@/shared/ui/setup-screen";

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

describe("Setup screen", () => {
  it("explains that a backend connection is required", () => {
    render(<SetupScreen />);
    expect(screen.getByRole("heading", { name: "Backend connection required" })).toBeInTheDocument();
  });
});

