# Open Conference Platform — frontend

Open-source (MIT), **self-hosted** conference software. Source: https://github.com/crewcrew/open-conference-platform This repository is the web frontend; the Django conference backend is the source of truth for all business logic, payments, accounts and writes.

The public Lovable deployment is **only an interactive product demo** with clearly labeled sample data. It is not a hosted conference service: nothing is bought, emailed, saved or checked in there.

## Two modes

| Mode | When | Behaviour |
| --- | --- | --- |
| **Demo** (default) | `VITE_OCP_API_URL` unset | Sample events, attendee pages and an organizer workspace (owner and volunteer roles). No network calls to any backend; no real accounts, payments or emails. Management actions are shown as non-interactive controls with a plain explanation. |
| **Live** (self-hosted) | `VITE_OCP_API_URL` set | Talks only to your Django backend. Never shows sample data — errors (401/403/404/network) are shown as errors, not replaced by fixtures. |

Mode is derived purely from build-time env, so server rendering, hydration, direct links and reloads always agree.

## Configuration

| Variable | Meaning |
| --- | --- |
| `VITE_OCP_API_URL` | Your Django **origin**, without `/api/v1`, e.g. `https://api.example.com`. Setting it switches to live mode. |
| `VITE_OCP_REPO_URL` | Optional override for forks. Defaults to the canonical repository `https://github.com/crewcrew/open-conference-platform`; "View source / Self-host" links to the repo root and "Download source" to `/archive/refs/heads/main.zip`. Invalid values fall back to the default. |

`VITE_` values are baked in at build time — rebuild after changing them.

## Self-hosting with your Django backend

Serve the frontend and Django on sibling subdomains of one domain, e.g. `app.example.com` and `api.example.com`, so session and CSRF cookies are same-site.

Django already implements exact-origin, credentialed CORS in its own middleware (no extra CORS package):

```bash
OCP_FRONTEND_ORIGINS=https://app.example.com
OCP_CSRF_TRUSTED_ORIGINS=https://app.example.com
```

Production cookies default to `Secure` + `SameSite=Lax`, correct for sibling domains. For a cross-site frontend you can set `OCP_SESSION_COOKIE_SAMESITE=None`, but browsers that block third-party cookies may still prevent sign-in.

### Auth & security (live mode)

- `GET /api/v1/session/` → session + CSRF token, kept **in memory only**.
- Login fetches a fresh session, then `POST /api/v1/auth/login/` with `X-CSRFToken`; logout `POST /api/v1/auth/logout/`.
- No passwords or tokens in browser storage; all requests use `credentials: "include"`.
- The demo stores only the chosen sample role (`owner`/`volunteer`) in sessionStorage — never credentials.

## Boundary: frontend vs Django

| In this frontend (read-only) | On Django (full-page navigation in live mode) |
| --- | --- |
| Public event list/detail, tickets, schedule in event timezone | Checkout (`public_url`), `/booking/`, `/accounts/signup/` |
| Organizer workspace: events, dashboard figures, orders (status filter), attendees (search), communications | Org create/settings/team, new event, event edit/sessions/tickets/questions/coupons/orders/attendees/emails/reports/history, order detail & refunds, check-in `/checkin/:id/` |

### Permissions

- Org links follow the membership role: `manage_org` (settings) = owner; `manage_team` = owner, admin; `manage_events` (new event) = owner, admin, event_manager — even with zero events. Volunteers get none.
- Event screens use each event's `capabilities`. Volunteers (only `check_in`) see their assigned events and the check-in station — no finance, attendee or report UI.
- Order statuses: pending, paid, failed, expired, cancelled, partially_refunded, refunded.

## Source layout

`src/features/{auth,organizations,events,schedule,ticketing,attendees,communications,reports,checkin}` — feature UI and queries. `src/shared` — config (backend + repo metadata), API client, types, capability rules, Django link builders, shared UI, demo fixtures. `src/routes` — thin route files.

## Development

```bash
bun install
bun run dev        # demo mode
bun run test
bun run build
```

## License

MIT.

