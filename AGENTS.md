# Repository conventions

Read PLAN.md before changes. Keep demo and observed data visibly distinct. Never commit secrets or runtime databases. Use Python type hints and validated API schemas; keep adapters independent of persistence and analytics pure. Frontend uses strict TypeScript and accessible semantic controls. Document new dependencies in PLAN.md.

Run backend: `python -m uvicorn backend.app.main:app --port 8000`. Seed: `python -m backend.app.cli seed`. Ingest: `python -m backend.app.cli ingest`. Frontend: `npm install` then `npm run dev`. Docker: `docker compose up --build` then `docker compose exec api python -m backend.app.cli seed`.

Checks: `python -m pytest`, `python -m ruff check backend`, `python -m mypy backend`, `npm test`, `npm run lint`, `npm run build`. Run relevant checks and smoke the running API after each phase; update PLAN.md and commit a clear phase message. Analytics require deterministic known-answer tests. External integrations must have offline fixture tests. Do not silently treat failed fetches or insufficient samples as success.

Configuration uses TREMOR_DB and TREMOR_USER_AGENT in .env (see .env.example). Keep .env ignored. Price fetching/importing and optional sources are CLI-only. Format Python with Ruff and frontend/config with Prettier. The default illustrative date filter begins September 2026; clear it to inspect earlier seeded history. Read README.md for data rights and source limitations before enabling observed data. Never relabel a review lead as verified without dated evidence.
