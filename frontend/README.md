# Open Conference Platform — frontend

A frontend for an existing Django conference management backend. **Django stays the source of truth**: all business logic, payments, checkout, refunds, check-in and every write operation remain on Django. This app reads from the JSON API and links to Django server pages for everything else.

## Configuration

| Variable | Required | Meaning |
| --- | --- | --- |
| `VITE_OCP_API_URL` | yes (live) | Django **origin**, without `/api/v1`. e.g. `https://api.example.com` |
| `VITE_OCP_DEMO_MODE` | no | `true` forces the labeled sample-data preview when no backend is set. Never use in production. |

```bash
# .env.production
VITE_OCP_API_URL=https://api.example.com
```

Values are baked in at build time (`VITE_` prefix) — rebuild after changing them. Without `VITE_OCP_API_URL` the site shows an honest **"Backend connection required"** screen with an opt-in, clearly labeled preview (fixtures only; nothing can be bought, changed or checked in; figures are fake).

## Recommended hosting: sibling subdomains

Serve the frontend and Django on sibling subdomains of one registrable domain, e.g. `app.example.com` and `api.example.com`. Requests are then **same-site**, so Django's session and CSRF cookies are sent reliably with `credentials: "include"` — including in browsers that block third-party cookies. Cross-site deployments (e.g. `*.lovable.app` → `api.example.com`) will be unreliable for login.

### Django settings

The backend already implements exact-origin, credentialed CORS in its own middleware — **do not add django-cors-headers**. Configure via environment:

```bash
OCP_FRONTEND_ORIGINS=https://app.example.com
OCP_CSRF_TRUSTED_ORIGINS=https://app.example.com
```

Production cookie defaults are `Secure` and `SameSite=Lax`, which work for sibling custom domains (preferred). For a cross-site frontend such as `*.lovable.app`, set `OCP_SESSION_COOKIE_SAMESITE=None`; this still depends on the browser allowing third-party cookies (Safari and privacy-focused browsers often block them), so sign-in may fail there.

## Auth & security

- `GET /api/v1/session/` provides the session and CSRF token; the token is kept **in memory only**.
- Login fetches a fresh session, then `POST /api/v1/auth/login/` with `X-CSRFToken`; the rotated token replaces the old one. Logout posts to `/api/v1/auth/logout/`.
- Passwords and tokens are never written to browser storage. All requests use `credentials: "include"`.
- 401 → sign-in prompt; 403 → "no access"; 404 → not found; network failures → retryable message. Backend `{error}` messages are shown.

## Boundary: what lives where

| In this frontend (read-only) | On Django (full-page navigation) |
| --- | --- |
| Public event list and detail, tickets, schedule (event timezone) | Checkout (`public_url`), booking lookup `/booking/`, signup `/accounts/signup/` |
| Organizer workspace: org/event lists, dashboard figures, orders, attendees, communications | Create/edit org (`/manage/new/`, `/manage/:org/settings/`), team, new event, event edit/sessions/tickets/questions/coupons/orders/attendees/emails/reports/history, order detail & refunds, check-in `/checkin/:id/` |

Links are shown only when the event's `capabilities` allow them. Volunteers (only `check_in`) see their assigned events and the check-in station — no finance, attendee or report UI. Org-level links follow the membership role exactly: `manage_org` (settings) = owner; `manage_team` (team) = owner or admin; `manage_events` (new event) = owner, admin or event_manager — including organizations with no events yet. Volunteers have no org management links. Event-specific UI always uses the event's `capabilities`.

## Source layout

`src/features/{auth,organizations,events,schedule,ticketing,attendees,communications,reports,checkin}` — feature UI and queries. `src/shared` — API client, types, config, formatting, capability rules, Django link builders, shared UI, preview fixtures. `src/routes` — thin route files.

## Development

```bash
bun install
bun run dev
bun run test     # smoke + rule tests
bun run build
```

