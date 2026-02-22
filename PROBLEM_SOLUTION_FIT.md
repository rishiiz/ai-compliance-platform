# Problem–Solution Fit: Challenge vs This Platform

This document maps the **hackathon challenge requirements** to your **AI Compliance Platform** to show that your website is a direct solution to the same problem.

---

## The Challenge (Problem Statement)

> Build a **software-only solution** that ingests **free-text PDF policy documents** and **connects to a company database**. It should **automatically identify records that violate compliance rules and business policies**. **Optional human oversight** can be incorporated during the data analysis phase. The agent must support **periodic monitoring** to detect future policy violations.

**Mission:**

1. **Ingest and interpret PDF policy documents** to extract **actionable compliance rules**
2. **Connect to and scan a company database** for compliance and business rule violations
3. **Flag detected violations** with **clear, explainable justifications**
4. **Incorporate human review and intervention** wherever needed
5. **Periodically monitor** data for new or recurring violations

**Optional:** Suggest remediation, summarize compliance/trends, dashboards/reporting, audit-ready reports.

**Key focus:** Accurate, explainable, and continuous data policy enforcement with actionable insights.

---

## How Your Platform Matches (Solution Mapping)

| # | Challenge requirement | Your platform solution | Where it lives |
|---|------------------------|------------------------|----------------|
| 1 | **Ingest and interpret PDF policy documents → actionable compliance rules** | Upload PDF → PyMuPDF extracts text → OpenAI extracts structured rules (entity, field, condition, operator, value, severity, policy_clause_text) → validated and stored | **POST /policy/upload**, `pdf_service.py`, `rule_extractor.py`, `rule_data` schema |
| 2 | **Connect to and scan a company database for violations** | Configure external DB (host, user, password, db name) → run scan → rule engine compiles rules to SQL and executes against that DB → violating rows stored as violations | **POST /database/connect**, **POST /scan/run**, `rule_engine.py`, `scan_service.py` |
| 3 | **Flag violations with clear, explainable justifications** | Each violation has `explanation` (AI-generated via OpenAI) and `evidence_snapshot` (row data); policy clause text linked from rule | `explanation_service.py`, Violation model, **GET /violations**, Review/UI |
| 4 | **Human review and intervention** | Review page: approve/dismiss violations, add reviewer notes; full audit trail per violation; status (pending/approved/dismissed) | **PATCH /violations/:id**, **GET /violations/:id/audit**, Review page, AuditLog |
| 5 | **Periodic monitoring for new/recurring violations** | Scheduler runs compliance scan on an interval (e.g. 24h); new violations created, previously resolved violations re-flagged if they reappear | `scheduler/jobs.py`, `run_scan()`, ScanState, **GET /dashboard/summary** |
| — | **Software-only, no hardware** | Entire stack is software: Next.js, FastAPI, PostgreSQL, optional external DB, OpenAI API, PyMuPDF | All codebase |
| — | **Accurate, explainable, continuous, actionable** | Rules from policy + validated schema; explanations per violation; scheduler + on-demand scan; dashboard, reports, export | End-to-end flow |

---

## Optional Features (Challenge Says “You May Optionally Add”)

| Optional feature | Your platform | Status |
|------------------|----------------|--------|
| **Suggest remediation steps** for detected violations | AI-generated suggested_remediation per violation; shown on Violations and Review pages | Implemented “suggested remediation” |
| **Summarize compliance status and trends over time** | Dashboard: compliance score, total policies, violations, critical alerts; trend chart (data-driven when scan history exists) | ✅ Implemented |
| **Present findings via dashboards or automated reporting** | Dashboard (KPIs, recent violations, risk heatmap), Reports page, CSV/PDF export | ✅ Implemented |
| **Generate audit-ready compliance reports** | **GET /reports/export/csv**, **GET /reports/export/pdf**; full audit log (**GET /audit**, **GET /profile/activity**, **GET /violations/:id/audit**) | ✅ Implemented |
| **Policy change impact** (optional differentiator) | **GET /policy/compare**: compare two policy versions (rules only in old, only in new, in both) and estimated new violations if new policy adopted (when DB connected) | ✅ Implemented |

---

## End-to-End Flow (How It Solves the Problem)

```
PDF policy (free text)
        ↓
   [Upload] POST /policy/upload
        ↓
   Extract text (PyMuPDF) → Extract rules (OpenAI) → Validate (schema) → Store Policy + Rules
        ↓
   [Connect DB] POST /database/connect  (company DB)
        ↓
   [Scan] POST /scan/run  or  Scheduler (periodic)
        ↓
   For each rule: compile to SQL → run on company DB → violating rows
        ↓
   For each violation: AI explanation + evidence snapshot → Store Violation
        ↓
   [Human oversight] Review page: approve/dismiss, add notes; audit trail
        ↓
   [Insights] Dashboard, Reports, CSV/PDF export, Notifications
```

---

## One-Sentence Fit

**Your platform is a software-only solution that (1) ingests PDF policies and extracts actionable compliance rules with AI, (2) connects to a company database and scans it for violations, (3) flags each violation with an AI-generated explanation and evidence, (4) supports human review and audit trail, and (5) runs periodic scans to detect new or recurring violations—plus dashboards, reporting, and audit-ready exports.**

All optional items from the challenge are covered: **suggested remediation steps** per violation, **policy change impact** (compare versions and estimated new violations), dashboards, reporting, and audit-ready exports.
