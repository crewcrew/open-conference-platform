# Contributing

Open Conference Platform is an MIT-licensed, self-hosted project. The Lovable site is a product demo with fictional data; the Django app is the working application people install themselves.

## Get started

Follow the local setup in README.md. Create a branch for your change and use the demo data, never real attendee records. Python 3.10+ is required; CI uses Python 3.12 and exercises SQLite and PostgreSQL.

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test tests --noinput
```

For frontend changes, see frontend/README.md and the architecture rules in frontend/AGENTS.md. Keep files in the relevant feature folder and keep API/service rules on Django. The frontend snapshot does not automatically sync with the Lovable project.

## Pull requests

Describe the user-facing problem, the change and how you verified it. Keep changes focused. Include migrations when changing models, and regression coverage for fixes affecting permissions, checkout, inventory, payments, email or check-in. Test tenant boundaries and volunteer restrictions when touching access rules. Include screenshots for visible interface changes.

Never commit environment files, credentials, databases, exported attendee data, node_modules, virtual environments or generated build output. Use clearly fictional data in screenshots and tests. Report security issues using SECURITY.md rather than public issues.

## License

By submitting a contribution you agree that it may be distributed under this project's MIT License. Keep third-party copyright and license notices intact.
