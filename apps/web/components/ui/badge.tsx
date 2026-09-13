import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex h-[22px] items-center gap-1.5 whitespace-nowrap rounded-full border border-transparent px-2 text-xs font-semibold transition-colors duration-150",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground",
        outline: "border-input bg-card text-muted-foreground font-medium",
      },
      tone: {
        crit: "bg-sev-crit-soft text-sev-crit",
        high: "bg-sev-high-soft text-sev-high",
        med: "bg-sev-med-soft text-sev-med",
        low: "bg-sev-low-soft text-sev-low",
        info: "bg-sev-info-soft text-sev-info",
        ok: "bg-ok-soft text-ok",
        neutral: "bg-na text-muted-foreground",
        violet: "bg-violet-soft text-violet",
        demo: "bg-accent text-primary",
        pro: "bg-violet-soft text-violet",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, tone, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, tone }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
