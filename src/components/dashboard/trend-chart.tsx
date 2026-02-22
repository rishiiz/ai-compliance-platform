"use client";

import { motion } from "framer-motion";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { useTheme } from "@/contexts/theme-context";

interface TrendChartProps {
  data: { date: string; score: number; violations: number }[];
}

const tooltipStyleLight = {
  backgroundColor: "rgba(255, 255, 255, 0.98)",
  border: "1px solid rgba(228, 228, 231, 0.9)",
  borderRadius: "8px",
};
const tooltipStyleDark = {
  backgroundColor: "rgba(24, 24, 32, 0.95)",
  border: "1px solid rgba(63, 63, 70, 0.8)",
  borderRadius: "8px",
};

export function TrendChart({ data }: TrendChartProps) {
  const { theme } = useTheme();
  const chartData = data.map((d) => {
    const dt = new Date(d.date);
    const isHourly =
      data.length >= 12 &&
      data.every((x, i) => !i || new Date(x.date).getTime() - new Date(data[i - 1].date).getTime() <= 3660000);
    const shortDate = isHourly
      ? `${String(dt.getUTCHours()).padStart(2, "0")}:00`
      : dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    return { ...d, shortDate };
  });

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="h-[300px] min-h-[300px] w-full min-w-0"
    >
      <ResponsiveContainer width="100%" height={300} minHeight={300}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.6} />
              <stop offset="100%" stopColor="var(--chart-2)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
          <XAxis
            dataKey="shortDate"
            className="text-xs"
            stroke="currentColor"
            tick={{ fill: "currentColor" }}
          />
          <YAxis
            domain={[0, 100]}
            className="text-xs"
            stroke="currentColor"
            tick={{ fill: "currentColor" }}
          />
          <Tooltip
            contentStyle={theme === "dark" ? tooltipStyleDark : tooltipStyleLight}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="rounded-md border bg-card px-3 py-2 text-sm shadow-md">
                  <p className="font-medium">{payload[0]?.payload?.shortDate}</p>
                  <p>Score: {payload[0]?.value ?? 0}</p>
                  <p>Violations: {payload[0]?.payload?.violations ?? 0}</p>
                </div>
              ) : null
            }
          />
          <Area
            type="monotone"
            dataKey="score"
            stroke="var(--primary)"
            strokeWidth={2}
            fill="url(#scoreGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  );
}
