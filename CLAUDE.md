# CLAUDE.md

Guidance for working in this repository.

## What this is

`agentic-mediapulse` is an agentic newsletter generator. Given a subject (a stock ticker, company name, or industry theme), a newsroom of focused agents researches, writes, and edits a locale-aware briefing across five editorial sections, with every claim traced to a real source. It is built on the Microsoft Agent Framework (`agent-framework`) plus Serper for web search.

## Layout

All application code lives under `src/`. Packages keep their top-level names (`agents`, `utils`), so imports are `from agents...` / `from utils...`, with `src` on the path (pytest sets `pythonpath = ["src"]`; the Docker image runs uvicorn with `--app-dir src`). Run entrypoints from the repo root so `load_dotenv()` finds `.env`.

- `src/api.py` — FastAPI service. `POST /run` (full campaign) and `POST /test` (one user). Both run in the background, return `202`, and default to dry-run. Auth via the `X-API-Key` header matched against `SECRET_KEY`.
- `src/app.py` — local CLI mirroring the API (`run`, `test`), for testing without HTTP.
- `src/agents/orchestrator.py` — the pipeline: analyst → 5 parallel beat desks (researcher → writer → editor) → managing-editor gap roundtable → masthead → reviewer → deterministic clean/assemble/dedupe. Most non-agent logic (citation gating, URL/article validation, dedupe, subject-name canonicalization, prose humanizing) lives here.
- `src/agents/` — one module per agent (`analyst`, `researcher`, `writer`, `editor`, `managing_editor`, `reviewer`), plus `beats.py` (beat desks), `campaign.py` (top-level run over subscriptions), and `tools/` (Serper search, web fetch).
- `src/agents/skills/` — `SKILL.md` files that control agent behavior (`subject-profile`, `section-research`, `newsletter-format`). Prefer editing these over code when changing how agents research or write.
- `src/utils/` — `db.py` (subscriptions/tickers from the Mediapulse Postgres), `memory.py`, `client.py`, `guardrails.py`, `sections.py`, `mailer.py`, `email_template.py`, `ticker.py`.
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

Config is in `pyproject.toml` under `[tool.pytest.ini_options]`: `pythonpath = ["src"]`, `testpaths = ["tests"]`, `asyncio_mode = "auto"` (async tests need no decorator). CI runs `pytest` in a separate `tests` job after installing both requirement files.

The suite covers the deterministic logic, not the LLM agents: orchestrator text/section helpers, the email template, Serper tools, the DB profile shaping, guardrail middleware, memory/ticker context providers, the mailer, the client model resolution, and the campaign delivery flow. Conventions for new tests:

- `tests/conftest.py` sets dummy credentials before collection, because importing the agent modules constructs the whole agent graph at import time.
- Every external call (httpx, psycopg, redis, the LLM clients) is monkeypatched. The suite is fully offline. A test that reaches the network is a test bug.
- Use `ACME` (and other clearly-fictional placeholders) for ticker symbols and company names, never real tickers.
- The `test-runner` subagent runs the suite and reports failures without editing.

## Pull requests

`/pr` (`.claude/skills/pr/`) opens a PR with `gh`: it runs ruff and pytest, makes sure the PR links to an open issue (creating one if none exists), opens the PR with `gh pr create`, then launches the `pr-check-monitor` subagent (haiku) in the background to watch CI and fix any failing check. The repo is `hyperjumptech/agentic-mediapulse`; `gh` lives at `/opt/homebrew/bin/gh`.

## Conventions

- Python 3.11, async throughout (`asyncio.gather` for parallel beats).
- Keep prose free of em dashes and semicolons in generated output (`_humanize` enforces this in the pipeline).
- Deterministic gates and agent feedback loops are bounded with explicit retry counts (`RETRIES`, `DISCUSSION_ROUNDS`); preserve those bounds when editing the orchestrator.

## External services

- `SERPER_API_KEY` — web search.
- `MEDIAPULSE_DATABASE_URL` — Postgres for subscriptions and ticker data; schema is defined in the upstream [Mediapulse](https://github.com/hyperjumptech/mediapulse) repo.
- `SECRET_KEY` — API auth.
