# Frontend API v1

Base: the configured Django origin plus `/api/v1/`. Every endpoint has a trailing slash. Use `credentials: 'include'`. JSON decimal amounts are strings, date/times are ISO 8601 in UTC, and event display uses the event's IANA `timezone`. Successful responses are JSON. Handle HTTP errors, including standard Django HTML CSRF/404 error responses, by status before parsing JSON.

## Authentication

- `GET session/` → `{authenticated, csrf_token, user: {name,email}|null, organizations: [{slug,name,role}]}`. Fetch before signing in.
- `POST auth/login/` with JSON `{email,password}` and `X-CSRFToken` → the session response with a new CSRF token. Invalid credentials return 400. All unsafe requests require CSRF; there are no CSRF exemptions in this API.
- `POST auth/logout/` with the latest `X-CSRFToken` → `{ok:true}`.

No auth tokens belong in localStorage. Keep the CSRF token in memory. Passwords are only used for the login POST. The proxy must rate-limit authentication and booking lookup; an example is in `deploy/nginx.conf.example`.

## Events

- `GET events/` → `{results:[{id,name,slug,summary,starts_at,ends_at,timezone,venue_name,status,currency,public_url}]}`. At most 100 published public events. Unlisted events appear only by direct slug, and drafts are never public.
- `GET events/:slug/` → event plus `description, venue_address, accessibility_info, refund_policy, booking_fee, tax_name, tax_rate, prices_include_tax, contact_email`, `ticket_types:[{id,name,description,price,available,sale_state}]`, and `sessions:[{id,title,kind,speakers,room,starts_at,ends_at,description}]`. Hidden ticket types and access codes are excluded. Navigate to `public_url` for ticket selection and checkout; the API does not reserve inventory. `available` is a snapshot and checkout revalidates it.
- `GET organizations/:orgSlug/events/` → `{results:[event plus capabilities: string[], manage_url, scanner_url]}`. At most 100 events. Requires authentication and membership. Volunteers see only their assigned events. Capabilities come from the backend; hide unavailable actions in the frontend.

## Event operations data

Prefix: `organizations/:orgSlug/events/:eventId/`.

| Endpoint | Capability | Response |
| --- | --- | --- |
| `dashboard/` | `view_reports` | `{event_id,currency,tickets_issued,checked_in,money:{revenue,discounts,fees,collected,refunds,net,tax,orders}}` |
| `orders/?page=1&status=paid` | `view_attendees` | Rows: `id,number,purchaser_first_name,purchaser_last_name,purchaser_email,status,total,refunded_total,currency,created_at` |
| `attendees/?page=1&q=search` | `view_attendees` | Rows: `id,first_name,last_name,email,ticket_type__name,order__number,ticket__status,ticket__checked_in_at` |
| `communications/?page=1` | `send_comms` | Rows: `id,subject,kind,status,scheduled_for,sent_at,recipient_count` |

Lists use `{results,count,page,page_size:50,has_next}`. A nonnumeric page returns 400. Authentication failures return 401, missing tenant membership returns 404, and insufficient capability returns 403. Capabilities are enforced server-side for every endpoint. API responses use `Cache-Control: no-store` and vary by Origin/Cookie. Booking access tokens and QR codes are excluded from organizer API responses.

Write workflows use full browser navigation to Django pages: `/manage/:orgSlug/e/:eventId/` followed by `edit/`, `sessions/`, `tickets/`, `questions/`, `coupons/`, `orders/`, `attendees/`, `emails/`, `reports/`, or `history/`. Team and settings live at `/manage/:orgSlug/team/` and `/manage/:orgSlug/settings/`. Scanner: `/checkin/:eventId/`. Use backend absolute URLs so existing session and CSRF protection remain in force.
