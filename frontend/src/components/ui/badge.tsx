import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const badgeVariants = cva('inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.24em]', {
  variants: {
    variant: {
      default: 'border-accent/40 bg-accent/10 text-accent',
      secondary: 'border-border bg-background/60 text-muted',
      danger: 'border-danger/40 bg-danger/10 text-danger',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
