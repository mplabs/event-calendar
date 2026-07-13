import { PrismaClient } from '@prisma/client'

function dbUrl(): string {
  const e = encodeURIComponent
  const { POSTGRES_USER: u, POSTGRES_PASSWORD: p, POSTGRES_DB: d, POSTGRES_HOST: h = 'db' } = process.env
  return `postgresql://${e(u!)}:${e(p!)}@${h}:5432/${e(d!)}`
}

const globalForPrisma = global as unknown as { prisma: PrismaClient }

export const db =
  globalForPrisma.prisma ??
  new PrismaClient({ datasources: { db: { url: dbUrl() } } })

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
