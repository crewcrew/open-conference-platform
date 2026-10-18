# Production deployment

This guide is for people deploying their own installation. The public Lovable site is a standalone sample-data demo; this project does not provide a shared hosted Django service.

## Architecture

For a real installation, Django owns authentication, organization permissions, checkout, ticket inventory, Stripe webhooks, refunds, email and check-in. Its built-in server-rendered pages work without Lovable. An optional separate frontend may be connected by the person self-hosting the project. PostgreSQL stores application data. A separate worker runs scheduled email and releases expired inventory holds. Frontend mutations currently navigate to Django's working management pages; the new API exposes read views and session authentication.

Use sibling domains, for example `app.example.com` for Lovable and `api.example.com` for Django. HTTPS cookies stay on the Django host and default to SameSite=Lax. Configure both frontend origins and CSRF trusted origins with exact HTTPS origins, never wildcards. If using the default lovable.app URL with an unrelated backend domain, set `OCP_SESSION_COOKIE_SAMESITE=None`; some browsers will still block third-party cookies. Custom sibling domains are the preferred production setup.

## Backend host

Optional Railway service configurations are described in [the Railway guide](railway.md). Choose your own host; no hosting account is required to explore the Lovable demo.

Choose a Linux VM or container service that supports a long-running web process, a worker and PostgreSQL. The 52 backend tests pass on SQLite and an isolated PostgreSQL instance. Gunicorn startup, static serving, and database-failure readiness have been smoke-tested. Docker is not installed in the development environment, so the image/Compose stack must still be built and smoke-tested on the deployment host before launch.

1. Copy `deploy/production.env.example` to `.env.production` and fill in the values. Generate a secret with `python -c 'import secrets; print(secrets.token_urlsafe(64))'`. Set the same database password in `POSTGRES_PASSWORD` and the URL (URL-encode it in the URL if needed). For managed PostgreSQL, use its connection string, including `?sslmode=require` or stricter certificate verification as required by the provider.
2. Build the image and start PostgreSQL:
   ```sh
   docker compose --env-file .env.production build
   docker compose --env-file .env.production up -d db
   ```
3. Back up an existing database before applying migrations. Run one release job, then start the app:
   ```sh
   docker compose --env-file .env.production run --rm release
   docker compose --env-file .env.production up -d web worker
   docker compose --env-file .env.production exec web python manage.py check --deploy
   docker compose --env-file .env.production exec web python manage.py createsuperuser
   ```
4. Install an HTTPS reverse proxy in front of `127.0.0.1:8000`. Adapt `deploy/nginx.conf.example`, issue real certificates, validate with `nginx -t`, and reload. The proxy must overwrite `X-Forwarded-Proto`. Keep the application port private. Configure equivalent rate limits for login, signup and booking lookup if using another proxy. Gunicorn URL access logs are disabled because booking URLs contain credentials.
5. Point the backend DNS name at the host. Confirm `/health/live/` and `/health/ready/` return 200 over HTTPS. Readiness returns 503 when the database is unavailable, without connection details.
6. Add a daily host cron job (use the absolute checkout path):
   ```cron
   15 3 * * * cd /srv/open-conference-platform && docker compose --env-file .env.production exec -T web python manage.py purge_personal_data
   30 3 * * * cd /srv/open-conference-platform && docker compose --env-file .env.production exec -T web python manage.py clearsessions
   ```
   Host cron times follow the host's timezone. Configure it deliberately. Monitor job failures and worker exits; scheduled email currently uses the existing one-shot claiming behavior and does not guarantee delivery after a process crash during a broadcast. Inspect delivery logs and reconcile interrupted broadcasts before retrying.

Production settings reject debug mode, weak secrets, SQLite, wildcard/local hosts, non-HTTPS base URLs, untrusted frontend origins, test payment providers and console email. HSTS starts at one hour without subdomains/preload; Django may report optional subdomain/preload warnings. Increase HSTS after HTTPS has been verified; enable subdomain/preload only after considering all affected domains.

## Optional frontend for self-hosters

Project: https://lovable.dev/projects/88bb01cd-8796-44d3-a3ce-f9778240175e

A local frontend source snapshot is in `frontend/` (Lovable commit `ad7c4fa5a1763003e7780d3121b9cd456dee71a6`). Lovable verified 33 tests, type checking, and a production build. The public demo is https://open-conference-compass.lovable.app. The local folder is an export, not an automatic Git sync; make subsequent remote edits in Lovable or configure a shared repository deliberately.

The Lovable demo runs on sample data. To connect your own frontend installation to your own Django instance, set `VITE_OCP_API_URL=https://api.example.com`, rebuild, and configure its custom domain. The URL is the Django origin, without `/api/v1`. Add the exact frontend origin to `OCP_FRONTEND_ORIGINS` and `OCP_CSRF_TRUSTED_ORIGINS` on Django, and restart the web/worker processes. No backend URL is fabricated. Without a backend URL, the demo frontend runs on fictional sample data.

Read-only API contract: `docs/api.md`. Checkout, refunds, invitations, attendee editing, event setup and scanning remain on Django pages. Authentication uses server sessions, CSRF tokens and credentialed fetch; no JWTs or passwords are stored in browser storage.

## Launch validation

Run backend tests on PostgreSQL (CI includes this target), then verify from the real frontend domain: login/logout, tenant isolation, volunteer restrictions, event listing, schedule, attendee search, pagination, checkout navigation and management links. Verify Safari and a browser that blocks third-party cookies.

Use a separate Stripe test configuration to exercise successful and failed checkout, duplicate webhooks, an expired hold and refunds before switching to live keys. Register the webhook at `/payments/webhook/stripe/` for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired`, and `refund.updated`. Confirm signatures and real email delivery from the verified sender. Never seed demo accounts in production.

Monitor HTTPS availability, 5xx errors, database connections, disk space, failed email deliveries, refund failures and outbox worker health. Configure encrypted database backups outside the host and test a restore. For Compose PostgreSQL, stream `pg_dump` to protected backup storage; do not commit backup files. Pin production images by digest in your deployment system after validation.

## Updating and rollback

Build and tag each release immutably. Back up PostgreSQL, run the release migration once, then restart web/worker with the new image. If application rollback is needed, restore the previous image only when schema compatibility is confirmed. Restore the database backup if a migration cannot be safely reversed; rehearse the restore procedure before launch. Compose volumes persist data; never run `down -v` against production.
