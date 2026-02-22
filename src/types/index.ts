// Shared types for API responses and app state (backend-friendly)

export interface Policy {
  id: string;
  name: string;
  version: string;
  status: string;
  uploadDate: string;
  department: string;
  rulesCount: number;
  lastReviewed: string | null;
}

export interface Rule {
  id: string;
  policyId: string;
  policyName: string;
  clause: string;
  severity: string;
  status: string;
  version: string;
  department: string;
  createdAt: string;
  category: string;
}

export interface Violation {
  id: string;
  ruleId: string;
  policyId: string;
  policyName: string;
  clause: string;
  severity: string;
  department: string;
  discoveredAt: string;
  status: string;
  evidence: string;
  aiExplanation: string;
  suggestedRemediation?: string;
  affectedResource: string;
  assignee: string;
}

export interface TrendDataPoint {
  date: string;
  score: number;
  violations: number;
}

export interface DepartmentRisk {
  department: string;
  critical: number;
  high: number;
  medium: number;
  riskScore: number;
}

export interface RecentViolationSummary {
  id: string;
  severity: string;
  department: string;
  description: string;
}

export interface ReportMetrics {
  policiesReviewed: number;
  violationsResolved: number;
  averageResolutionTime: string;
  complianceTrend: string;
}

export interface Analytics {
  complianceScore: number;
  totalPolicies: number;
  activeViolations: number;
  criticalAlerts: number;
  trendData: TrendDataPoint[];
  departmentRiskHeatmap: DepartmentRisk[];
  recentViolations: RecentViolationSummary[];
  reportMetrics: ReportMetrics;
}

// Auth (for backend login)
export interface LoginCredentials {
  email: string;
  password: string;
  role?: string;
}

export interface AuthUser {
  name: string;
  role: string;
  email: string;
  department: string;
}

export interface LoginResponse {
  user: AuthUser;
  token?: string;
}

export interface NotificationItem {
  id: string;
  type: "critical" | "warning" | "success" | "info";
  title: string;
  body: string | null;
  policy_name?: string;
  read: boolean;
  createdAt: string;
}
