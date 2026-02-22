"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";
import { useEffect, useState } from "react";

interface KpiCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: { value: number; label: string };
  delay?: number;
  className?: string;
  gradient?: boolean;
}

export function KpiCard({
  title,
  value,
  icon,
  trend,
  delay = 0,
  className,
  gradient = false,
}: KpiCardProps) {
  // Animate number if it's numeric
  const numericValue = typeof value === "number" ? value : parseFloat(String(value).replace(/[^0-9.-]/g, ""));
  const isNumeric = !isNaN(numericValue);
  const [displayValue, setDisplayValue] = useState(isNumeric ? 0 : value);

  useEffect(() => {
    if (!isNumeric) return;

    const startTime = Date.now() + (delay * 1000);
    const duration = 800;

    const animate = () => {
      const now = Date.now();
      const elapsed = now - startTime;

      if (elapsed < 0) {
        requestAnimationFrame(animate);
        return;
      }

      if (elapsed < duration) {
        const progress = elapsed / duration;
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        const current = eased * numericValue;

        if (typeof value === "string" && value.includes("%")) {
          setDisplayValue(`${Math.round(current)}%`);
        } else if (typeof value === "string" && value.includes(",")) {
          setDisplayValue(Math.round(current).toLocaleString());
        } else {
          setDisplayValue(Math.round(current));
        }
        requestAnimationFrame(animate);
      } else {
        setDisplayValue(value);
      }
    };

    requestAnimationFrame(animate);
  }, [value, delay, isNumeric, numericValue]);

  return (
    <div className="group">
      <Card className={cn("overflow-hidden shadow-sm hover:shadow-md transition-all duration-200 hover:-translate-y-[2px]", className)}>
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-muted-foreground mb-2">{title}</p>
              <p
                className={cn(
                  "text-3xl font-semibold tracking-tight",
                  gradient && "gradient-text"
                )}
              >
                {displayValue}
              </p>
              {trend && (
                <div className="flex items-center gap-1 mt-2">
                  {trend.value >= 0 ? (
                    <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5 text-red-500" />
                  )}
                  <p
                    className={cn(
                      "text-xs font-medium",
                      trend.value >= 0 ? "text-emerald-500" : "text-red-500"
                    )}
                  >
                    {trend.value >= 0 ? "+" : ""}
                    {trend.value}% {trend.label}
                  </p>
                </div>
              )}
            </div>
            <div
              className={cn(
                "rounded-lg p-3 transition-all duration-150",
                gradient
                  ? "bg-primary/15 group-hover:bg-primary/20"
                  : "bg-muted/50 group-hover:bg-muted/60"
              )}
            >
              <span
                className={cn(
                  "flex h-6 w-6 items-center [&>svg]:h-6 [&>svg]:w-6 transition-transform duration-150 group-hover:scale-[1.01]",
                  gradient ? "text-amber-700 dark:text-amber-400" : "text-muted-foreground"
                )}
              >
                {icon}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
