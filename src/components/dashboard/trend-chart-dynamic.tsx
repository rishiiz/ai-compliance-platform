"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

const TrendChartInner = dynamic(
  () => import("./trend-chart").then((m) => m.TrendChart),
  {
    ssr: false,
    loading: () => (
      <Skeleton className="h-[300px] min-h-[300px] w-full min-w-0 rounded-lg" />
    ),
  }
);

interface TrendChartProps {
  data: { date: string; score: number; violations: number }[];
}

export function TrendChart(props: TrendChartProps) {
  return <TrendChartInner {...props} />;
}
