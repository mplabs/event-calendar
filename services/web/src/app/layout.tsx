import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Jena Events',
  description: 'Veranstaltungen in Jena, Weimar und Apolda',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className="bg-white text-gray-900 antialiased">{children}</body>
    </html>
  )
}
