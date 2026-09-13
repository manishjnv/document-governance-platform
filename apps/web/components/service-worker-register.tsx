'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'

export function ServiceWorkerRegister() {
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(null)

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return

    let registration: ServiceWorkerRegistration | undefined

    navigator.serviceWorker.register('/service-worker.js').then((reg) => {
      registration = reg

      // Already-waiting worker from a previous session (e.g. page loaded before it activated).
      if (reg.waiting) setWaitingWorker(reg.waiting)

      reg.addEventListener('updatefound', () => {
        const installing = reg.installing
        if (!installing) return
        installing.addEventListener('statechange', () => {
          if (installing.state === 'installed' && navigator.serviceWorker.controller) {
            setWaitingWorker(installing)
          }
        })
      })
    })

    // T-3065: reload once the newly-activated worker takes control.
    const onControllerChange = () => window.location.reload()
    navigator.serviceWorker.addEventListener('controllerchange', onControllerChange)
    return () =>
      navigator.serviceWorker.removeEventListener('controllerchange', onControllerChange)
  }, [])

  if (!waitingWorker) return null

  return (
    <div
      role="status"
      className="app-theme font-app fixed inset-x-0 top-0 z-[70] flex items-center justify-center gap-3 bg-primary px-4 py-2 text-[13px] text-primary-foreground"
    >
      <span>A new version is available.</span>
      <Button
        size="sm"
        variant="outline"
        className="border-primary-foreground/40 bg-transparent text-primary-foreground hover:bg-primary-foreground/10"
        onClick={() => waitingWorker.postMessage({ type: 'SKIP_WAITING' })}
      >
        Reload
      </Button>
    </div>
  )
}
