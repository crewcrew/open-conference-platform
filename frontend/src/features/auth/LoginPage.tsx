import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";

import { buttonVariants } from "@/components/ui/button";
import { toApiError } from "@/shared/api/client";
import { backendUrl, djangoPaths } from "@/shared/backend-links";
import { useMode } from "@/shared/mode";
import { PublicShell } from "@/shared/ui/public-shell";
import { LoadingState } from "@/shared/ui/states";
import { DemoEntry } from "./DemoEntry";
import { login, sessionQuery, useSession } from "./api";

export function LoginPage({ redirect }: { redirect?: string | undefined }) {
  const mode = useMode();
  const session = useSession();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const target = redirect && redirect.startsWith("/manage") ? redirect : "/manage";

  useEffect(() => {
    if (mode === "live" && session.data?.authenticated) navigate({ to: target, replace: true });
  }, [mode, session.data?.authenticated, navigate, target]);


  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const next = await login(email, password);
      setPassword("");
      if (!next.authenticated) {
        setError("Sign-in didn't complete. Check your details and try again.");
        return;
      }
      qc.setQueryData(sessionQuery(mode).queryKey, next);
      navigate({ to: target, replace: true });
    } catch (err) {
      const apiErr = toApiError(err);
      setError(
        apiErr.kind === "network"
          ? apiErr.message
          : apiErr.status === 400 || apiErr.status === 401
            ? apiErr.message || "Email or password is incorrect."
            : apiErr.message,
      );
    } finally {
      setBusy(false);
    }
  }

  const signup = backendUrl(djangoPaths.signup());
  if (mode === "demo") return <DemoEntry target={target} />;

  return (
    <PublicShell>
      <div className="mx-auto max-w-md px-4 py-16">
        <p className="eyebrow">Organizer workspace</p>
        <h1 className="mt-2 text-3xl font-semibold">Sign in</h1>
        {session.isPending ? (
          <LoadingState />
        ) : (
          <form onSubmit={onSubmit} className="panel mt-8 space-y-5 p-6" noValidate>
            {error && (
              <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
            )}
            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium">Email</label>
              <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-input bg-card px-3 py-2" />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium">Password</label>
              <input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-input bg-card px-3 py-2" />
            </div>
            <button type="submit" className={buttonVariants({ className: "w-full" })} disabled={busy || !email || !password}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
        )}
        <p className="mt-6 text-sm text-muted-foreground">
          New organizer?{" "}
          {signup && <><a href={signup} className="text-primary underline underline-offset-2">Create an account</a>{" · "}</>}
          <Link to="/" className="underline underline-offset-2">Back to events</Link>
        </p>
      </div>
    </PublicShell>
  );
}

