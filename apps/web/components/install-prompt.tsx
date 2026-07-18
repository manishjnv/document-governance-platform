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
      className="fixed bottom-4 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 items-center justify-between gap-3 rounded-md border border-border bg-background px-3 py-2 text-sm shadow-sm"
    >
      <span>Install Scopewise for offline access</span>
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
