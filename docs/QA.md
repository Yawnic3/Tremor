# Verification record — 2026-10-17

Native Python 3.12 and Node 22 execution on Windows. Docker unavailable.

- Backend: 17 pytest cases, Ruff and mypy pass. Tests cover known-answer OLS/CAR and confidence intervals, insufficient observations, adjusted-price requirements, cache/CSV behavior, adapter fixtures, failed-source cooldown, normalized filters and idempotent seeds.
- Frontend: Vitest, ESLint, strict TypeScript and Vite production build pass. Vite warns about the size of the MapLibre bundle (approximately 1.3 MB before gzip); an explicitly bundled module worker fixes Vite dev worker resolution.
- Native servers: FastAPI health, event filters, company/exposure/price/history endpoints, OpenAPI and Vite page return successfully.
- Live fetches: USGS 354 records, NWS 11 geolocated alerts. USGS January 2025 backfill returned 6 M4+ contiguous-US records. These are local cache observations, not committed source fixtures.
- GDELT live fetch failed; recorded failure/cooldown retained existing cache. FIRMS not live-tested without a free MAP_KEY. Both have offline normalization fixtures.
- Browser: clustered basemap renders; event type filter returns one recent illustrative earthquake; severity 5 yields empty state and recovers; observed mode displays fetched records; Apple selection displays location marker, provenance and explicitly synthetic chart; historical panel displays 6 illustrative events, CAR intervals and nonsignificance warnings. Native dialog Escape dismisses and returns focus to opener.
- Responsive: desktop 1440×1000 and mobile approximately 390×844 checked, no horizontal page overflow, separate panel/list scroll areas. Temporary viewport overrides reset after QA. Screenshots saved in docs/screenshots.
- Git exclusion audit: only .env.example is tracked; .env, environments, dependencies, runtime SQLite, imported prices, logs, coverage and build artifacts are ignored. Docker context has corresponding exclusions.

Remaining limitations: Docker needs an actual Compose smoke test on a Docker host; 46 corporate location leads remain unverified; observed studies require licensed adjusted-price histories; optional upstream integrations need live verification. Statistical inference is exploratory, not causal or predictive.
