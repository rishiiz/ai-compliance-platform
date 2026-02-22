# AI Compliance Platform – Overview

This document answers: **(1)** What is connected (frontend ↔ backend ↔ database), **(2)** What features exist and how the structure works, **(3)** How to run everything.

---

## 1. What is connected (frontend ↔ backend ↔ database)

### Frontend ↔ Backend

- **Connection:** The frontend calls the backend API when `NEXT_PUBLIC_API_URL` is set (e.g. `http://localhost:8000`).
- **Where:** In the **project root**, create `.env.local` with:
  ```bash
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```
- **CORS:** The backend allows requests from `http://localhost:3000` and `http://127.0.0.1:3000`, so the Next.js app can call the API from the browser.
- **API usage:** `src/lib/api-client.ts` builds the base URL from `NEXT_PUBLIC_API_URL`; `src/api/index.ts` uses it for all data (dashboard, violations, rules, policies, audit, etc.). When the URL is not set, the app returns empty/default data.

### Backend ↔ Database(s)

- **Main database (PostgreSQL):** Used for all app data. The backend connects using `DATABASE_URL` in `backend/.env` (e.g. `postgresql://postgres:1981@localhost/compliance_db`). Tables are created on startup (policies, rules, violations, audit_logs, scan_state, users, notifications, app_settings). If the database does not exist, the backend creates it on first run.
- **External database (optional):** Used only for **compliance scans**. You connect it via **POST /database/connect** (host, username, password, db_name). The backend keeps this connection in memory and uses it when you run **POST /scan/run** (or the scheduled scan) to evaluate rules against your data. The main app (policies, violations, dashboard) always uses the main PostgreSQL DB.

### Summary diagram

```
[Browser]  ←→  Next.js (localhost:3000)  ←→  FastAPI (localhost:8000)  ←→  PostgreSQL (main DB)
                    NEXT_PUBLIC_API_URL              DATABASE_URL
                                                           ↓
                                                    (optional) external DB
                                                    for scans only
```

**So:** Frontend and backend are connected via `NEXT_PUBLIC_API_URL` and CORS. Backend and main database are connected via `DATABASE_URL`. External DB is connected only when you call `/database/connect` and is used only for scans.

---

## 2. Features and how the structure works

### Frontend features (by route)

| Route / area | Feature | Data source when API URL is set |
|--------------|---------|----------------------------------|
| `/` | Landing page | Static |
| `/login` | Login (email, password, role) | Demo auth (backend has POST /auth/login if you wire it) |
| `/dashboard` | Compliance score, KPIs, trend, recent violations | GET /dashboard/summary |
| `/upload` | Upload policy PDF → rules | Can call POST /policy/upload (frontend upload page can be wired) |
| `/rules` | Rules list with severity/filters | GET /rules |
| `/violations` | Violations table, filters, evidence | GET /violations |
| `/review` | Approve/reject violations, comments | GET /violations, PATCH /violations/:id, GET /violations/:id/audit |
| `/reports` | Analytics, export PDF/CSV | GET /dashboard/summary (analytics), GET /reports/export/csv, /pdf |
| `/profile` | User info, activity, 2FA card | GET /profile/activity; auth/2FA via backend when wired |
| `/settings` | System, notifications, policy, users (admin) | GET/PATCH /settings, GET/POST /users when wired |
| Header | Notifications bell | GET /notifications, PATCH /notifications/:id/read when wired |

**Roles:** Admin (full), Compliance Officer (no Settings), Viewer (Dashboard + Reports only). Enforced in the frontend layout/sidebar.

### Backend features (by API area)

| Area | Endpoints | Purpose |
|------|-----------|---------|
| **Health** | GET /health | Checks main DB, external DB, OpenAI key, scheduler |
| **Dashboard** | GET /dashboard/summary | Counts and recent violations for the UI |
| **Policy** | GET /policy, POST /policy/upload | List policies; upload PDF → extract rules → store |
| **Rules** | GET /rules | List rules (optional ?severity=) |
| **Violations** | GET /violations, GET /violations/:id/audit, PATCH /violations/:id | List, audit trail, update status |
| **Database** | POST /database/connect | Store external DB connection for scans |
| **Scan** | POST /scan/run | Run all rules against external DB, upsert violations |
| **Audit** | GET /audit | Global audit log (optional filters) |
| **Notifications** | GET /notifications, PATCH /notifications/:id/read | List and mark read |
| **Settings** | GET /settings, PATCH /settings | Key-value app settings |
| **Reports** | GET /reports/export/csv, GET /reports/export/pdf | Export compliance data |
| **Auth** | POST /auth/login, GET /auth/me | Login and current user |
| **2FA** | POST /auth/2fa/enable, verify, disable | Two-factor for users |
| **Profile** | GET /profile/activity | Recent activity (audit) |
| **Users** | GET /users, POST /users | List and create users (admin) |

**Scheduler:** A background job runs a compliance scan every 24 hours and updates the single `ScanState` row and writes to `AuditLog`.

### How the structure works (and that it’s working)

- **Frontend:** Next.js App Router. `(app)` group = protected routes (auth guard). Data is loaded via `src/api/index.ts` and hooks in `src/api/hooks.ts` (e.g. `useAnalytics`, `useViolations`, `useRules`). All API calls go to `NEXT_PUBLIC_API_URL` when set.
- **Backend:** FastAPI. Routers live under `app/routes/` (dashboard, policy, rules, violations, database, scan, audit, notifications, settings, reports, auth, profile, users). Models under `app/models/` (Policy, Rule, Violation, AuditLog, ScanState, User, Notification, AppSettings). DB session via `get_db`; tables created in `init_db()` on startup.
- **Database:** Main DB holds policies, rules, violations, audit log, scan state, users, notifications, app settings. External DB is only for running rules during a scan.
- **Verification:** Backend has 41 pytest tests (health, all main routes, auth, 2FA, settings, notifications, reports, profile, users, policy/rules/violations lists, connectivity). Run: `cd backend && pytest tests/ -v`. All pass when the repo is in a good state.

So: **frontend pages and header use the API when `NEXT_PUBLIC_API_URL` is set; backend serves all listed endpoints and talks to the main DB (and optional external DB for scans); structure is frontend (Next.js) → backend (FastAPI) → PostgreSQL (and optional external DB). It is built to work end-to-end when run as below.**

---

## 3. How to run it

### Prerequisites

- **Node.js 18+** (for frontend)
- **Python 3.11+** (for backend)
- **PostgreSQL** (for main database)
- **OpenAI API key** (for policy/rule extraction and explanations)

### Step 1: Backend

1. Open a terminal and go to the backend folder:
   ```bash
   cd ai-compliance-platform/backend
   ```
2. (Optional) Create and activate a virtualenv:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1    # Windows PowerShell
   # source venv/bin/activate      # macOS/Linux
   ```
3. Install dependencies and set env:
   ```bash
   pip install -r requirements.txt
   copy .env.example .env          # Windows
   # cp .env.example .env          # macOS/Linux
   ```
   Edit `.env`: set `DATABASE_URL` (e.g. `postgresql://postgres:1981@localhost/compliance_db`) and `OPENAI_API_KEY`.
4. Start the API server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Backend will be at **http://localhost:8000** (docs: http://localhost:8000/docs).

### Step 2: Frontend

1. Open **another** terminal and go to the **project root** (not inside `backend`):
   ```bash
   cd ai-compliance-platform
   ```
2. Set the backend URL so the frontend talks to the API:
   - Create or edit **`.env.local`** in the project root with:
     ```bash
     NEXT_PUBLIC_API_URL=http://localhost:8000
     ```
3. Install and run:
   ```bash
   npm install
   npm run dev
   ```
   Frontend will be at **http://localhost:3000**.

### Step 3: Use the app

- Open **http://localhost:3000**.
- Use **Sign in** or **Access Demo** → log in (any email/password; choose role).
- You’ll land on **Dashboard** (data from backend). Use the sidebar for **Rules**, **Violations**, **Review**, **Reports**, **Profile**, **Settings** (admin), and **Upload**).
- To run compliance scans: connect your data source first via **POST /database/connect** (e.g. from http://localhost:8000/docs), then run **POST /scan/run** or wait for the 24-hour job.

### Optional: Run backend tests

From `backend`:

```bash
pytest tests/ -v
```

You should see **41 passed** (health, routes, new endpoints, schemas, connectivity).

---

## Quick reference

| What | Where | Command / URL |
|------|--------|----------------|
| Frontend | Project root | `npm run dev` → http://localhost:3000 |
| Backend | `backend/` | `uvicorn app.main:app --reload --port 8000` → http://localhost:8000 |
| API docs | Backend | http://localhost:8000/docs |
| Health | Backend | http://localhost:8000/health |
| Connect frontend to backend | Project root | `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| Backend DB | `backend/.env` | `DATABASE_URL=postgresql://...` |
| Backend tests | `backend/` | `pytest tests/ -v` |
