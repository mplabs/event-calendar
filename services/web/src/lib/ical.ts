type IcalEvent = {
  title: string
  description: string | null
  startsAt: Date
  endsAt: Date | null
  allDay: boolean
  url: string | null
  dedupeHash: string
  venue?: { name: string } | null
}

function esc(s: string): string {
  return s.replace(/\\/g, '\\\\').replace(/,/g, '\\,').replace(/;/g, '\\;').replace(/\r?\n/g, '\\n')
}

function fold(s: string): string {
  const out: string[] = []
  while (s.length > 75) { out.push(s.slice(0, 75)); s = ' ' + s.slice(75) }
  return [...out, s].join('\r\n')
}

function dt(d: Date): string {
  return d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
}

export function buildIcal(events: IcalEvent[], stamp: Date): string {
  const lines: string[] = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Jena Events//events.dronechronicles.de//DE',
    'X-WR-CALNAME:Jena Events',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
  ]

  for (const e of events) {
    const vevent: string[] = [
      'BEGIN:VEVENT',
      fold(`UID:${e.dedupeHash}@events.dronechronicles.de`),
      `DTSTART:${dt(e.startsAt)}`,
      ...(e.endsAt ? [`DTEND:${dt(e.endsAt)}`] : []),
      fold(`SUMMARY:${esc(e.title)}`),
      ...(e.description ? [fold(`DESCRIPTION:${esc(e.description)}`)] : []),
      ...(e.url ? [fold(`URL:${e.url}`)] : []),
      ...(e.venue?.name ? [fold(`LOCATION:${esc(e.venue.name)}`)] : []),
      `DTSTAMP:${dt(stamp)}`,
      'END:VEVENT',
    ]
    lines.push(...vevent)
  }

  lines.push('END:VCALENDAR')
  return lines.join('\r\n')
}
