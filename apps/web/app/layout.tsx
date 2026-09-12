import type { Metadata } from 'next'
import Script from 'next/script'
import { Inter } from 'next/font/google'
import './globals.css'
import { ServiceWorkerRegister } from '@/components/service-worker-register'
import { InstallPrompt } from '@/components/install-prompt'
import { CtaClickTracker } from '@/components/CtaClickTracker'

const inter = Inter({ subsets: ['latin'], display: 'swap', variable: '--font-inter' })

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
    <html lang="en" className={inter.variable}>
      <body>
        {GA_MEASUREMENT_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
              strategy="afterInteractive"
            />
            <Script id="ga4-init" strategy="afterInteractive">
              {`window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${GA_MEASUREMENT_ID}');`}
            </Script>
          </>
        )}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
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
