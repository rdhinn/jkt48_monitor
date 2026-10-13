# JKT48 Availability Monitor

Real-time monitoring of JKT48 ticket availability (video call, meet & greet, two
shot) using the **[48pedia.id Public API](https://api.48pedia.id/v1)**.

- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + Recharts — dark dashboard
- **Backend**: FastAPI + SQLAlchemy 2 (async) + Alembic migrations
- **Database**: PostgreSQL 16 (Docker) or SQLite (local, default)
- **Workers**: background polling scheduler + Telegram long-polling bot
- **Notifications**: Telegram bot alerts on significant availability changes

> ⚠️ Live data requires a free 48pedia API key, obtained at
> https://48pedia.id/register. Without a key the app still runs: sources are
> reported as *unavailable* and snapshots are simply not produced. Errors are
> **never** converted into fake `sold_out` data.

---

## Architecture

```
frontend (Next.js :3000)
   │  REST /api/v1 (js fetch)
   ▼
backend (FastAPI :8000, uvicorn)   ──►  48pedia.id Public API (Bearer API key)
   │  │ poll every POLL_INTERVAL_SECONDS (default 60s)
   │  │ single-flight monitor + change detection + deduplicated Telegram alerts
   ▼
PostgreSQL 16 (db:5432) / SQLite fallback
```

Status model (canonical): `available`, `sold_out`, `not_open`, `unknown`,
`unavailable`, `cancelled`. Ticket counts are non-negative integers or `null`.

---

## Quick start with Docker

```bash
cp .env.example .env        # then fill JKT48_API_KEY, JWT_SECRET, admin password…
docker compose up --build
```

- Frontend → http://localhost:3000
- Backend  → http://localhost:8000  (OpenAPI: /docs)
- Migrations run automatically via `alembic upgrade head` before startup.

## Local development (Windows / any OS)

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m alembic upgrade head     # SQLite by default
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
# optional: set NEXT_PUBLIC_API_BASE_URL, defaults to http://localhost:8000/api/v1
npm run dev        # http://localhost:3000
```

### Tests

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q      # 87 tests (connectors, sync, diff,
                                         # notifications, API, rate limiting)
```

---

## Configuration

All settings come from environment variables (see
[backend/.env.example](backend/.env.example) and [.env.example](.env.example)).

| Variable | Default | Purpose |
| --- | --- | --- |
| `JKT48_API_KEY` | *(empty)* | 48pedia API key — **required** for live data |
| `JKT48_API_BASE_URL` | `https://api.48pedia.id/v1` | API base URL |
| `POLL_INTERVAL_SECONDS` | `60` | Scheduler polling interval |
| `ENABLE_SCHEDULER` | `true` | Enable background monitor loop |
| `MAX_MANUAL_REFRESH_PER_MINUTE` | `4` | Manual refresh rate limit |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin` *(dev)* | Seeded admin credentials |
| `JWT_SECRET` | dev value | Signing key (~≥32 chars) |
| `TELEGRAM_BOT_TOKEN` | *(empty)* | Bot token (from @BotFather); empty disables alerts |
| `TELEGRAM_POLLING_ENABLED` | `false` | Run the long-polling commands worker |
| `DATABASE_URL` | SQLite (local) | e.g. `postgresql+asyncpg://user:pass@db:5432/jkt48_monitor` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated browser origins |

### Telegram notifications

1. Create a bot with [@BotFather](https://t.me/BotFather), copy the token.
2. Set `TELEGRAM_BOT_TOKEN` (and `TELEGRAM_POLLING_ENABLED=true` to enable the
   `/availability`, `/members`, `/favorite`, … commands).
3. In the web UI (**Pengaturan** → *Notifikasi Telegram*) input your chat/group
   ID, pick an event type and save a subscription.
4. The monitor notifies on significant changes: new events with real data,
   `sold_out → available`, `available → sold_out`, and ticket-count decreases.
   Messages are deduplicated per subscription+event.

### Manual refresh

Authenticated endpoint that triggers an immediate one-off sync, rate limited:

```
POST /api/v1/monitor/refresh          (Authorization: Bearer <token>)
GET  /api/v1/auth/token               Body: {"username": "admin", "password": "…"}
```

The web UI exposes this on **Pengaturan → Sinkronisasi manual**.

---

## API (prefix `/api/v1`)

| Endpoint | Description |
| --- | --- |
| `GET /health` | Health + source configured flag |
| `GET /dashboard` | Stats, recent changes, availability-by-category, source status |
| `GET /sources/status` | Per-source state (`48pedia`, `jkt48_official`, `jkt48connect`) |
| `GET /members` | Members (search/team/generation/status/category/favorites filters) |
| `GET /members/{id}` | Member detail + availability summary |
| `GET /availability` | Latest availability rows (filters: category, status, member, favorites…) |
| `GET /availability/history` | Snapshot history (paginated) |
| `GET /events` · `GET /events/{id}` | Events & sessions |
| `GET|POST|DELETE /favorites/...` | Favorite members |
| `GET|PUT /notifications` | Telegram subscriptions; `DELETE /notifications/{id}` |
| `GET /monitor/status` | Worker status |
| `POST /monitor/refresh` | Manual sync (auth + rate limited) |

Full interactive docs at http://localhost:8000/docs.

---

## Data sources

| Source | Status | Notes |
| --- | --- | --- |
| **48pedia.id Public API** | ✅ Supported | Exclusives, detail & live sales (`sold_count`, `available_count`, `fill_rate`, `as_of`). |
| jkt48.com | ⚠️ Unsupported | Returns HTTP 403 to automated clients; not scraped. |
| JKT48Connect (official) | ⚠️ Unsupported | Host not resolvable / ticket stock not documented. |

Known 48pedia caveats: some fields are absent or `null` for certain events/
categories (e.g. `available_count`), which is handled by storing `null` and
leaving status as derived from real data only.

---

## Project layout

```
backend/
  app/api/v1/          # routers (auth, dashboard, members, availability, …)
  app/connectors/      # 48pedia adapter, normalization, registry
  app/services/        # diff, sync, monitor, notifier, telegram
  app/repositories/    # data access layers
  app/models/          # SQLAlchemy models + enums
  alembic/             # migrations (initial schema applied in dev)
  tests/               # pytest suite
frontend/
  app/                 # pages: dashboard, availability, members, schedule,
                       #         history, favorites, settings
  components/ hooks/ lib/ types/
docker-compose.yml     # db + backend + frontend
```

## Limitations

- Windows sandbox used for development cannot run Docker, so the compose stack
  was not executed end-to-end locally; the backend was verified with SQLite and
  the frontend was built/typed (next build).
- Live 48pedia requests could not be exercised without an API key; connectors,
  mapping and error handling are covered by unit tests using mocked HTTP.