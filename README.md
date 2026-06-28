# Jena Event Aggregator

Aggregates event information for **Jena, Weimar, and Apolda** from many sources
(venue websites, regional aggregators, RSS/iCal feeds), normalizes it with an
LLM, and makes it browsable, filterable by interest, and exportable as iCal.

See [`PLAN.md`](./PLAN.md) for the full design, roadmap, and decisions.

## Architecture

Two services share one Postgres, orchestrated with Docker Compose on a single VPS:

- **`services/scraper`** (Python) — the ingestion pipeline:
  `fetch → LLM extract → normalize → dedupe → store`. LLM access is
  provider-agnostic via OpenRouter.
- **`services/web`** (TypeScript / Next.js) — API + UI + iCal export. *Phase 2.*
- **`db/migrations`** — the canonical SQL schema; the contract both services
  share so neither side drifts.
- **`sources.yaml`** — the config-driven source registry.

## Quick start

```bash
cp .env.example .env          # set POSTGRES_PASSWORD, OPENROUTER_API_KEY, ...

docker compose up -d db       # start Postgres
docker compose run --rm migrate   # apply db/migrations/*.sql

# List configured sources
docker compose run --rm scraper list-sources

# Run one source end-to-end (omit --dry-run to write to the DB)
docker compose run --rm scraper run-source example-feed --dry-run
```

## Local development (scraper)

```bash
cd services/scraper
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m eventscraper.cli list-sources
```

`tests/` use saved/synthetic data and do **not** hit the network or the LLM.

## Adding a source

Add an entry to [`sources.yaml`](./sources.yaml). Most sources need no code —
pick `fetch.type` (`feed` for RSS/iCal, `html` for static pages). Fill in the
`legal` block (robots.txt / ToS / contact) and set `enabled: true` only once
it's verified. See `PLAN.md` §2 for the legal/ethical guardrails.

## Status

- [x] Plan & decisions (`PLAN.md`)
- [x] Phase 0 — foundations: infra, schema, source registry, OpenRouter client
- [ ] Phase 1 — vertical slice on a real feed + HTML venue
- [ ] Phase 2 — web app: browse/filter + iCal export
- [ ] Phase 3 — scale sources, dedupe, classification, scheduling/monitoring
- [ ] Phase 4 — "I feel lucky"
