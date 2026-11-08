# Local setup

## Requirements

- Python **3.12 recommended** (backend declares 3.11–3.14), uv and an isolated environment.
- Node **24 LTS** (frontend requires >=22.12), npm and a WebGL-capable browser.
- PostgreSQL + pgvector, either Compose (Docker Engine/Desktop with Linux containers)
  or an existing managed service. Docker is not necessary for frontend demo mode.
- Optional user-supplied OpenAI/eBay credentials; never put secrets in frontend variables.

Run the following from the repository root in two terminals. Paths are relative
to this copy; no original development folder or portable tool installation is used.

## Database and backend

```bash
cd backend
uv sync --locked --extra dev --python 3.12
cp .env.example .env
```

PowerShell uses `Copy-Item .env.example .env`. Set `POSTGRES_PASSWORD` to your own
local password and use the same URL-encoded value in `DATABASE_URL`.
For Compose, leave the loopback port/database/user consistent with this example:

```bash
docker compose up -d --wait
uv run --locked alembic upgrade head
uv run --locked python -m app.database.verify
uv run --locked python -m app
```

The entry point binds loopback **8002** and selects an async-psycopg-compatible
Windows event loop. Startup checks migrations and idempotently seeds Golf Plus
2009/CFFB; it never silently switches to memory. No manual or document is seeded.
No extra seed command is required. Open `/docs` for the actual OpenAPI endpoints.

For managed PostgreSQL, skip Compose. Configure a dedicated database with the
`vector` extension available and use a `postgresql+psycopg://` URL. Preserve SSL
parameters required by the provider; percent-encode special characters in secrets.
Run the same Alembic, verification and startup commands. Never test against user data.

## Frontend

```bash
cd frontend
npm ci
npm run dev -- --port 5174
```

Vite proxies `/api` to loopback 8002. Use `http://127.0.0.1:5174/` for backend mode,
or append `?demo=1` for explicitly synthetic browser-only examples. Source Vite
defaults to 5173; these instructions and the optional launcher intentionally use
5174. `frontend/.env.example` contains public build-time settings only.

## AI and RAG

Put your own `OPENAI_API_KEY` in `backend/.env`, then restart the backend.
The configured defaults are `gpt-4.1-mini` and `text-embedding-3-small` (1536-D).
Without a key, ordinary assessments return a configuration error. CRUD/history
and deterministic recognized critical alerts do not require OpenAI.

The seven authored generic notes can be loaded **without generating vectors**:

```bash
cd backend
uv run --locked python -m app.rag.cli
```

To generate their embeddings, explicitly accept API cost by running:

```bash
uv run --locked python -m app.rag.cli --index
```

For private authorized documents, set a random `RAG_ADMIN_TOKEN` (at least 24
characters) and use the authenticated document upload/index routes in `/docs`,
or the reviewed manifest CLI. Keep files/manifests outside Git. Permissions,
source identity and applicability must be verified separately. [RAG guide](../technical/RAG.md).

## MCP

For a credential-free synthetic tool demonstration, set in `backend/.env`:

```dotenv
MCP_ENABLED=true
MCP_TRANSPORT=stdio
AUTOMOTIVE_PROVIDER=demo
```

Restart the backend. Stdio starts the MCP server per bounded client session;
do not manually start another MCP process. For eBay, select `ebay` or
`ebay_sandbox` and fill the matching credential pair. Neither tool access nor
demo mode requires OpenAI. [Provider/HTTP details](../technical/MCP.md).

## Optional desktop launcher

After installing dependencies, configuring the backend and applying migrations,
Windows users can double-click `Open MotorAI.vbs`. The launcher finds the project's
backend environment and Node on PATH, checks service identity and opens 5174.
It performs no installs, migrations or configuration edits. Occupied ports owned
by other applications are reported, never killed. A cross-platform console check:

```bash
python scripts/start_motorai.py --no-window
```

## Verification

Run backend commands from `backend/`, frontend commands from `frontend/`:

```bash
uv run --locked pytest tests -m "not live and not database" -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

```bash
npm run generate:api
npm run format:check
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Use `PYTHON` to select the installed backend interpreter for API generation and
browser tests if it is not in `backend/.venv`. The browser suite uses a separate
test-only FastAPI process on 18001 and Vite on 15173, with memory storage and a fake
structured model, never real credentials. Close other test instances before running.
If those test ports belong to another application, set `MOTOR_E2E_BACKEND_PORT`
and `MOTOR_E2E_FRONTEND_PORT` to distinct free ports in the same terminal before
running Playwright. For example, PowerShell uses
`$env:MOTOR_E2E_BACKEND_PORT="18104"` and `$env:MOTOR_E2E_FRONTEND_PORT="15174"`.
The harness refuses occupied ports and never stops unrelated applications.

For database tests, create a **separate** database named `test_motor` with pgvector.
Export `TEST_DATABASE_URL=postgresql+psycopg://.../test_motor` in your shell and run
`uv run --locked pytest tests -m database -q`. PowerShell uses `$env:TEST_DATABASE_URL`.
Fixtures create/drop only freshly allocated test schemas and refuse the development DB.
Use a direct (unpooled) connection for schema-isolated tests. Neon transaction
pooling rejects the per-test `search_path` startup parameter; this does not imply
that the application database is unavailable. Do not put real connection strings
in source control.

## Troubleshooting

- Database startup failure: check reachability, SSL options, extension availability
  and migration revision. There is no automatic database reset or memory fallback.
- Port conflict: choose a free frontend port explicitly; update CORS if connecting
  directly across origins. Avoid interfering with other applications on 8000/5173.
- No evidence: ingest, verify eligibility and index your own authorized references;
  text loading alone is not semantic search. Source flags are not proof of rights.
- `invalid_client` from eBay: check matching environment App ID/Cert ID and keyset
  enablement; ordinary Parts errors do not switch to invented offers.
- MCP startup latency: cold subprocess imports can be slow; see timeouts in the
  example file. A timeout is unavailable data, not a compatibility conclusion.
- 3D unavailable: a poster fallback appears. Keep asset files and credits intact.
- uv hardlink errors on cloud-backed Windows folders: repeat `uv sync --locked
  --extra dev --python 3.12 --link-mode copy`. Copy mode was used in release verification.
- Image rights: the included engine photo is non-commercial. Replace it or obtain
  separate permission before a commercial deployment.
