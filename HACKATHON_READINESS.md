# Hackathon readiness – what’s real vs mock

This doc summarizes what is **driven by the backend and database** (suitable for a live demo) and how to test the full flow.

---

## Data source summary

| Feature | Data source | Notes |
|--------|-------------|--------|
| **Login** | Backend `POST /auth/login` | Requires password. Default: `admin@company.com` / `Admin@123`. |
| **Dashboard KPIs** | Backend `GET /dashboard/summary` | Compliance score, total policies, active violations, critical alerts, recent violations – all from DB. No hardcoded “vs last month” trends. |
| **Notifications (bell)** | Backend `GET /notifications`, `PATCH /.../read` | Real list; “Welcome” seeded on first run; “Policy uploaded” created when you upload a PDF. |
| **Policy upload** | Backend `POST /policy/upload` | Real file upload → PDF text extraction → OpenAI rule extraction → stored in DB. Extracted rules shown in UI. |
| **Policies list** | Backend `GET /policy` | From DB. |
| **Rules list** | Backend `GET /rules` | From DB. |
| **Violations list** | Backend `GET /violations` | From DB (populated by scans or manually). |
| **Review (approve/dismiss)** | Backend `PATCH /violations/:id` | Status and notes saved to DB. |
| **Reports export** | Backend `GET /reports/export/csv` and `/pdf` | From DB. |
| **Settings / Users** | Backend `GET/PATCH /settings`, `GET/POST /users` | From DB. |

When `NEXT_PUBLIC_API_URL` is **not** set, the frontend falls back to empty/mock data (e.g. 0 policies, no notifications, mock login).

---

## How to test end-to-end (full stack)

1. **Start backend**
   - From `backend/`: `pip install -r requirements.txt`, set `backend/.env` (`DATABASE_URL`, `OPENAI_API_KEY`), then:
   - `uvicorn app.main:app --reload --port 8000`

2. **Start frontend**
   - In project root: `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - `npm install && npm run dev`

3. **Login**
   - Go to `/login`, sign in with `admin@company.com` / `Admin@123`. Empty or wrong password should show an error.

4. **Dashboard**
   - You should see **0** policies, **0** violations, **100%** compliance (no data yet). Numbers come from the API.

5. **Upload a policy**
   - Go to **Upload policy**, choose `backend/sample-policy.pdf` (or any PDF). Upload runs against `POST /policy/upload`. After success you should see extracted rules in the UI and a new “Policy uploaded” notification in the bell.

6. **Dashboard after upload**
   - Refresh or re-open dashboard: **Total policies** and **Total rules** should increase. **Recent violations** may still be 0 until a scan runs.

7. **Notifications**
   - Open the bell: at least “Welcome” and, after an upload, “Policy uploaded”. Clicking a notification marks it read (calls backend).

8. **Violations and review**
   - If you have an external DB connected and ran **POST /scan/run**, violations appear under **Violations** and **Review**. You can approve/dismiss; changes are persisted.

9. **Reports**
   - **Reports** page and CSV/PDF export use data from the same backend endpoints.

---

## Database

- **Main DB (PostgreSQL):** All app data (policies, rules, violations, users, notifications, audit logs, settings). Required for a “fully working” demo.
- **External DB (optional):** Only needed to **run scans** and generate violations from your data. Without it, you can still demo: login, upload PDF, view policies/rules, dashboard counts, notifications, and reports.

---

## Verdict for hackathon

- **Authentication:** Real (password required; default admin seeded).
- **Dashboard:** Real counts and recent violations from DB; no fake trend text.
- **Notifications:** Real (from DB; seeded + created on policy upload).
- **Policy upload:** Real (PDF → backend → extraction → DB; UI shows extracted rules).
- **Policies / Rules / Violations / Review / Reports / Settings:** All backed by the API and DB.

For an international hackathon, the app is **suitable as a full-stack demo** as long as the backend and main database are running and `NEXT_PUBLIC_API_URL` is set. Use the sample PDF to demonstrate upload and rule extraction, and (if you have time) connect an external DB and run a scan to show violations and review flow.
