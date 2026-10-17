# Tremor implementation plan

## Architecture and assumptions
Local research application: React + TypeScript + Vite, MapLibre GL JS, and a Python FastAPI service with SQLite. SQLite uses bounding-box prefiltering and exact haversine distance; no spatial extension is necessary for the initial dataset. Docker Compose runs both services. A scheduled command ingests upstream data; the API never starts uncontrolled background network work. Daily prices and normalized events persist locally. No credentials are needed for USGS/NWS or the core seeded experience. All demo records and synthetic prices are explicitly labeled and excluded from real-world inference.

## Data model
Event: id, type, coordinates, start/end, normalized severity, source, source URL, region, raw payload, synthetic flag. Company: ticker, name, sector. Facility: company, location, type, optional asset/revenue weight, evidence URL, confidence, quality note. Exposure: event/facility distance and weighted proximity score. DailyPrice: provider, ticker, date, adjusted-close assumption, close. IngestionRun: source, outcome, count, error, timestamp. Study: estimation window [-140,-21], market-model OLS with intercept, CAR windows [-1,+1], [0,+5], [0,+20], independent-event aggregation, sample count, t statistic, confidence interval, caveats.

## Sources and terms verification
Verify official current documentation before implementing network adapters. USGS GeoJSON earthquake feeds; NWS active alerts GeoJSON (polygons reduced to centroids, therefore approximate). NASA FIRMS CSV requires a free MAP_KEY; GDELT DOC geographic search requires conservative throttling. SEC EDGAR and company disclosures support a curated headquarters/facility seed, with explicit confidence and limitations. Alpha Vantage daily prices require a free key and have a small daily quota; default to imported CSV and labeled synthetic demo prices until configured. Never represent synthetic values as market observations. Store provenance and fetch timestamps. Do not redistribute vendor price data without applicable permission.

## Dependencies and reasons
FastAPI/Pydantic: typed OpenAPI and validation; uvicorn: ASGI server; httpx: bounded upstream HTTP; numpy: reliable linear algebra; pytest/ruff/mypy: deterministic testing and quality checks. React/ReactDOM: interactive UI; MapLibre: requested clustered map; Vite/TypeScript: build and type checking; Vitest: frontend logic tests; ESLint: frontend lint. Use native SVG for price charts to avoid another chart dependency. Standard-library sqlite3 for durable cache, CSV and scheduler commands; no ORM or scheduler dependency needed.

## Phases and acceptance checklist
- [x] 1. Scaffolding: health endpoint, empty map, Compose, CI, lint/type/test commands; start app and pass checks; commit. Docker execution is blocked by missing Docker; native equivalent used.
- [x] 2. Events: idempotent USGS/NWS adapters, filters and API, failure/rate-limit handling, map events; tests and running-app checks; commit.
- [x] 3. Exposure: 50 curated US-listed company candidates, provenance/confidence, spatial matching, ranked panel and facility display; tests and running-app checks; commit. Four headquarters sources reviewed; remaining 46 explicitly low-confidence review candidates, not independently verified.
- [x] 4. Prices: swappable provider, persistent cache, CSV import/demo distinction, event-marked chart; tests and running-app checks; commit.
- [ ] 5. Analytics: known-answer market-model tests, aggregation and statistical honesty, historical UI; tests and running-app checks; commit.
- [ ] 6. Additional sources/performance: FIRMS/GDELT adapters, bbox, clusters, USGS historical backfill CLI; tests and running-app checks; commit.
- [ ] 7. Polish: responsive/accessibility/loading/errors, methodology, README/screenshots; full validation and final commit.

## Risks and open questions
- Python and Docker are not on the current shell PATH. Find a bundled Python runtime; Docker execution may remain externally blocked and must be reported, not claimed as passed.
- No existing Git repository. Initialize one and make local phase commits, subject to filesystem permissions.
- Assume US focus and USD daily close. Headquarters are only a weak exposure proxy, not a comprehensive supply-chain/revenue model. Seed records must explain this.
- Upstream failures, changing terms, geocoding uncertainty, adjusted price quality, overlapping events, survivorship bias and correlated company observations can invalidate studies. Show warnings; no predictive claims.
- Historical event inventories and actual price histories must be loaded before meaningful real studies. Demo output is educational only.
- Assume local-only delivery as requested by the working-repository and Docker requirements; no hosted publication.

## Validation log
Plan created before application code. Each phase records actual checks and any blocked criteria here.

Phase 1: backend pytest, ruff, mypy and frontend test/lint/build passed; API health and Vite serve checked. TestClient requires an unsandboxed local socket on this host. npm audit found vulnerable initial MapLibre/Vitest versions; upgraded to MapLibre 6.14 and Vitest 5.0.5 (zero reported vulnerabilities). Git ignores cover secrets, environments, caches, builds, logs and runtime data; Docker context has matching exclusions.

Phase 2: 5 backend fixture/API tests cover normalization, idempotency, filters and upstream failure cooldown; frontend test/lint/build and backend ruff/mypy pass. Seeded app runs on localhost. USGS feed and NWS official API docs verified 2026-10-17; fetches cached 15 minutes, 429/failures retain existing data, no busy retries. Demo and observed events are separate modes. Sources: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php and https://www.weather.gov/documentation/services-web-API (free/open government data, NWS nonpublic rate limits and User-Agent requirement). Basemap uses CARTO/OSM with built-in attribution; external network required.

Phase 3: product renamed Tremor per user. 8 backend tests pass; frontend checks pass. Facility schema supports types, weights, confidence, provenance and verification date. Matching uses haversine with latitude prefilter and conservative 0.2 unknown-weight proxy. Seed intentionally documents limited HQ-only coverage and 46 unverified corporate-source review leads; do not interpret these as fully audited operational facilities. Apple, Microsoft, ExxonMobil and Boeing official sources reviewed. Exposures ranked with reasons and configurable radius; company selection displays facility markers. No third-party disclosure text redistributed.

Phase 4: 10 backend tests plus frontend tests/lint/build and ruff/mypy pass. Deterministic synthetic series are separate from observed cache; prices API makes no network requests. CSV importer validates unique dates/positive adjusted close, preserves provenance, and atomically replaces the active series. Provider abstraction and explicit fetch-prices command cache 24 hours. Alpha Vantage official support confirms 25 free requests/day (https://www.alphavantage.co/support/); free compact daily data is unadjusted and often too short for analytics. Adjusted history should be imported under the user's data rights. Event-marked SVG chart includes source/warnings. No new chart dependency.

