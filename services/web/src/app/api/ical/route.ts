import type { NextRequest } from 'next/server'
import { db } from '@/lib/db'
import { parseURLSearchParams, buildWhere } from '@/lib/filters'
import { buildIcal } from '@/lib/ical'

export async function GET(req: NextRequest) {
  const filters = parseURLSearchParams(req.nextUrl.searchParams)
  const events = await db.event.findMany({
    where: buildWhere(filters),
    include: { venue: true },
    orderBy: { startsAt: 'asc' },
    take: 500,
  })

  return new Response(buildIcal(events, new Date()), {
    headers: {
      'Content-Type': 'text/calendar; charset=utf-8',
      'Content-Disposition': 'attachment; filename="jena-events.ics"',
      'Cache-Control': 'public, max-age=3600',
    },
  })
}
