# CLAUDE.md

Guidance for working in this repository.

## What this is

`agentic-mediapulse` is an agentic newsletter generator. Given a subject (a stock ticker, company name, or industry theme), a newsroom of focused agents researches, writes, and edits a locale-aware briefing across five editorial sections, with every claim traced to a real source. It is built on the Microsoft Agent Framework (`agent-framework`) plus a round-robin web toolbelt (Serper, Exa, Tavily, Firecrawl, Diffbot) for search and page fetch.

## Layout

All application code lives under `src/`. Packages keep their top-level names (`agents`, `db`, `emails`), so imports are `from agents...` / `from db...` / `from emails...`, with `src` on the path (pytest sets `pythonpath = ["src"]`; the Docker image runs uvicorn with `--app-dir src`). Run entrypoints from the repo root so `load_dotenv()` finds `.env`.

- `src/api.py` — FastAPI service. `POST /run` (full campaign) and `POST /test` (one user). Both run in the background, return `202`, and default to dry-run. Auth via the `X-API-Key` header matched against `SECRET_KEY`.
- `src/app.py` — local CLI mirroring the API (`run`, `test`), for testing without HTTP.
- `src/newsroom/` — the pipeline that orchestrates the agents. `orchestrator.py` is the run: analyst → 5 parallel beat desks (researcher → writer → editor) → managing-editor gap roundtable → masthead → reviewer → deterministic clean/assemble/dedupe (most non-agent logic, citation gating, URL/article validation, dedupe, subject-name canonicalization, prose humanizing, lives here). `beats.py` builds the five beat desks, `campaign.py` is the top-level run over subscriptions (which skips and marks `failed` any newsletter that comes out with zero sections rather than sending it), and `translation.py` is the post-assembly step that translates each finished edition into the configured `NEWSLETTER_LANGUAGES` and stores the variants, which are archived not emailed (English stays the only thing sent).
- `src/agents/` — one module per agent (`analyst`, `researcher`, `writer`, `editor`, `managing_editor`, `reviewer`, `translator`), plus `sections.py` (the five editorial beats that the researcher/writer agents are built on), `providers/` (subject-memory and ticker-profile context providers), and `tools/` (the `web_search` and `web_fetch` tools over a round-robin + failover provider package in `tools/providers/`: Serper, Exa, Tavily, Firecrawl, Diffbot, selected deterministically and hidden from the LLM).
- `src/agents/runtime/` — agent plumbing shared by every agent: `chat_client.py` (per-role chat client plus the `SKILLS` provider), `make_agent.py` (the factory that wires generic activity tracking into every agent), `guardrails.py` (guardrail/citation middleware), and `tracking.py` (the generic `ActivityTracker`/`ToolTracker` middleware, `newsletter_scope`, and run context vars). New agents are built via `make_agent(...)` so tracking is automatic.
- `src/agents/skills/` — `SKILL.md` files that control agent behavior (`subject-profile`, `section-research`, `newsletter-format`, `translation`). Prefer editing these over code when changing how agents research or write.
- `src/db/` — all database access. `mediapulse.py` reads subscriptions and ticker profiles from the upstream MediaPulse Postgres (`MEDIAPULSE_DATABASE_URL`, read-only, raw psycopg). The app's own Postgres (`DATABASE_URL`, SQLModel) uses `engine.py` for the shared engine, with each table's model alongside its operations: `newsletters.py` (archives each newsletter as markdown plus JSONB metadata, with a `pending`/`completed`/`failed` lifecycle via `create_newsletter`/`finalize_newsletter`), `newsletter_translations.py` (stored localized variants of a finished newsletter, keyed by `newsletter_id` + `language` with a denormalized `subject`, written by `newsroom/translation.py`), `memory.py` (subject-brief agent memory), and `agent_activity.py` (one row per agent run and tool call, tied to its `newsletter_id`, recording status, duration, model, and token usage). The schema is owned by Alembic migrations, not `create_all` (see Migrations).
- `src/emails/` — everything email-related. `mailer.py` sends via Resend. `templates/` pairs each template's renderer with its tokenized HTML: `templates/newsletter.py` parses the newsletter markdown and fills `templates/newsletter.html` (the gitignored build artifact from `email-playground`).
- `email-playground/` — a standalone React Email (TypeScript) project that is the visual source-of-truth for MediaPulse email templates (the newsletter is the first one). `npm run build:templates` renders each template to a tokenized `src/emails/templates/<name>.html` that the Python side consumes (`emails/templates/newsletter.py` for the newsletter). Those HTML files are gitignored build artifacts, regenerated fresh in CI and the Docker build. Restyle emails there, not in Python. See `email-playground/README.md`.
- `tests/` — pytest suite covering the deterministic logic (see Testing below).

## Setup

```
conda env create -f environment.yml
conda activate agentic-mediapulse
pip install -r requirements-dev.txt   # adds ruff
cp .env.example .env                  # fill in keys
```

## Running

```
python src/app.py run                              # dry-run full campaign
python src/app.py run --send                        # email all subscribers
python src/app.py test --email=you@example.com      # dry-run one user
python src/api.py                                    # serve at http://localhost:8000 (docs at /docs)
```

## Migrations

The app's own Postgres schema (`DATABASE_URL`) is managed by Alembic, not `create_all`. Migrations live in `alembic/versions/`; `alembic/env.py` puts `src` on the path, loads `.env`, resolves `DATABASE_URL` (reusing `db.engine._engine_url`), and targets `SQLModel.metadata`.

```
alembic upgrade head                                  # apply pending migrations
alembic revision -m "add X"                            # new (hand-written) migration
alembic revision --autogenerate -m "add X"            # diff models vs DB, needs a live DATABASE_URL
alembic downgrade -1                                   # roll back one
```

The Docker image runs `alembic upgrade head` on container start via `docker-entrypoint.sh`, then execs the `CMD`. It is skipped when `DATABASE_URL` is unset or `RUN_MIGRATIONS=0`. To run migrations as a standalone release job with the same image: `docker run -e RUN_MIGRATIONS=0 <image> alembic upgrade head`. After changing a SQLModel table, add a migration in the same change so deploys stay in sync.

## Code quality

CI (`.github/workflows/code-quality.yml`) runs exactly these two commands, both must pass:

```
ruff check .
ruff format --check .
```

Ruff config is in `pyproject.toml`: line length 120, target `py311`, lint rules `E`/`F`/`I`/`W`, with `E402` ignored in `src/api.py` and `src/app.py` (they `load_dotenv()` before importing app modules).

A `PostToolUse` hook in `.claude/settings.json` runs both ruff commands automatically after any `.py` file is edited and reports violations to fix. It invokes ruff via `conda run -n agentic-mediapulse`, so the conda env must exist. That hook is the enforcement path, so there is no separate lint subagent.

## Testing

```
pytest                                  # whole suite
conda run -n agentic-mediapulse pytest  # if pytest is not on PATH
```

The email-template tests read `src/emails/templates/newsletter.html`, which is gitignored and generated by the playground. Build it once before running the suite locally (CI does this in the `tests` job):

```
cd email-playground && npm install && npm run build:templates
```

Config is in `pyproject.toml` under `[tool.pytest.ini_options]`: `pythonpath = ["src"]`, `testpaths = ["tests"]`, `asyncio_mode = "auto"` (async tests need no decorator). CI runs `pytest` in a separate `tests` job after installing both requirement files.

The suite covers the deterministic logic, not the LLM agents: orchestrator text/section helpers, the email template, Serper tools, the MediaPulse profile shaping, the newsletter store and lifecycle and subject-memory upsert, the agent-activity store, the guardrail and activity-tracking middleware, the subject-memory and ticker-profile context providers, the mailer, the client model resolution, and the campaign delivery flow. Conventions for new tests:

- `tests/conftest.py` sets dummy credentials before collection, because importing the agent modules constructs the whole agent graph at import time.
- Every external call (httpx, psycopg, the LLM clients) is monkeypatched, and the SQLModel store is exercised against in-memory SQLite. The suite is fully offline. A test that reaches the network is a test bug.
- Use `ACME` (and other clearly-fictional placeholders) for ticker symbols and company names, never real tickers.
- The `test-runner` subagent runs the suite and reports failures without editing.

## Pull requests

`/pr` (`.claude/skills/pr/`) opens a PR with `gh`: it runs ruff and pytest, makes sure the PR links to an open issue (creating one if none exists), opens the PR with `gh pr create`, then launches the `pr-check-monitor` subagent (haiku) in the background to watch CI and fix any failing check. The repo is `hyperjumptech/agentic-mediapulse`; `gh` lives at `/opt/homebrew/bin/gh`.

## Conventions

- Python 3.11, async throughout (`asyncio.gather` for parallel beats).
- Keep prose free of em dashes and semicolons in generated output (`_humanize` enforces this in the pipeline).
- Deterministic gates and agent feedback loops are bounded with explicit retry counts (`RETRIES`, `DISCUSSION_ROUNDS`); preserve those bounds when editing the orchestrator.
- Surround a multi-line block (`if`, `for`, `while`, `with`, `try`) with a blank line above and below whenever other code sits next to it in the same block. Also put a blank line above a `return` that has code before it.
- Keep docstrings and comments to a single concise line, and drop comments that only restate what the code shows.

## External services

- `SERPER_API_KEY` — web search and page fetch (the baseline provider).
- `EXA_API_KEY`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, `DIFFBOT_API_KEY` — optional extra providers; when their key is set they join a deterministic round-robin with failover (Exa and Tavily also search, Firecrawl and Diffbot fetch only). `web_search`/`web_fetch` keep an identical signature, so the LLM never sees which provider served a call.
- `MEDIAPULSE_DATABASE_URL` — read-only Postgres for subscriptions and ticker data; schema is defined in the upstream [MediaPulse](https://github.com/hyperjumptech/mediapulse) repo.
- `DATABASE_URL` — the app's own read-write Postgres for archived newsletters and agent memory. Tables are auto-created on first use, separate from `MEDIAPULSE_DATABASE_URL`.
- `NEWSLETTER_LANGUAGES` — optional, comma-separated target language names (e.g. `Indonesian,Thai`). When set and `DATABASE_URL` is configured, each finished newsletter is also translated into every listed language and stored in `newsletter_translations`. English is always the base and the only language emailed; translations are archived, not sent. `TRANSLATOR_MODEL` overrides the translator's model like the other per-role model vars.
- `SECRET_KEY` — API auth.
