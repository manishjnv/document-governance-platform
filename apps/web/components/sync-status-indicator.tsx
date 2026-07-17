'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export function SyncStatusIndicator() {
  // ponytail: navigator.onLine as initial state avoids an offline flash on first paint.
  const [online, setOnline] = useState(
    typeof navigator === 'undefined' ? true : navigator.onLine
  )

  useEffect(() => {
    const goOnline = () => setOnline(true)
    const goOffline = () => setOnline(false)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  return (
    <Badge variant={online ? 'secondary' : 'destructive'} className="gap-1.5">
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          online ? 'bg-emerald-500' : 'bg-current'
        )}
      />
      {online ? 'Online' : 'Offline'}
    </Badge>
  )
}
