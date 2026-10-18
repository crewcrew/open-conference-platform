import { Link, Navigate } from "@tanstack/react-router";
import { Building2 } from "lucide-react";

import { useSession } from "@/features/auth/api";
import { djangoPaths } from "@/shared/backend-links";
import { humanize } from "@/shared/format";
import { ManagementLink } from "@/shared/ui/management-link";
import { PublicShell } from "@/shared/ui/public-shell";
import { EmptyState } from "@/shared/ui/states";

export function OrgPickerPage() {
  const session = useSession();
  const orgs = session.data?.organizations ?? [];
  if (orgs.length === 1 && orgs[0]) return <Navigate to="/manage/$orgSlug" params={{ orgSlug: orgs[0].slug }} replace />;

  return (
    <PublicShell>
      <div className="mx-auto max-w-3xl px-4 py-14">
        <p className="eyebrow">Signed in as {session.data?.user?.name ?? session.data?.user?.email}</p>
        <h1 className="mt-2 text-3xl font-semibold">Choose an organization</h1>
        <div className="mt-8">
          {orgs.length === 0 ? (
            <EmptyState title="You're not part of an organization yet">
              <p>Create one to start running events, or ask an existing organization to invite you.</p>
              <div className="mt-5"><ManagementLink path={djangoPaths.newOrganization()} variant="default">Create organization in management</ManagementLink></div>
            </EmptyState>
          ) : (
            <>
              <ul className="panel divide-y">
                {orgs.map((o) => (
                  <li key={o.slug}>
                    <Link to="/manage/$orgSlug" params={{ orgSlug: o.slug }} className="flex items-center gap-3 p-4 hover:bg-muted focus-visible:bg-muted">
                      <Building2 className="size-5 text-muted-foreground" aria-hidden />
                      <span className="flex-1 font-medium">{o.name}</span>
                      <span className="text-sm text-muted-foreground">{humanize(o.role)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
              <div className="mt-6"><ManagementLink path={djangoPaths.newOrganization()}>Create another organization</ManagementLink></div>
            </>
          )}
        </div>
      </div>
    </PublicShell>
  );
}

