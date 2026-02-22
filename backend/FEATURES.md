# Frontend features vs backend support

## Frontend feature list (from app routes + README)

| # | Feature | Frontend location | Backend before | Backend after (added) |
|---|---------|------------------|----------------|------------------------|
| 1 | Landing page | `/` | N/A | N/A |
| 2 | Login (email, password, role) | `/login` | None (demo only) | POST /auth/login, GET /auth/me |
| 3 | Auth + roles (admin, compliance, viewer) | AuthContext | None | User model + login |
| 4 | Dashboard (score, KPIs, trend, heatmap, recent violations) | `/dashboard` | GET /dashboard/summary ✓ | — |
| 5 | Upload policy (PDF → rules) | `/upload` | POST /policy/upload ✓ | — |
| 6 | Rules list (severity, filters) | `/rules` | GET /rules ✓ | — |
| 7 | Violations list (filters, evidence) | `/violations` | GET /violations ✓ | — |
| 8 | Review (approve/reject + comments) | `/review` | PATCH /violations/:id ✓ | GET /violations/:id/audit |
| 9 | Audit trail (review page) | Review page | None | GET /audit, GET /violations/:id/audit |
| 10 | Reports (analytics + export PDF/CSV) | `/reports` | Dashboard data ✓ | GET /reports/export/csv, /pdf |
| 11 | Profile (user, activity metrics, 2FA) | `/profile` | None | GET /profile/activity, GET /profile/me |
| 12 | Two-factor authentication | Profile card | None | POST /auth/2fa/enable, verify, disable |
| 13 | Recent activity / history | Profile + Review | None | GET /audit, GET /profile/activity |
| 14 | Settings (system, notifications, policy, users) | `/settings` | None | GET/PATCH /settings, GET/POST /users |
| 15 | Notifications (bell, list, read) | Header dropdown | None | GET /notifications, PATCH /notifications/:id/read |
| 16 | Database connect (for scans) | — | POST /database/connect ✓ | — |
| 17 | Scan run | — | POST /scan/run ✓ | — |

## What was added (backend only, no changes to existing code)

| Area | Endpoints | Notes |
|------|-----------|--------|
| **Audit / history** | GET /audit, GET /violations/{id}/audit | Uses existing AuditLog |
| **Notifications** | GET /notifications, PATCH /notifications/{id}/read | New model Notification |
| **Settings** | GET /settings, PATCH /settings | New model AppSettings (key-value) |
| **Reports export** | GET /reports/export/csv, GET /reports/export/pdf | CSV export; PDF returns CSV until reportlab added |
| **Auth** | POST /auth/login, GET /auth/me | New model User; login creates user if missing |
| **2FA** | POST /auth/2fa/enable, POST /auth/2fa/verify, POST /auth/2fa/disable | Requires pyotp; enable returns secret + qr_uri |
| **User management** | GET /users, POST /users | List and add users (Admin) |
| **Profile activity** | GET /profile/activity | Recent AuditLog entries |
