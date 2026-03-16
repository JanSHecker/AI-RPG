import type { ReactNode } from 'react'

export function PlayChip({
  children,
  variant = 'default',
}: {
  children: ReactNode
  variant?: 'danger' | 'default' | 'muted'
}) {
  return (
    <div className="play-chip" data-variant={variant}>
      {children}
    </div>
  )
}
