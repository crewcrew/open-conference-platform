# Railway launch

Optional deployment reference for people choosing to self-host on Railway. No shared backend or paid resources are provided by this project; the Lovable product demo runs independently on fictional sample data.

## Service layout

Use one Railway project with these services, in the same region:

| Service | Source | Configuration | Public domain |
| --- | --- | --- | --- |
| `Postgres` | Railway PostgreSQL service | Persistent volume and backups | No public TCP proxy needed |
| `web` | This workspace's backend | `/railway.json` | Yes, backend HTTPS domain |
| `worker` | Same backend source | `/deploy/railway/worker.json` | None |
| `maintenance` | Same backend source | `/deploy/railway/maintenance.json` | None |

All source deployments use the repository root and its Dockerfile. The Docker build excludes the Lovable frontend, local databases, local environments and virtualenvs. Configure each service's config-file path explicitly so worker and maintenance do not inherit the web start command. The web pre-deploy job applies migrations once before promoting that deployment. Wait for the web release migration to succeed before starting the worker or maintenance services against a fresh database. Maintenance runs daily at 14:15 UTC; Railway schedules use UTC.

The workspace has no Git remote configured. Deploy the source directly through the Railway connection/CLI if supported, or connect a private repository before configuring Git-based deploys. The local `frontend/` is a snapshot of the separate Lovable project, not its Git sync.

## Environment

Set secrets directly in Railway's secret/variable interface. Do not paste Stripe keys, SMTP passwords, database credentials or account tokens into chat, source files or the Lovable frontend.

Set shared variables on the backend services:

- `DJANGO_SETTINGS_MODULE=ocp.settings.production`
- `OCP_DEBUG=0`
- `OCP_SECRET_KEY`: generate a new random value, at least 50 characters; use the same stable value on web/worker/maintenance and across redeploys.
- `OCP_DATABASE_URL=${{Postgres.DATABASE_URL}}`: reference the private database URL, using the actual database service name.
- `OCP_BASE_URL=https://api.YOUR_DOMAIN`: the actual backend origin, also on workers so links in email are correct. A Railway-generated domain may be used while testing, but production login works most reliably with sibling custom domains.
- `OCP_ALLOWED_HOSTS=api.YOUR_DOMAIN,healthcheck.railway.app`: include the actual Railway-generated hostname if it remains in use. Do not use wildcards.
- `OCP_FRONTEND_ORIGINS=https://app.YOUR_DOMAIN`: include only the frontend domains actually in use, comma-separated. The Lovable preview origin can be included explicitly when needed.
- `OCP_CSRF_TRUSTED_ORIGINS`: the same frontend origin list.
- `OCP_BEHIND_PROXY=1`
- `OCP_SESSION_COOKIE_SAMESITE=Lax` for sibling custom domains. Unrelated lovable.app/Railway domains need `None`; browser third-party-cookie blocking can still prevent login. Do not call that configuration browser-compatible without testing it.
- `OCP_PAYMENT_PROVIDER=stripe`, `OCP_STRIPE_SECRET_KEY`, `OCP_STRIPE_WEBHOOK_SECRET`: real account configuration, initially test keys for end-to-end validation, then live keys for public paid sales.
- `OCP_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `OCP_DEFAULT_FROM_EMAIL` (verified sender), `OCP_EMAIL_HOST`, `OCP_EMAIL_PORT`, `OCP_EMAIL_HOST_USER`, `OCP_EMAIL_HOST_PASSWORD`, `OCP_EMAIL_USE_TLS=1`.
- `OCP_GOOGLE_FONTS=0` if using system fonts on Django pages.

Django's production guard requires real database, Stripe and SMTP configuration. Do not use invented keys or console email to force a deployment through.

The web service uses Railway's `PORT` environment variable. Only `/health/live/` and `/health/ready/` are exempt from Django's HTTPS redirect to permit internal probes. The Railway probe hostname is explicitly allowed; every login and business API URL continues to require HTTPS. Readiness checks the database and returns 503 on connection failure.

Set a budget/usage limit and service resource limits before starting paid workloads. Enable database backups and configure ongoing uptime/error monitoring; the deploy healthcheck alone is not ongoing monitoring. Configure rate limiting for authentication, signup and booking lookup at the hosting edge or a trusted reverse proxy before allowing public registration.

## Release order for your own installation

1. Connect the Railway account, confirm spending limit and region, and provision private PostgreSQL with persistent storage/backups.
2. Create the web service and assign its public domain; set its environment and secrets, then deploy the reviewed source. Check successful build, migrations, deploy healthcheck and HTTPS `/health/ready/`.
3. Start the worker and configure the maintenance schedule from the same source and environment. Verify outbox processing and scheduled-job exits.
4. Configure sibling frontend/backend custom domains and their DNS/TLS. Verify final origins before changing Lovable.
5. In Lovable project `88bb01cd-8796-44d3-a3ce-f9778240175e`, set `VITE_OCP_API_URL` to the actual backend HTTPS origin without `/api/v1`, ensure demo mode is disabled, and rebuild. This value is public configuration, not a credential. For a real installation, keep your frontend unpublished until integration checks succeed. The project’s public sample-data demo does not need this connection.
6. Validate login/logout from the actual frontend origin, secure cookies, tenant/volunteer restrictions, event discovery, search/pagination, management navigation and booking lookup. Test Safari and a browser that blocks third-party cookies.
7. Configure the Stripe signed webhook at `${OCP_BASE_URL}/payments/webhook/stripe/`, verify success/failure, duplicate notifications, expiry and refunds in Stripe test mode, and confirm actual ticket email delivery. Switch to live keys only when those checks pass.
8. Create the initial real organizer account. Never seed demo users in production. Publish the Lovable frontend and verify both production URLs and ongoing monitoring.

See `production.md` for rollback, retention and backup requirements. Source references: [Railway config](https://docs.railway.com/config-as-code/reference), [healthchecks](https://docs.railway.com/deployments/healthchecks), [pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command).
