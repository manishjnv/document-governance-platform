import type { Metadata } from 'next'
import './globals.css'
import { ServiceWorkerRegister } from '@/components/service-worker-register'
import { InstallPrompt } from '@/components/install-prompt'

export const metadata: Metadata = {
  metadataBase: new URL('https://scopewise.assessiq.in'),
  title: {
    default: 'ScopeWise -- AI-Powered SOW & RFP Review',
    template: '%s | ScopeWise',
  },
  description: 'Catch contract risk before you sign. AI review of your SOW or RFP for scope, delivery, commercial, security, PMO, and legal risk.',
  manifest: '/manifest.json',
  themeColor: '#0066cc',
  openGraph: {
    siteName: 'ScopeWise',
    type: 'website',
  },
  twitter: {
    card: 'summary',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
        >
          Skip to main content
        </a>
        <ServiceWorkerRegister />
        <main id="main-content">{children}</main>
        <InstallPrompt />
      </body>
    </html>
  )
}
