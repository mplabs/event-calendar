import { PrismaClient } from '@prisma/client'

function getDatabaseUrl(): string {
  if (process.env.DATABASE_URL) return process.env.DATABASE_URL
  const e = encodeURIComponent
  const { POSTGRES_USER: user, POSTGRES_PASSWORD: pass, POSTGRES_DB: db, POSTGRES_HOST: host = 'db' } = process.env
  return `postgresql://${e(user!)}:${e(pass!)}@${host}:5432/${e(db!)}`
}

const globalForPrisma = global as unknown as { prisma: PrismaClient }

export const db =
  globalForPrisma.prisma ??
  new PrismaClient({ datasources: { db: { url: getDatabaseUrl() } } })

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
