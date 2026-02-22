# Demo Guide: How to Show Your Website Running to Judges

Use this as a **script** to run a live demo. Do a quick rehearsal so everything starts smoothly.

---

## Before the Demo (Setup, ~5 min)

### 1. Start the backend

Open a terminal:

```bash
cd backend
pip install -r requirements.txt
```

Create or edit `backend/.env`:

- `DATABASE_URL` = your PostgreSQL connection (e.g. `postgresql://user:password@localhost/compliance_db`)
- `OPENAI_API_KEY` = your OpenAI API key (required for rule extraction and violation explanations)

Start the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Leave this terminal open. You should see: `Uvicorn running on http://0.0.0.0:8000`.

### 2. Start the frontend

Open a **second** terminal, from the **project root** (not inside `backend`):

Create or edit `.env.local` in the project root:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then:

```bash
npm install
npm run dev
```

Leave this running. You should see: `Local: http://localhost:3000`.

### 3. Sample PDFs (already in the repo)

You have **two** sample PDFs to upload during the demo:

| File | Location | Content |
|------|----------|--------|
| **Data Protection Policy** | `backend/sample-policy.pdf` | Encryption, retention, third-party, access control |
| **HR & Training Policy** | `backend/sample-hr-policy.pdf` | Training deadline, background check, access review, certification |

To create the second PDF if it’s not there:

```bash
cd backend
python scripts/generate_sample_hr_policy.py
```

Keep both PDFs handy (e.g. on Desktop or in `backend/`) so you can drag-and-drop during the demo.

---

## Demo Script (What to Show Judges, ~5–8 min)

### Step 1: Login (real auth)

1. Open **http://localhost:3000** in the browser.
2. Click **Sign in** (or go to **/login**).
3. Log in with:
   - **Email:** `admin@company.com`
   - **Password:** `Admin@123`
4. Say: *“We use real authentication; you can’t sign in with empty credentials. This admin user is seeded on first run.”*

### Step 2: Dashboard (empty at first)

1. After login you land on the **Dashboard**.
2. Show: **Total Policies: 0**, **Active Violations: 0**, **Compliance Score: 100%**.
3. Say: *“Right now there’s no data. We’ll add policies and then show how violations and the dashboard update.”*

### Step 3: Ingest PDF policies (core requirement)

1. Go to **Upload policy** (or **Upload** in the nav).
2. **First PDF:** Drag and drop **`backend/sample-policy.pdf`** (or choose file).
3. Wait for: “Upload complete” and the list of **extracted rules** (e.g. encryption, retention, DPA, access control).
4. Say: *“The app extracts text from the PDF, sends it to OpenAI, and gets structured compliance rules. Only valid rules are stored.”*
5. **Second PDF:** Click “Upload another”, then upload **`backend/sample-hr-policy.pdf`**.
6. Show the second set of extracted rules (training, background check, etc.).
7. Optional: Open the **bell (Notifications)** and show the “Policy uploaded” notifications.

### Step 4: Policies and rules in the app

1. Go to **Policies** (or the policies section if in nav). Show **2 policies** with rule counts.
2. Go to **Rules**. Show the list of rules from both PDFs (severity, clause text).
3. Say: *“All of these rules came from the two PDFs we just uploaded. No manual rule entry.”*

### Step 5: Database connection and scan (optional but impressive)

If you have a **company-style database** (PostgreSQL/MySQL with tables that match the rule entities, e.g. `employees` with columns like `training_completed`, `date_of_joining`):

1. Go to **Settings** → **Database** tab. Enter Host, Username, Password, Database name and click **Connect database**. Wait for “Connected successfully.”
2. Go to **Dashboard**. In the **“Scan database”** card, click **Run scan now**. Wait for “Scan complete: X violation(s) found.”
3. Go to **Violations**. Show new violations (if any) with **explanation** and **evidence**.
4. Say: *“The engine compiles each rule to SQL and runs it against the connected DB. Violations are flagged with an AI-generated explanation and a snapshot of the row.”*

If you **don’t** have a real DB:

- Say: *“We’d connect a company DB here and run a scan. Violations would appear with explanations and evidence. For this demo we’re focusing on policy ingestion and rule extraction.”*
- You can still show the **Review** page and **Violations** list (may be empty).

### Step 6: Human review and audit trail

1. Go to **Review** (or **Violations** then filter by “pending”).
2. If there are violations: click one, show **evidence** and **AI explanation**, then **Approve** or **Dismiss** and add a note.
3. Say: *“Every status change is logged. There’s an audit trail per violation for regulators.”*
4. Optional: Show **GET /violations/:id/audit** in the API docs (http://localhost:8000/docs) to show the audit log for a violation.

### Step 7: Periodic monitoring

1. Say: *“A scheduler runs a full compliance scan on a schedule (e.g. every 24 hours). New violations are created and previously resolved ones can reappear if data violates again. So we get continuous monitoring, not just one-off checks.”*
2. Optional: Open **http://localhost:8000/docs**, show **GET /dashboard/summary** and mention that last scan time and status are stored and shown.

### Step 8: Dashboards and audit-ready reports

1. Go back to **Dashboard**. Show updated **Total Policies** and **Total Rules** (and **Active Violations** if you ran a scan).
2. Go to **Reports**. Show the reports view and **export CSV/PDF**.
3. Say: *“We can export compliance data and use the audit log for audit-ready reports.”*

### Step 9: Optional extras (if time)

- **Profile → Two-factor authentication:** Show “Enable 2FA” and briefly that it’s wired to the backend (secret, verify code).
- **Notifications:** Show that they come from the backend (e.g. “Policy uploaded”, “Welcome”).

---

## One-Liner for Judges

*“We built a software-only platform that ingests free-text PDF policies, extracts actionable compliance rules with AI, connects to a company database, scans it for violations, flags each with an explainable justification, supports human review and audit trail, and runs periodic scans—with dashboards and audit-ready exports.”*

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Frontend shows 0 / empty | Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local` and restart `npm run dev`. |
| Login fails | Backend must be running; use `admin@company.com` / `Admin@123`. |
| Upload fails (422) | Check `OPENAI_API_KEY` in `backend/.env`. |
| No violations | Connect a DB and run a scan, or skip and focus on policy upload + rules. |
| Second PDF missing | Run `python backend/scripts/generate_sample_hr_policy.py` from project root or from `backend/`. |

Good luck with the demo.
