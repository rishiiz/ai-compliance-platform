"use client";

interface ComplianceScoreProps {
  score: number;
  size?: number;
  strokeWidth?: number;
}

export function ComplianceScore({
  score,
  size = 160,
  strokeWidth = 12,
}: ComplianceScoreProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;

  const getColor = () => {
    if (score >= 90) return "#22c55e";
    if (score >= 70) return "#6366f1";
    if (score >= 50) return "#f59e0b";
    return "#ef4444";
  };

  return (
    <div className="relative inline-flex items-center justify-center" aria-label={`Compliance score ${score}%`}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle
          className="text-muted/30"
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <circle
          className="stroke-cap-round"
          strokeWidth={strokeWidth}
          stroke={getColor()}
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          strokeLinecap="round"
          style={{
            strokeDasharray: circumference,
            strokeDashoffset: offset,
          }}
        />
      </svg>
      <span className="absolute text-sm font-medium tabular-nums text-foreground">
        {score}%
      </span>
    </div>
  );
}
