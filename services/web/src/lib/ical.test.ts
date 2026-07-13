import { expect, test } from 'vitest'
import { buildIcal } from './ical'

test('escapes special chars, folds long lines, formats UTC DTSTART', () => {
  const desc = 'x'.repeat(100) // >75 chars, forces folding
  const ics = buildIcal(
    [
      {
        title: 'Rock, Pop\nand more',
        description: desc,
        startsAt: new Date('2026-03-14T09:05:00Z'),
        endsAt: null,
        allDay: false,
        url: null,
        dedupeHash: 'abc123',
        venue: null,
      },
    ],
    new Date('2026-03-14T09:05:00Z'),
  )

  // comma and newline escaped in SUMMARY
  expect(ics).toContain('SUMMARY:Rock\\, Pop\\nand more')
  // UTC DTSTART stamp for the known input
  expect(ics).toContain('DTSTART:20260314T090500Z')
  // long DESCRIPTION line folded: CRLF + leading space, first chunk is 75 octets
  expect(ics).toContain('DESCRIPTION:' + 'x'.repeat(63) + '\r\n ' + 'x'.repeat(12))
})
