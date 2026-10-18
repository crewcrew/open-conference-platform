This folder is an exported source snapshot from Lovable, not an automatically
synchronized repository. Preserve published history and deliberately export any
subsequent Lovable changes into this folder before releasing them.

## Architecture rules
- Product is MIT open-source, self-hosted software; the Lovable deployment is a public interactive demo only, never a hosted service — don't add hosted-backend setup to visitor pages.
- Mode is derived from build-time env only (`src/shared/mode.ts`): no `VITE_OCP_API_URL` → demo, set → live; keeps SSR, hydration and reloads consistent.
- Live mode never falls back to fixtures; all data goes through `load()` and query keys start with the mode.
- Django is the source of truth; the frontend only reads `/api/v1/` and links (full-page) to Django pages for every write — no pretend forms. In demo, those links render as non-interactive controls.
- Source is organized by feature under `src/features/*`; API client, config (backend + repository metadata), link builders and shared UI live in `src/shared`; route files stay thin.
- Repository links come from `PROJECT.repoUrl` in `src/shared/config.ts`, overridable by a validated `VITE_OCP_REPO_URL`; never render placeholder links.
- Backend data is fetched client-side with `credentials: "include"`, so `/manage` and `/login` use `ssr: false`.
- CSRF token is held in memory only; never persist credentials or tokens. Demo persists only the sample role choice.
- Permission rules live in `src/shared/capabilities.ts` and `src/shared/backend-links.ts` and are covered by tests.

