import type { Metadata } from 'next'
import './globals.css'
import { ServiceWorkerRegister } from '@/components/service-worker-register'
import { InstallPrompt } from '@/components/install-prompt'

export const metadata: Metadata = {
  title: 'EDGP',
  description: 'Enterprise Document Governance Platform',
  manifest: '/manifest.json',
  themeColor: '#0066cc',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ServiceWorkerRegister />
        {children}
        <InstallPrompt />
      </body>
    </html>
  )
}
