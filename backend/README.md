# RoadWatch AI: Backend

FastAPI + SQLAlchemy + PostgreSQL. Requires Python 3.11 or newer.

## Setup (Windows PowerShell)

Run these from `E:\work_folder\RoadWatch_AI\backend`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

If PowerShell blocks `Activate.ps1`, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Edit `.env`:
1. Set `SECRET_KEY`. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
2. Set `DATABASE_URL`. For PostgreSQL, install it, create a database named `roadwatch`, and put your password in the URL.
   To start without PostgreSQL, use the SQLite line in `.env.example` instead.

Then create the tables and an administrator, and start the server:

```powershell
alembic upgrade head
python -m app.cli.create_admin
uvicorn app.main:app --reload
```

- API docs (try every endpoint): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

## After pulling new code

If `requirements.txt` changed, run `pip install -r requirements-dev.txt` again (with the environment active), then
`alembic upgrade head` if a new migration was added.

## Tests

```powershell
pytest
```

Tests use an in-memory SQLite database, so PostgreSQL is not needed to run them.

## Code layout

```
app/
├── api/            HTTP only: routes, dependencies, error mapping
│   └── routes/     complaints.py (citizen), auth.py, admin_complaints.py
├── services/       Business rules: complaint_service, auth_service, photo_storage
├── repositories/   Database queries only
├── models/         SQLAlchemy tables
├── schemas/        Request and response shapes (Pydantic)
├── core/           Settings, enums, security, complaint code, errors
├── db/             Engine, session, base class
└── cli/            create_admin
alembic/            Database migrations
tests/              One file per feature area
```

Rule of thumb: a route never queries the database, a service never knows about HTTP,
a repository never contains business rules.

## API summary

| Method and path | Who | Purpose |
|---|---|---|
| POST /api/complaints | Citizen | Submit (form data: description, latitude, longitude, optional address_text, contact, photo; `website` must stay empty). Returns 429 when rate limited |
| GET /api/complaints/{id} | Citizen | Track status and timeline |
| POST /api/admin/login | Admin | Get a bearer token |
| GET /api/admin/complaints | Admin | List with filters (status, category, priority, search, date_from, date_to) and paging. Dates are whole days in the `TIMEZONE` setting (default `Asia/Karachi`) |
| GET /api/admin/complaints/{id} | Admin | Full detail and history |
| PATCH /api/admin/complaints/{id} | Admin | Change status, category, priority, add a note |
| GET /api/admin/complaints/{id}/photo | Admin | Download the photo |

## Language model (Gemini)

See `docs/setup.md`, section "Gemini". Quick check: `python -m app.cli.try_llm`. Without a configured key and model,
triage runs with the rule-based fallback.

## Spam protection on the submit endpoint

- **Rate limit:** each IP address may submit `SUBMISSIONS_PER_HOUR` complaints per hour (default 10).
  Extra requests get `429` with a `Retry-After` header. Counts are kept in memory, so they reset
  when the server restarts. For demos or heavy manual testing, raise the value in `.env`.
- **Honeypot:** the form field `website` must stay empty. The real frontend form hides it
  (CSS hidden, `tabindex="-1"`, `autocomplete="off"`). Bots tend to fill every field, and a filled
  `website` is silently ignored: the API answers `201` with an ID that tracks nowhere.
- Behind a proxy or load balancer all users share the proxy's address, so the limiter would need
  the real client address. This is noted as a known limitation in `docs/decisions.md`.

## Changing the schema

1. Edit the model in `app/models/`.
2. `alembic revision --autogenerate -m "describe the change"`
3. Read the generated file in `alembic/versions/`, then `alembic upgrade head`.

## Where later milestones plug in

- AI tools and the triage agent: a new `app/ai/` package called from a service. Routes stay unchanged.
- New categories, statuses or priorities: edit `app/core/enums.py`, then create a migration.
