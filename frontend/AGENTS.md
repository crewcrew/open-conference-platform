<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture rules
- Django is the source of truth; the frontend only reads `/api/v1/` and links (full-page) to Django pages for every write — no pretend forms.
- Source is organized by feature under `src/features/*`; API client, types, link builders and shared UI live in `src/shared`; route files stay thin.
- All backend data is fetched client-side with `credentials: "include"` (cookies live on the backend origin), so `/manage` and `/login` use `ssr: false`.
- CSRF token is held in memory only (`src/shared/api/csrf.ts`); never persist credentials or tokens.
- Data loaders go through `load()` so preview mode uses fixtures and live mode never does; query keys start with the mode.
- Capability-based visibility rules live in `src/shared/capabilities.ts` and `src/shared/backend-links.ts` and are covered by tests.

