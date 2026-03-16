import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const alertVariants = cva('rounded-xl border p-4 text-sm leading-6', {
  variants: {
    variant: {
      default: 'border-accent/40 bg-accent-soft/35 text-foreground',
      danger: 'border-danger/40 bg-danger/10 text-danger',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {}

export function Alert({ className, variant, ...props }: AlertProps) {
  return <div className={cn(alertVariants({ variant }), className)} role="alert" {...props} />
}
