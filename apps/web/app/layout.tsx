import type { Metadata } from 'next'
import Script from 'next/script'
import { IBM_Plex_Mono, IBM_Plex_Sans, Inter } from 'next/font/google'
import './globals.css'
import './app-theme.css'
import { ServiceWorkerRegister } from '@/components/service-worker-register'
import { InstallPrompt } from '@/components/install-prompt'
import { CtaClickTracker } from '@/components/CtaClickTracker'

const inter = Inter({ subsets: ['latin'], display: 'swap', variable: '--font-inter' })
// App-only type (scoped through .app-theme / font-app on the shell and login roots). Latin subset,
// three weights, so the two families add roughly 120 KB; marketing pages keep Inter.
const plex = IBM_Plex_Sans({ subsets: ['latin'], weight: ['400', '500', '600'], display: 'swap', variable: '--font-plex' })
const plexMono = IBM_Plex_Mono({ subsets: ['latin'], weight: ['400', '500'], display: 'swap', variable: '--font-plex-mono' })

const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID

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
    images: [{ url: '/og-default.png', width: 1200, height: 630, alt: 'ScopeWise: evidence-based risk reviews. Contracts, detections, code.' }],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/og-default.png'],
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${plex.variable} ${plexMono.variable}`}>
      <body>
        {GA_MEASUREMENT_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
              strategy="lazyOnload"
            />
            <Script id="ga4-init" strategy="lazyOnload">
              {`window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${GA_MEASUREMENT_ID}');`}
            </Script>
          </>
        )}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-[hsl(var(--primary))] focus:px-3.5 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-none focus:ring-2 focus:ring-offset-2"
        >
          Skip to main content
        </a>
        <ServiceWorkerRegister />
        {GA_MEASUREMENT_ID && <CtaClickTracker />}
        <main id="main-content">{children}</main>
        <InstallPrompt />
      </body>
    </html>
  )
}
