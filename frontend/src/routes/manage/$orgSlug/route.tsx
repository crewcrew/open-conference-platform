import { createFileRoute } from "@tanstack/react-router";

import { WorkspaceLayout } from "@/features/organizations/WorkspaceLayout";

export const Route = createFileRoute("/manage/$orgSlug")({
  component: OrgLayout,
});

function OrgLayout() {
  const { orgSlug } = Route.useParams();
  return <WorkspaceLayout orgSlug={orgSlug} />;
}

