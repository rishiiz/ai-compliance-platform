"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ChevronRight, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface Violation {
  id: string;
  severity: string;
  department: string;
  description: string;
}

interface RecentViolationsProps {
  violations: Violation[];
}

const severityColors: Record<string, "critical" | "warning" | "default"> = {
  critical: "critical",
  high: "warning",
  medium: "default",
};

export function RecentViolations({ violations }: RecentViolationsProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.4 }}
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <h3 className="font-semibold">Recent Violations</h3>
          <Link
            href="/violations"
            className="text-sm text-primary hover:underline flex items-center gap-1"
          >
            View all
            <ChevronRight className="h-4 w-4" />
          </Link>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {violations.map((violation, index) => (
              <motion.div
                key={violation.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 + index * 0.1 }}
              >
                <Link href={`/violations?id=${violation.id}`}>
                  <div className="flex items-start gap-3 rounded-lg p-3 transition-colors hover:bg-accent/50">
                    <div className="rounded-full bg-destructive/10 p-2">
                      <AlertTriangle className="h-4 w-4 text-destructive" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm line-clamp-1">
                        {violation.description}
                      </p>
                      <div className="mt-1 flex items-center gap-2">
                        <Badge
                          variant={
                            severityColors[violation.severity] || "default"
                          }
                          className="text-xs"
                        >
                          {violation.severity}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {violation.department}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
