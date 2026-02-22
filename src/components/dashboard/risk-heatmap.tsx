"use client";

import { motion } from "framer-motion";

interface DepartmentRisk {
  department: string;
  critical: number;
  high: number;
  medium: number;
  riskScore: number;
}

interface RiskHeatmapProps {
  data: DepartmentRisk[];
}

/* Pastel legend colors: low risk = Light Teal, Pale Blue, Muted Yellow, Soft Peach, high = Soft Coral */
function getRiskColor(score: number) {
  if (score >= 70) return "bg-[#f7b7a3]";
  if (score >= 50) return "bg-[#f4c6a8]";
  if (score >= 30) return "bg-[#efd88a]";
  if (score >= 15) return "bg-[#c8ddf2]";
  return "bg-[#a9d7d3]";
}

export function RiskHeatmap({ data }: RiskHeatmapProps) {
  const maxScore = Math.max(...data.map((d) => d.riskScore), 1);

  if (data.length === 0) {
    return (
      <div className="flex min-h-[120px] items-center justify-center rounded-lg border border-dashed border-border/50 bg-muted/20 py-8">
        <p className="text-sm text-muted-foreground">No department risk data yet. Run a scan to see risk by department.</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="space-y-3"
    >
      {data.map((dept, index) => (
        <motion.div
          key={dept.department}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.3 + index * 0.05 }}
          className="space-y-2"
        >
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{dept.department}</span>
            <span className="text-muted-foreground">
              {dept.riskScore}%
              {dept.critical > 0 && (
                <span className="ml-2 text-red-400">
                  {dept.critical} critical
                </span>
              )}
            </span>
          </div>
          <div className="flex h-2 gap-1 overflow-hidden rounded-full bg-muted/50">
            <motion.div
              initial={{ width: 0 }}
              animate={{
                width: `${(dept.riskScore / maxScore) * 100}%`,
              }}
              transition={{ duration: 0.8, delay: 0.4 + index * 0.05 }}
              className={`h-full rounded-full ${getRiskColor(dept.riskScore)}`}
            />
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
