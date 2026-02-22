import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/90",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "text-foreground hover:bg-accent",
        warning:
          "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30 dark:border-amber-500/20 hover:bg-amber-500/25",
        success:
          "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 dark:border-emerald-500/20 hover:bg-emerald-500/25",
        critical:
          "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/40 dark:border-red-500/30 hover:bg-red-500/25",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
  VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
