# Web app (TypeScript / Next.js) — Phase 2

Not built yet. This is where the public surface lives once the ingestion
pipeline (`services/scraper`) is proven on real Jena/Weimar/Apolda data.

Planned scope (see ../../PLAN.md §6, §8, §9):

- **Next.js (App Router)** serving both the JSON API and the web UI.
- **Prisma** pointed at the same Postgres the scraper writes to. The DB schema
  is owned by `db/migrations/*.sql` (the contract); Prisma introspects it
  (`prisma db pull`) rather than owning migrations, so the two services can't
  drift.
- **Browse / filter** by category (taxonomy), date range, free text, price
  ("free only"), and area (jena / weimar / apolda). Filter state lives in the
  URL so any view is shareable.
- **iCal export**: `GET /api/ical?categories=music,film&area=jena` returns
  `text/calendar` (subscribable), plus a one-off `.ics` download per view/event.
  Use stable per-event UIDs (the event `dedupe_hash`) so calendar clients
  update/dedupe correctly.

When ready, uncomment the `web` service in `../../docker-compose.yml`.
