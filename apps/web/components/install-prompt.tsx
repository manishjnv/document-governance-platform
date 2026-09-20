'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    const handler = (event: Event) => {
      event.preventDefault()
      setDeferredPrompt(event as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  if (!deferredPrompt || dismissed) return null

  return (
    <div
      role="status"
      className="app-theme font-app fixed bottom-4 left-1/2 z-[70] flex w-[calc(100%-32px)] max-w-[400px] -translate-x-1/2 items-center justify-between gap-2.5 rounded-lg border border-border bg-card py-2 pl-3 pr-2 text-[13px] text-foreground shadow-card"
    >
      <span>Install ScopeSense for offline access</span>
      <div className="flex shrink-0 gap-1.5">
        <Button
          size="sm"
          onClick={async () => {
            await deferredPrompt.prompt()
            await deferredPrompt.userChoice
            setDeferredPrompt(null)
          }}
        >
          Install
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setDismissed(true)}>
          Dismiss
        </Button>
      </div>
    </div>
  )
}
