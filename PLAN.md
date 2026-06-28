# Jena Event Aggregator — Project Plan

> Aggregate event information for Jena and the surrounding region from many
> sources (venues + other aggregators), make it easy to browse, filter by
> interest, and export to iCal. Later: an "I feel lucky" function that buys you
> a random ticket to get you out of the house.

Status: planning. Nothing built yet. This document is the shared spec we
iterate on before writing code.

---

## 1. Goals & non-goals

### v1 goals
- Pull events from a configurable set of sources (venue websites, regional
  aggregators, RSS/iCal feeds, APIs where they exist).
- Use an LLM to turn messy HTML/text into clean, structured events.
- Deduplicate events that appear in more than one source.
- Browse, search, and filter by interest (category/tag), date, location, price.
- Export any filtered view as an iCal feed (subscribable URL + one-off download).
- Run unattended on a schedule and stay fresh.

### Explicit non-goals for v1
- Buying tickets ("I feel lucky") — design for it, build it in a later phase.
- User accounts / personalization beyond saved filters (can be URL-encoded).
- A mobile app (responsive web is enough).

---

## 2. Legal & ethical guardrails (decide early, affects design)

This is an aggregator that scrapes third parties in the EU, so this is not
optional plumbing — it shapes the architecture.

- **robots.txt & ToS:** respect robots.txt; keep a per-source allow/deny flag
  and a polite crawl rate. Some aggregators forbid scraping — prefer official
  feeds/APIs or a partnership where possible.
- **Copyright:** event *facts* (what/when/where) aren't protectable, but
  descriptions and images are. Store source descriptions but prefer to link
  back; consider LLM-generated neutral summaries instead of copying text.
  Always deep-link to the original source ("more info / tickets").
- **GDPR:** events are mostly non-personal, but organizer contact details can be
  personal data. Minimize what we store; have a takedown contact.
- **Attribution:** show the source on every event. Be a good citizen — this
  also makes venues *want* to be listed.

Action: maintain `sources.yaml` with a `legal` block per source (robots ok?,
feed available?, rate limit, contact). No source goes live without it filled in.

---

## 3. Architecture overview

```
                ┌─────────────┐
   sources.yaml │  Scheduler  │ (cron)
        │       └──────┬──────┘
        ▼              ▼
  ┌───────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────┐
  │  Fetcher  │──▶│  Extractor   │──▶│  Normalizer  │──▶│  Dedupe   │
  │ http/RSS/ │   │  (LLM, JSON  │   │ + classifier │   │ + upsert  │
  │ iCal/head-│   │   schema)    │   │  (taxonomy)  │   │           │
  │  less     │   └──────────────┘   └──────────────┘   └─────┬─────┘
  └───────────┘                                               ▼
                                                        ┌───────────┐
                                                        │ Postgres  │
                                                        └─────┬─────┘
                                                              ▼
                                            ┌───────────────────────────┐
                                            │  API (REST/JSON + iCal)    │
                                            └─────────────┬──────────────┘
                                                          ▼
                                            ┌───────────────────────────┐
                                            │  Web UI (browse/filter)    │
                                            └───────────────────────────┘
```

Pipeline stages are independent and idempotent so we can re-run any stage and
debug sources in isolation.

---

## 4. Ingestion pipeline (the heart of it)

**Source registry (`sources.yaml`)** — config-driven, no code per source where
possible:
```yaml
- id: kassablanca
  name: Kassablanca
  region: jena
  fetch:
    type: html        # html | rss | ical | json-api | headless
    url: https://...
    list_selector: ".event"   # optional hint; LLM works without it
  schedule: "0 6 * * *"
  legal: { robots_ok: true, feed: false, rate_limit_s: 5, contact: "..." }
```

**Stage 1 — Fetch.** Strategy per source: plain HTTP (cheerio) for static
pages, RSS/iCal/JSON parsers where feeds exist (cheap, reliable — always prefer
these), headless browser (Playwright, already installed here) only for JS-heavy
sites. Store the raw payload + a content hash.

**Stage 2 — Extract (LLM).** This is where the "intelligence" lives. Feed
cleaned content (strip nav/boilerplate, keep main region) to an LLM with a
**strict JSON schema** and ask for an array of events. Key tactics:
- Provider-agnostic via OpenRouter; a thin `LLMClient` interface so we can swap
  models/providers (see §7).
- Use structured/JSON output mode; validate against the schema (zod) and retry
  on failure.
- **Skip work when content hash is unchanged** — biggest cost lever.
- Chunk long pages; cap tokens; use a cheap model for extraction, escalate only
  on parse failures.

**Stage 3 — Normalize & classify.** Coerce to canonical types: timezone always
`Europe/Berlin`, parse German date formats, geocode venue → lat/lng (cache),
map to our **interest taxonomy** (LLM or rules; see §6).

**Stage 4 — Dedupe & upsert.** Same event from multiple sources → one record.
Match key: fuzzy(title) + same start (±slot) + same/near venue. Keep all source
links on the merged event. Upsert by stable hash; mark unseen events as expired.

---

## 5. Data model (canonical Event)

```
Event
  id              uuid
  title           text
  description     text            -- neutral summary preferred over copied text
  start           timestamptz
  end             timestamptz?    -- nullable
  all_day         bool
  venue_id        fk -> Venue
  categories      text[]          -- from taxonomy (§6)
  tags            text[]          -- free-form
  price_min/max   numeric?        -- null = unknown; 0 = free
  currency        text
  url             text            -- canonical source page
  ticket_url      text?
  image_url       text?
  organizer       text?
  status          enum(active, cancelled, expired)
  first_seen / last_seen  timestamptz
  dedupe_hash     text

EventSource (many-to-many: an event can come from several sources)
  event_id, source_id, source_url, raw_hash, extracted_at

Venue
  id, name, address, lat, lng, region, website

Source   -- mirrors sources.yaml, plus runtime stats (last_run, ok/fail counts)
```

DB: **PostgreSQL** (PostGIS optional, for "events near me"/radius later).

---

## 6. Interest taxonomy & filtering

A fixed top-level taxonomy keeps filtering coherent across messy sources, e.g.:
`Music / Concerts`, `Clubs & Parties`, `Theatre & Performance`, `Film`,
`Art & Exhibitions`, `Literature & Talks`, `Family & Kids`, `Food & Drink`,
`Sports & Outdoors`, `Markets & Festivals`, `Community & Politics`, `Uni & Science`.

The LLM maps each event to one or more categories; free-form tags stay
searchable. UI filters: category (multi-select), date range, free text, price
(incl. "free only"), venue/area. Filter state lives in the URL so any view is
shareable — and is exactly what the iCal endpoint consumes.

---

## 7. LLM layer (implementation-agnostic)

- Single `LLMClient` interface: `extractEvents(content, schema)` and
  `classify(event, taxonomy)`. Default impl talks to **OpenRouter**; the
  interface lets us drop in any provider or a local model later.
- Config via env: `OPENROUTER_API_KEY`, `LLM_MODEL_EXTRACT`,
  `LLM_MODEL_CLASSIFY` — never hard-code a model.
- Cost/robustness controls: content-hash caching, cheap-first with escalation,
  token caps, JSON-schema validation + bounded retries, structured logging of
  token usage per source so we can see what each source costs.

---

## 8. Tech stack (proposed — open to change, see §11)

- **Language:** TypeScript end-to-end (one language, shared types across
  pipeline/API/UI). Playwright is already provisioned in this environment.
- **App framework:** Next.js (App Router) — serves both the API routes and the
  web UI; deploy as one unit.
- **DB/ORM:** PostgreSQL + Prisma.
- **Scraping:** `undici`/fetch + `cheerio` for static, `rss-parser` /
  `node-ical` for feeds, Playwright for headless.
- **iCal:** `ics` for generation.
- **Validation:** `zod` (doubles as the LLM JSON schema).
- **Scheduling:** cron (platform cron / GitHub Actions / a worker) hitting an
  ingestion entrypoint.
- **Tests:** vitest; golden-file tests for extractors using saved raw HTML so we
  don't hit the network or the LLM in CI.

Alternative worth noting: a separate **Python** scraping service (richer
scraping ecosystem) feeding the same Postgres. Adds a language boundary; only
worth it if scraping gets gnarly. Default to all-TS until it hurts.

---

## 9. iCal export

- Per-filter subscribable feed: `GET /api/ical?categories=music,film&area=jena`
  returns `text/calendar` so users subscribe in Google/Apple Calendar and get
  auto-updates.
- One-off `.ics` download button on any filtered view and on single events.
- Stable UIDs per event so calendar clients update/dedupe correctly.

---

## 10. Phased roadmap

- **Phase 0 — Foundations:** repo scaffold, Postgres + schema/migrations,
  `sources.yaml` format, `LLMClient` against OpenRouter, CI with golden tests.
- **Phase 1 — Vertical slice:** one feed source + one HTML source end-to-end
  (fetch → LLM extract → normalize → store). Prove the pipeline on real Jena
  data.
- **Phase 2 — Product surface:** API + web UI with browse/filter, plus iCal
  export. Now it's usable.
- **Phase 3 — Scale & quality:** add many sources, dedupe across them, LLM
  classification into the taxonomy, geocoding, scheduling/monitoring,
  per-source health dashboard.
- **Phase 4 — "I feel lucky" (separate spec):** see §12.

Recommend building Phases 0–2 as the first milestone — that's a real,
shippable, useful site.

---

## 11. Decisions (locked)

1. **Stack:** TypeScript **+** Python. Python owns the ingestion service
   (fetch → LLM extract → normalize → dedupe → store); TypeScript/Next.js owns
   the API + web UI. They share one Postgres. DB schema is the contract between
   them — owned by SQL migrations in `db/migrations` so neither side drifts.
2. **Hosting:** single VPS, everything in Docker Compose (postgres + scraper +
   web). No managed cloud dependency.
3. **Region for v1:** Jena, Weimar, Apolda. `region` field carries the value;
   sources are tagged per city.
4. **First sources:** a vertical slice — one feed source (RSS/iCal) + one HTML
   venue — to prove the whole pipeline end-to-end before scaling breadth.

---

## 12. "I feel lucky" (Phase 4 — sketch, not committed)

Inspired by Berlin concert-ticket subscriptions: surprise you with a ticket to
get you out. Hard parts are mostly *outside* aggregation:

- **Payment:** real money → needs accounts, a payment provider (Stripe), spend
  limits, refunds policy, and clear consent before each purchase.
- **Buying:** almost no venues offer a purchase API. Automating checkout on
  third-party ticket sites is brittle and usually against their ToS — risky.
  More realistic first step: **affiliate/deep-link "surprise me"** that picks a
  random event matching your interests/budget/date and hands you off to buy,
  optionally pre-filling. True auto-buy only where a real API or partnership
  exists.
- **Preferences:** budget cap, categories, radius, blackout dates, how often.

Treat this as its own project once the aggregator is solid.

---

## Next step

Answer the four questions in §11 and I'll scaffold Phase 0 (repo structure,
schema, `sources.yaml`, and the OpenRouter `LLMClient`) on this branch.
