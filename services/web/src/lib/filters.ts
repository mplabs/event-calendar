import type { Prisma } from '@prisma/client'

export type Filters = {
  q: string
  categories: string[]
  area: string | null
  from: Date
  to: Date | null
  free: boolean
}

function todayUtcMidnight(): Date {
  const d = new Date()
  d.setUTCHours(0, 0, 0, 0)
  return d
}

export function parseSearchParams(
  params: Record<string, string | string[] | undefined>
): Filters {
  const str = (k: string) => (Array.isArray(params[k]) ? (params[k] as string[])[0] : (params[k] as string | undefined)) ?? ''
  const arr = (k: string): string[] => {
    const v = params[k]
    if (!v) return []
    return Array.isArray(v) ? v : [v]
  }
  return {
    q: str('q'),
    categories: arr('category'),
    area: str('area') || null,
    from: str('from') ? new Date(str('from')) : todayUtcMidnight(),
    to: str('to') ? new Date(str('to')) : null,
    free: str('free') === '1',
  }
}

export function parseURLSearchParams(sp: URLSearchParams): Filters {
  return {
    q: sp.get('q') ?? '',
    categories: sp.getAll('category'),
    area: sp.get('area'),
    from: sp.get('from') ? new Date(sp.get('from')!) : todayUtcMidnight(),
    to: sp.get('to') ? new Date(sp.get('to')!) : null,
    free: sp.get('free') === '1',
  }
}

export function buildWhere(f: Filters): Prisma.EventWhereInput {
  const where: Prisma.EventWhereInput = {
    status: 'active',
    startsAt: f.to ? { gte: f.from, lte: f.to } : { gte: f.from },
  }
  if (f.area) where.region = f.area
  if (f.categories.length) where.categories = { hasSome: f.categories }
  if (f.q) where.OR = [
    { title: { contains: f.q, mode: 'insensitive' } },
    { description: { contains: f.q, mode: 'insensitive' } },
  ]
  if (f.free) where.priceMin = { equals: 0 }
  return where
}
