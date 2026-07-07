import type { Prisma } from '@prisma/client'
import { db } from '@/lib/db'
import { parseSearchParams, buildWhere } from '@/lib/filters'

const REGIONS = [
  { value: '', label: 'Alle Regionen' },
  { value: 'jena', label: 'Jena' },
  { value: 'weimar', label: 'Weimar' },
  { value: 'apolda', label: 'Apolda' },
]

type Event = Prisma.EventGetPayload<{ include: { venue: true } }>

function formatDay(d: Date): string {
  return d.toLocaleDateString('de-DE', {
    timeZone: 'Europe/Berlin',
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatTime(d: Date, allDay: boolean): string {
  if (allDay) return 'Ganztägig'
  return d.toLocaleTimeString('de-DE', {
    timeZone: 'Europe/Berlin',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function dayKey(d: Date): string {
  return d.toLocaleDateString('en-CA', { timeZone: 'Europe/Berlin' }) // YYYY-MM-DD
}

function EventCard({ event }: { event: Event }) {
  const price =
    event.priceMin === null
      ? null
      : event.priceMin.toNumber() === 0
      ? 'kostenlos'
      : `ab ${event.currency} ${event.priceMin.toFixed(0)}`

  return (
    <article className="flex gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
      <div className="w-16 shrink-0 text-sm font-mono text-gray-400 pt-0.5 text-right">
        {formatTime(event.startsAt, event.allDay)}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-medium leading-snug">
          {event.url ? (
            <a href={event.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
              {event.title}
            </a>
          ) : (
            event.title
          )}
        </h3>
        {event.venue && (
          <p className="text-sm text-gray-500 mt-0.5">{event.venue.name}</p>
        )}
        {(event.categories.length > 0 || price) && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {event.categories.map(c => (
              <span key={c} className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full">
                {c}
              </span>
            ))}
            {price && (
              <span className={`text-xs px-2 py-0.5 rounded-full border ${
                price === 'kostenlos'
                  ? 'bg-green-50 text-green-700 border-green-200'
                  : 'bg-gray-50 text-gray-600 border-gray-200'
              }`}>
                {price}
              </span>
            )}
          </div>
        )}
      </div>
    </article>
  )
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const sp = await searchParams
  const filters = parseSearchParams(sp)

  const [events, cats] = await Promise.all([
    db.event.findMany({
      where: buildWhere(filters),
      include: { venue: true },
      orderBy: { startsAt: 'asc' },
      take: 200,
    }),
    db.$queryRaw<{ category: string }[]>`
      SELECT DISTINCT unnest(categories) AS category FROM event ORDER BY 1
    `,
  ])

  // Group events by calendar day in Berlin timezone
  const days = new Map<string, { label: string; events: Event[] }>()
  for (const e of events) {
    const k = dayKey(e.startsAt)
    if (!days.has(k)) days.set(k, { label: formatDay(e.startsAt), events: [] })
    days.get(k)!.events.push(e)
  }

  // iCal URL mirrors current filters
  const icalParams = new URLSearchParams()
  if (filters.q) icalParams.set('q', filters.q)
  if (filters.area) icalParams.set('area', filters.area)
  if (filters.free) icalParams.set('free', '1')
  filters.categories.forEach(c => icalParams.append('category', c))
  const icalUrl = `/api/ical?${icalParams}`

  return (
    <main className="max-w-3xl mx-auto px-4 py-8">
      <header className="mb-6 flex items-baseline justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">Jena Events</h1>
        <a href={icalUrl} className="text-sm text-blue-600 hover:underline shrink-0">
          Kalender abonnieren
        </a>
      </header>

      <form method="GET" className="mb-8 space-y-3 bg-gray-50 p-4 rounded-xl border border-gray-200">
        <div className="flex gap-2">
          <input
            name="q"
            defaultValue={filters.q}
            placeholder="Suchen…"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            name="area"
            defaultValue={filters.area ?? ''}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            {REGIONS.map(r => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>

        {cats.length > 0 && (
          <div className="flex flex-wrap gap-3">
            {cats.map(({ category }) => (
              <label key={category} className="flex items-center gap-1.5 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  name="category"
                  value={category}
                  defaultChecked={filters.categories.includes(category)}
                  className="rounded border-gray-300"
                />
                {category}
              </label>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-3 items-center">
          <label className="flex items-center gap-1.5 text-sm">
            Von
            <input
              type="date"
              name="from"
              defaultValue={filters.from.toISOString().slice(0, 10)}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
            />
          </label>
          <label className="flex items-center gap-1.5 text-sm">
            Bis
            <input
              type="date"
              name="to"
              defaultValue={filters.to?.toISOString().slice(0, 10) ?? ''}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
            />
          </label>
          <label className="flex items-center gap-1.5 text-sm cursor-pointer">
            <input
              type="checkbox"
              name="free"
              value="1"
              defaultChecked={filters.free}
              className="rounded border-gray-300"
            />
            Kostenlos
          </label>
          <button
            type="submit"
            className="ml-auto px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors"
          >
            Suchen
          </button>
        </div>
      </form>

      {days.size === 0 ? (
        <p className="text-gray-400 text-center py-16">Keine Veranstaltungen gefunden.</p>
      ) : (
        Array.from(days.values()).map(({ label, events: dayEvents }) => (
          <section key={label} className="mb-8">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              {label}
            </h2>
            <div className="space-y-2">
              {dayEvents.map(e => <EventCard key={e.id} event={e} />)}
            </div>
          </section>
        ))
      )}
    </main>
  )
}
