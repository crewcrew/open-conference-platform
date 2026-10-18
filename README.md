# Open Conference Platform

A self-hosted, MIT-licensed platform for running a conference end to end. Organizers publish an event, sell or give away tickets, email attendees, handle refunds, and check people in at the door. Attendees register, pay on the payment provider's page, and get QR tickets.

**Try the product:** the [Lovable project](https://lovable.dev/projects/88bb01cd-8796-44d3-a3ce-f9778240175e) hosts an interactive sample-data demo. It is a product showcase; it does not accept real registrations, process payments or send email. A public demo URL will be added when it is published.

**Run your own copy:** download this repository or clone it, then follow the quickstart below. The Django application includes the full attendee and organizer experience, so you can use it without Lovable or a separate JavaScript frontend. The optional frontend source is included in `frontend/`.

## Download

Use GitHub's **Code → Download ZIP**, extract it, and open the project directory. With Git installed:

```bash
git clone https://github.com/crewcrew/open-conference-platform.git
cd open-conference-platform
```

## Run it locally

You need Python 3.10 or later.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env            # then set OCP_SECRET_KEY and OCP_DEMO_PASSWORD
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
```

On Windows, use `.venv\Scripts\python` and `.venv\Scripts\pip` in place of the `.venv/bin/` commands.

`seed_demo` creates **Fieldwork 2027**, a fictional two-day conference with sessions, four ticket types, coupons, about 30 orders, a bounced email, a refund request and a partial refund. The four demo accounts all use the password in `OCP_DEMO_PASSWORD`:

| Email | Role |
|---|---|
| alex@fieldwork.example | Owner |
| priya@fieldwork.example | Administrator |
| tomasi@fieldwork.example | Event manager |
| jo@fieldwork.example | Check-in volunteer (assigned to Fieldwork 2027) |

Then open:

- `/e/fieldwork-2027/`: the public event page. Add `?code=CREW27` to see the hidden crew ticket.
- `/manage/`: the organizer pages.
- `/checkin/1/`: the check-in scanner. It works on a phone over HTTPS. Camera access needs HTTPS or localhost.

Emails print to the terminal running `runserver`. Payments use the built-in **test provider**: its page has *Pay successfully* and *Decline* buttons, never asks for card details, and only exists while `OCP_PAYMENT_PROVIDER=test`.

Run the tests:

```bash
.venv/bin/python manage.py test tests
```

## What's in it

| Area | What works |
|---|---|
| Organisations and access | Sign-up creates an organisation and its owner. Invite people as Owner, Administrator, Event manager or Check-in volunteer. Volunteers only reach the events they're assigned to. People outside an organisation get a 404. |
| History | Changes to events, tickets, coupons, sessions, team, attendees and refunds are recorded with who and what changed. |
| Event setup | Create, edit, preview, publish, unpublish, cancel and duplicate an event. Public or unlisted. Multi-day schedule with sessions, rooms and capacities. Pick-one session groups (for example a choice of workshops). |
| Time zones | Times are stored in UTC and always shown in the event's zone with its label, e.g. "NZDT (UTC+13)". Organizer forms take venue-local times. |
| Tickets | Multiple ticket types with price, quantity, sale window, per-order limits, session access, and hidden types unlocked by an access code. Free and paid. |
| No overselling | Checkout holds places for a set time (15 minutes by default) using conditional database updates, so two buyers can't both get the last place. Expired holds are released. A payment that arrives after its places have gone is refunded automatically. |
| Checkout | Group orders with per-attendee details and session choice. Purchaser details are separate from attendees. Booking fee, tax and refund policy are shown before paying. Configurable questions. Separate opt-in for marketing. |
| Orders and tickets | Order statuses: pending, paid, failed, expired, cancelled, part refunded, refunded. Each attendee gets a unique ticket with a non-guessable QR code. Tickets are issued once, on confirmed payment, even if the provider calls back twice. |
| Payments | Provider interface with two providers: the built-in test provider and Stripe Checkout (hosted page, signed webhooks, refunds). Card details never touch the platform. |
| Coupons | Percentage or fixed amount, chosen ticket types, start and end dates, use limit, one per order, disable without losing history, uses listed per coupon. |
| Refunds | Cancel some or all tickets with a full, policy-based, custom or zero refund, behind a confirm step. Attendees can request cancellation from their booking link. Failed refunds are flagged and can be retried. |
| Email | Confirmations, per-attendee tickets, cancellations, booking-link lookup, organizer updates to everyone or a filtered group, and scheduled reminders. Every send is logged; failures show on the dashboard and can be resent to a corrected address without new tickets. Email backend is configurable. |
| Attendees | Search and filter by ticket type, session, order status and attendance. Edit with history. Resend tickets. Desk check-in. |
| Check-in | Mobile web scanner using the camera (BarcodeDetector, with a jsQR fallback). Typed or hardware-scanner codes also work. Clear admitted / already checked in / not valid results. Name search fallback. Offline scans are saved in the browser and synced later, each recorded exactly once. |
| Dashboard and reports | Tickets issued, remaining capacity, check-ins, weekly registrations, ticket sales, discounts, booking fees, refunds, tax and net. Filter by ticket type, status and date. |
| Exports | Orders, attendees and attendance as CSV, with times in the event's zone. |
| Calendar | `.ics` download for each event. |
| Data retention | `purge_personal_data` removes names, emails and answers once an event's retention period has passed. Totals are kept. |

Ten core acceptance scenarios have automated coverage in `tests/test_acceptance.py`.

## Not built yet

Planned features and current limitations:

- General write APIs and outgoing webhooks (API-01 to API-04). The versioned frontend read/session API is now available; rate limiting is configured at the reverse proxy.
- Session-level check-in at the door (CHK-06). The data model supports it.
- Recurring events, seat maps, ticket variations, add-ons, bundles, donations, waitlists, ticket transfers, invoices.
- Bulk coupon codes, CSV attendee import, email template designer, SMS.
- Multi-language interface.
- Password reset by email. Signed-in users can change their password at `/accounts/password/`. Until reset is built, an operator can reset a password with `manage.py changepassword`.
- The Stripe provider is implemented against Stripe's documented API, and its signature checks are tested. It has **not** been run against a live Stripe account.

## Deploying

- Set `OCP_DEBUG=0`, a long random `OCP_SECRET_KEY`, `OCP_ALLOWED_HOSTS`, `OCP_BASE_URL` and `OCP_CSRF_TRUSTED_ORIGINS`.
- For real traffic, use PostgreSQL (`OCP_DATABASE_URL=postgres://…`, then `pip install "psycopg[binary]"`). SQLite remains available locally with WAL and immediate transactions. The guarded production settings require PostgreSQL.
- Serve over HTTPS behind a reverse proxy. Set `OCP_BEHIND_PROXY=1` if the proxy terminates TLS. Turn on HSTS with `OCP_HSTS_SECONDS` once HTTPS is confirmed.
- The container collects and serves static assets with WhiteNoise and runs Gunicorn (`ocp.wsgi`). See the production runbook for the release migration and worker processes.
- Run `manage.py process_outbox` every minute from cron. It sends scheduled emails and frees expired holds. Run `manage.py purge_personal_data` daily.
- Set the email settings (`OCP_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` and `OCP_EMAIL_HOST…`).
- For Stripe: set `OCP_PAYMENT_PROVIDER=stripe`, `OCP_STRIPE_SECRET_KEY` and `OCP_STRIPE_WEBHOOK_SECRET`. Point a webhook at `/payments/webhook/stripe/` for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired` and `refund.updated`.
- Back up the database. Everything else can be rebuilt from the code.
- The scanner loads jsQR from cdn.jsdelivr.net on browsers without BarcodeDetector, such as iOS Safari. Fonts come from Google Fonts unless `OCP_GOOGLE_FONTS=0`. Self-host both if your privacy policy needs it.

## Layout

Each feature owns its forms, views, templates and API adapters. Django app labels and migrations retain their existing identities so databases remain compatible.

```
ocp/accounts/   organisations, memberships, roles, auth, invitations, audit
ocp/events/     event setup, sessions, ticket types, questions, public event API
ocp/ticketing/  orders, attendees, coupons, refunds, payment and inventory rules
ocp/checkin/    scanner views, check-in rules and scanner JavaScript
ocp/comms/      email services, messages, delivery records and email templates
ocp/reports/    dashboard, financial summaries, reports and history
ocp/public/     attendee event, checkout, booking and ticket pages
ocp/organizer/  shared organizer shell, permissions decorator, URL routing, demo seed
ocp/core/       shared templates/styles, API utilities, CORS and health endpoints
ocp/settings/   base/local and guarded production configuration
frontend/      Lovable frontend source snapshot, organized by feature
deploy/        Gunicorn, proxy and environment examples
docs/          frontend API contract and deployment runbook
tests/         acceptance, service, API and production configuration tests
```

## Product demo and self-hosting

Lovable is used to demonstrate the product with fictional data. It does not need a centrally hosted Django backend. Explore the attendee pages, organizer workspace and volunteer permissions, then download the source to run your own installation. Demo actions never create real accounts, charge money or send messages.

The optional frontend is developed in [Lovable](https://lovable.dev/projects/88bb01cd-8796-44d3-a3ce-f9778240175e), with a source snapshot under [`frontend/`](frontend/README.md). Feature modules live in `frontend/src/features/`. The local snapshot is not automatically synchronized with Lovable. Self-hosters may connect it to their own Django instance; Django owns authentication, inventory, payments and organizer changes.

For your own production installation, see [the deployment guide](docs/production.md), including optional Docker/Compose and Railway configurations. The [frontend API contract](docs/api.md) describes session authentication, CORS and feature endpoints. Production uses `DJANGO_SETTINGS_MODULE=ocp.settings.production`; local commands use `ocp.settings`.

## Contributing and license

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and pull-request guidance, and [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

Released under the [MIT License](LICENSE). Third-party dependencies retain their own licenses.

## Project decisions still open

The build makes these assumptions. Each one is easy to change.

1. **Pilot and volumes**: unknown. Use PostgreSQL if checkout peaks above a few dozen buyers a minute.
2. **Hosting**: self-hosted Django app.
3. **Payments**: provider-agnostic; Stripe adapter included. Merchant of record not decided. Booking fees aren't refunded.
4. **Session choice**: at checkout. Organizers can change it afterwards.
5. **Offline scanning**: built in, because it costs little.
6. **Refund approval**: Owners and Administrators only. Policy dates suggest an amount, which can be overridden.
7. **Privacy jurisdiction and retention**: retention is set per event. The jurisdiction still needs choosing.
8. **Transfers, waitlists, invoices, sponsor registration**: not built.
9. **Governance**: MIT licensed; contribution workflow is documented in CONTRIBUTING.md. Longer-term project governance is still open.
