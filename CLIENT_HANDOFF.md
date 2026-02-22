# AI Compliance Platform – Client Handoff

This document explains how the project works, what it does, how to connect and run it (database, backend, frontend), which APIs and services are used, and where to find things in the codebase.

---

## 1. Project Overview and How It Works

**What it is:** An AI-powered compliance monitoring system for SaaS companies. You upload policy PDFs, the system extracts rules (using an LLM), you connect a company database, and the platform runs compliance scans and surfaces violations. You can also ask natural-language questions about your policies (RAG). The platform uses **Llama 3.3 70B Versatile** via **Groq** for all LLM tasks (rule extraction, Ask policy answers, violation explanations). It does **not** use OpenAI when configured as recommended (Groq + local RAG embeddings).

**High-level flow:**

1. Users sign in (backend auth). Admins and Compliance Officers upload PDF policies; rules are extracted automatically (Llama 3.3 70B via Groq).
2. An external database (your company’s DB) is connected via the API. Scans run the extracted rules against that database.
3. Violations appear in the Review section. Users can approve/reject, add notes, and see AI-generated explanations and remediation (Llama 3.3 70B via Groq).
4. **Ask policy:** Users ask questions in plain language; answers are grounded in indexed policy text (RAG + Llama 3.3 70B via Groq). No prior knowledge or guessing—only what’s in the documents.

**Two main parts:**

- **Frontend:** Next.js app (default port 3000). UI for login, dashboard, upload, rules, Ask policy, violations, review, reports, profile, settings.
- **Backend:** FastAPI API (default port 8000). Handles auth, policy upload, rule extraction (Llama 3.3 70B via Groq), DB connection, scans, violations, RAG indexing and Ask.

The frontend is already built to call the backend. When `NEXT_PUBLIC_API_URL` is set (e.g. `http://localhost:8000`), the app uses the API. When it’s empty, the app uses mock data so you can run the UI without the backend.

---

## 2. APIs and External Services Used

| Service / technology | Purpose | Where it’s used |
|----------------------|--------|------------------|
| **Groq API** | LLM text generation | Rule extraction (Llama 3.3 70B), Ask policy answers, violation explanations and remediation. Base URL: `https://api.groq.com/openai/v1`. Model: `llama-3.3-70b-versatile` (configurable via `GROQ_MODEL`). |
| **Chroma** | Vector store for RAG | Policy text chunks are embedded and stored in Chroma; similarity search retrieves relevant excerpts for Ask policy and for violation explanation context. Persisted under `backend/data/chroma` (or `RAG_CHROMA_PATH`). |
| **PostgreSQL (app)** | Main application database | Stored in `DATABASE_URL`. Tables: users, policies, rules, violations, audit_log, notifications, scan_state, app_settings. Used by all backend routes. |
| **PostgreSQL (external)** | Company data for scans | Optional. Connected via POST `/database/connect` (host, username, password, db_name). Scan service runs rule SQL against this DB to find violating records. |
| **Sentence-transformers / ONNX** | RAG embeddings (default) | When `USE_LOCAL_EMBEDDINGS=true`: model `all-MiniLM-L6-v2` (or ONNX fallback). Used to embed policy chunks and user questions; no OpenAI. |
| **OpenAI embeddings (optional)** | RAG embeddings | Only when `USE_LOCAL_EMBEDDINGS=false` and `OPENAI_API_KEY` set. Model: `text-embedding-3-small`. Not required for recommended setup. |
| **PyMuPDF (fitz)** | PDF text extraction | Policy upload: extract raw text from uploaded PDFs before rule extraction and RAG indexing. |
| **ReportLab** | PDF report export | Reports → Export PDF: generates compliance report PDF on the backend. |
| **Redis (optional)** | Caching | When `REDIS_URL` is set: RAG response cache, chunk cache, embedding cache. Otherwise in-memory cache. |

**Frontend:** Next.js (React), Tailwind CSS, shadcn/ui. All backend calls use `fetch` to `NEXT_PUBLIC_API_URL` with `Authorization: Bearer <token>` when the user is logged in (token from `localStorage` after login).

---

## 3. Backend API Reference

Base URL: `http://localhost:8000` (no `/api/v1` prefix). Full interactive docs: http://localhost:8000/docs.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | No | Health check; returns status and checks (database, groq_api_key, openai_api_key, scheduler). |
| POST | `/auth/login` | No | Login with email/password; returns `user` + `token`. |
| GET | `/auth/me` | Bearer | Current user (id, email, name, role, department, two_fa_enabled). |
| POST | `/auth/logout` | Bearer | Logout; clears server-side token; audit log. |
| POST | `/auth/2fa/enable` | Bearer | Start 2FA; returns `secret`, `qr_uri`. |
| POST | `/auth/2fa/verify` | Bearer | Verify TOTP code; enable 2FA. |
| POST | `/auth/2fa/disable` | Bearer | Disable 2FA. |
| GET | `/dashboard/summary` | Bearer | Dashboard: policy/rule/violation counts, pending/high severity, last 5 violations, last scan info. |
| GET | `/policy` | Bearer | List policies (id, name, version, is_active, uploaded_at, rules_count). |
| POST | `/policy/upload` | Bearer | Upload policy PDF; extract text (PyMuPDF), extract rules (Groq/Llama), store policy + rules; RAG index in background. Returns list of created rules. |
| POST | `/policy/ask` | Bearer | RAG: question + optional policy_id; retrieve chunks (Chroma), generate answer (Groq/Llama). Rate limited per hour. |
| GET | `/policy/rag-status` | Bearer | RAG status: indexed_count, total_with_text, rag_available, hint. |
| POST | `/policy/reindex` | Bearer | Index all policies that have extracted_text into Chroma. |
| GET | `/policy/compare` | Bearer | Compare two policies: rule diff (only_in_old, only_in_new, in_both) + optional impact (new violations count). Query: old_policy_id, new_policy_id, compute_impact. |
| GET | `/rules` | Bearer | List rules; optional query: severity. |
| POST | `/rules` | Bearer | Create rule manually (policy_id, severity, policy_clause_text). |
| DELETE | `/rules/{rule_id}` | Bearer | Delete a rule. |
| POST | `/database/connect` | No | Connect external DB (body: host, username, password, db_name). Stores engine in memory for scans. |
| POST | `/scan/run` | Bearer | Run compliance scan: execute all rules against connected external DB, upsert violations, mark resolved; update ScanState; audit log. |
| GET | `/violations` | Bearer | List violations; optional query: severity, status. |
| PATCH | `/violations/{id}` | Bearer | Update violation status (approved / dismissed) and optional reviewer_notes; audit log. |
| GET | `/violations/{id}/audit` | Bearer | Audit trail for one violation. |
| GET | `/reports/export/csv` | Bearer | Download compliance report as CSV. |
| GET | `/reports/export/pdf` | Bearer | Download compliance report as PDF. |
| GET | `/notifications` | Bearer | List notifications (bell icon). |
| PATCH | `/notifications/{id}/read` | Bearer | Mark notification as read. |
| GET | `/settings` | Bearer | App settings (key-value). |
| PATCH | `/settings` | Bearer | Update settings (scan_frequency, severity_threshold, email_alerts, policy_upload_max_file_size_mb, etc.). |
| GET | `/users` | Bearer | List users (admin). |
| POST | `/users` | Bearer | Create user (admin). |
| PATCH | `/users/{id}/password` | Bearer | Set user password (admin). |
| DELETE | `/users/{id}` | Bearer | Delete user (admin). |
| GET | `/profile/metrics` | Bearer | Profile: logins, reports_viewed, exports for current month. |
| POST | `/profile/track` | Bearer | Track action (e.g. report_viewed) for metrics. |
| GET | `/profile/activity` | Bearer | Recent activity (audit log) for current user; query: limit, hours. |
| GET | `/metrics/rag` | Bearer | RAG metrics (aggregates, recent) if RAG_METRICS_ENABLED. |
| GET | `/audit` | Bearer | Audit log entries; query params for filtering. |

---

## 4. Features and How Each One Works

### Auth and roles

- **Login:** User enters email and password. Frontend calls `POST /auth/login`. Backend checks user exists, verifies password (bcrypt), creates a random token, stores token→user_id in memory, writes “login” to audit log, returns `user` (id, email, name, role, department, two_fa_enabled) and `token`. Frontend stores token in `localStorage` and uses it as `Authorization: Bearer <token>` on all subsequent requests.
- **Roles:** Admin, Compliance Officer, Viewer. Stored in `User.role`. Sidebar and page access are driven by role on the frontend; backend does not enforce role per route in the current setup (all authenticated users can call the same endpoints).
- **Current user:** `GET /auth/me` returns the user for the Bearer token; used for profile and 2FA status.
- **2FA:** Enable (`POST /auth/2fa/enable`) returns a secret and QR URI; user scans with authenticator app. Verify (`POST /auth/2fa/verify`) with code enables 2FA. Disable (`POST /auth/2fa/disable`) turns it off.

### Dashboard

- **Data:** Frontend calls `GET /dashboard/summary`. Backend reads from PostgreSQL: counts of policies, rules, violations; pending and high-severity counts; last 5 violations (with rule severity and explanation snippet); last scan timestamp, status, duration, total violations found (from `ScanState`).
- **UI:** Compliance score (derived from pending/total violations), KPIs, 30-day trend (frontend can use same summary or mock), risk heatmap (from summary data), recent violations list. No external API besides the backend.

### Policies (upload and list)

- **List:** `GET /policy` returns all policies with `rules_count`. Frontend maps to Policy type and shows in upload/policy list pages.
- **Upload:** User selects a PDF. Frontend sends `POST /policy/upload` with `FormData` (file). Backend: (1) Validates PDF, applies rate limit (uploads per hour) and file size limit (from settings or env). (2) Saves file to temp, extracts text with **PyMuPDF** (`extract_text_from_pdf`). (3) Creates or versions Policy (same name → new version, previous inactive), saves `extracted_text` on policy. (4) **Rule extraction:** calls **Groq** (Llama 3.3 70B) with policy text to get structured rules (entity, field, condition, operator, value, severity, policy_clause_text); validates and stores Rule rows. (5) Starts **RAG indexing in a background thread:** chunks text, embeds with sentence-transformers (or OpenAI if configured), adds to **Chroma**. (6) Writes audit log and notification, returns list of created rules. No OpenAI required when using Groq + local embeddings.

### Rules

- **List:** `GET /rules` (optional `?severity=`) returns rules with policy name and clause text. Frontend shows severity badges and expandable details.
- **Create:** `POST /rules` with policy_id, severity, policy_clause_text; backend creates Rule. Used for manual rule entry.
- **Delete:** `DELETE /rules/{id}` removes the rule. Used from Rules UI.

### Ask policy (RAG)

- **Flow:** User types a question and optionally selects a policy. Frontend calls `POST /policy/ask` with `{ query, policy_id }`. Backend: (1) Rate limit check (per user, per hour). (2) Optional response cache (same query + policy_id). (3) **Retrieval:** sanitize query, embed with same model as index (sentence-transformers or OpenAI), **Chroma** similarity search (top-k, min similarity, optional policy_id filter), trim chunks to token budget (score-order). (4) **Answer:** Build prompt with policy excerpts + question; system prompt says “answer only from excerpts.” Call **Groq** (Llama 3.3 70B) for completion; return answer. If index empty, fallback: use raw policy text (truncated) and same LLM to generate answer, with a note that RAG index is still building.
- **Index status:** `GET /policy/rag-status` returns indexed_count, total_with_text, rag_available, hint (e.g. “Index existing policies” or dependency message).
- **Reindex:** `POST /policy/reindex` loads all policies with `extracted_text`, chunks and indexes each into Chroma. Used by “Index existing policies” button.

### Database connection

- **Connect:** User enters host, username, password, db name. Frontend calls `POST /database/connect` with that body. Backend uses **SQLAlchemy** to create a PostgreSQL engine and stores it in memory (`create_external_engine_from_credentials`). Used for running scans; no data is imported into the app DB.

### Scans

- **Run:** User clicks “Run scan.” Frontend calls `POST /scan/run`. Backend: loads all Rule rows; for each rule, **rule_engine** builds SQL from `rule_data` (entity, field, condition, operator, value) and executes it against the **external DB** engine. Rows returned are “violating” records. For each violation: (1) **Explanation:** optional RAG retrieval for policy context, then **Groq** (Llama 3.3 70B) to generate short explanation. (2) **Remediation:** same LLM to suggest remediation. (3) Upsert Violation (record_id, rule_id, status pending, explanation, suggested_remediation, evidence_snapshot). Violations no longer in current results are marked resolved. (4) Update single **ScanState** row (last_scan_timestamp, status, total_violations_found, scan_duration_seconds). (5) Audit log “scan_run” with summary. Returns rules_checked, total_violations, resolved_count, by_rule. If no external DB is connected, returns 200 with a message telling the user to connect a database.

### Violations

- **List:** `GET /violations` (optional `?severity=&status=`) returns violations with rule and policy info, evidence, explanation, suggested_remediation, reviewer_notes. Frontend maps to Violation type and shows table with filters and evidence panel.
- **Update status (Review):** User approves or dismisses; optional reviewer notes. Frontend calls `PATCH /violations/{id}` with status (approved/dismissed) and reviewer_notes. Backend updates Violation and writes “status_changed” to audit log.
- **Audit:** `GET /violations/{id}/audit` returns audit entries for that violation (history of status changes, etc.).

### Policy Impact

- **Compare:** User selects two policies (old and new). Frontend calls `GET /policy/compare?old_policy_id=&new_policy_id=&compute_impact=true`. Backend uses `compare_policies`: diff of rules (only in old, only in new, in both); if compute_impact and external DB connected, estimates how many new violations would appear. No external API; reads from app DB and optionally runs a lightweight check against external DB.

### Reports

- **Export CSV:** `GET /reports/export/csv` streams a CSV (summary + violations table). Backend reads Policy/Rule/Violation/ScanState, writes audit “export,” returns StreamingResponse.
- **Export PDF:** `GET /reports/export/pdf` builds a PDF with ReportLab (title, summary, violation list), logs export, returns file. No LLM; backend only.

### Profile

- **Metrics:** `GET /profile/metrics` returns logins, reports_viewed, exports for current month (from audit log).
- **Activity:** `GET /profile/activity?limit=&hours=` returns recent audit entries for the current user (e.g. “Policy uploaded”, “Violation status updated”, “Signed in”). Frontend shows last 4 and “See all.”
- **Track:** `POST /profile/track` with action_type (e.g. report_viewed) records an audit entry for metrics.

### Settings (Admin)

- **Get:** `GET /settings` returns key-value app settings (e.g. scan_frequency, severity_threshold, policy_upload_max_file_size_mb).
- **Update:** `PATCH /settings` with partial keys updates AppSettings. Used for upload limits and app configuration.

### Notifications

- **List:** `GET /notifications` returns notifications (type, title, body, read, created_at). Shown in bell dropdown.
- **Mark read:** `PATCH /notifications/{id}/read` marks one as read. Created by backend on events (e.g. policy uploaded).

### Audit

- **List:** `GET /audit` returns audit log entries (action_type, entity_type, entity_id, performed_by, timestamp, meta). Used for compliance and debugging.

---

## 5. How the RAG Model Works

Ask policy answers are grounded **only** in your policy text: the system retrieves relevant excerpts from an index, then the LLM (**Llama 3.3 70B Versatile** via Groq) generates an answer from those excerpts. No general knowledge—only what’s in the documents.

**APIs and components:**

- **Embeddings (indexing and query):** By default **sentence-transformers** model `all-MiniLM-L6-v2` (or Chroma’s ONNX fallback). Optionally **OpenAI** `text-embedding-3-small` when `USE_LOCAL_EMBEDDINGS=false` and `OPENAI_API_KEY` is set.
- **Vector store:** **Chroma** (persistent client, collection `policy_chunks`). Path: `backend/data/chroma` or `RAG_CHROMA_PATH`.
- **LLM for answer:** **Groq API** with model **Llama 3.3 70B Versatile** (`llama-3.3-70b-versatile`). Same model is used for rule extraction and violation explanations.

**Indexing** (when policies are uploaded or “Index existing policies” is run):

- Policy text is cleaned (page numbers, repeated headers/footers, optional boilerplate shortening).
- Text is split into chunks by token count (configurable via `RAG_CHUNK_TOKENS`, `RAG_CHUNK_OVERLAP_TOKENS` in backend config).
- Each chunk is embedded with the embedding model above and stored in Chroma with metadata (policy_id, chunk_index, policy_name).
- Optional: for very long policies, summary chunks can be added when `RAG_USE_SUMMARIES` is enabled.

**Retrieval** (when the user asks a question):

- The user’s question is sanitized and rate-limited (per user per hour).
- The same embedding model encodes the question; optional embedding cache (in-memory or Redis).
- **Chroma** similarity search returns top-k chunks (optionally filtered by policy_id). Results are filtered by minimum similarity score; optional re-ranking can be enabled.
- Retrieved chunks are trimmed to a token budget so the prompt fits the context window, with higher-scoring chunks kept first.

**Answer generation:**

- The system builds a prompt: policy excerpts (the trimmed chunks) + the user’s question. A system prompt instructs the model to answer **only** from those excerpts.
- This prompt is sent to **Groq** (Llama 3.3 70B). The model’s reply is returned as the “Ask policy” answer.
- Optional: response and chunk caching (in-memory or Redis) for repeated questions.

**Key env vars:** `USE_LOCAL_EMBEDDINGS` (default true = no OpenAI), `RAG_CHROMA_PATH`, `RAG_TOP_K`, `RAG_MIN_SIMILARITY`, `RAG_ASK_MAX_CONTEXT_TOKENS`, `RAG_ASK_MAX_TOKENS`, `GROQ_MODEL` (default `llama-3.3-70b-versatile`). See `backend/.env.example` for the full list.

---

## 6. How to Connect and Run (Step-by-Step)

**Prerequisites:** Node.js 18+, Python 3.11+, PostgreSQL, and a **Groq API key** (required for the LLM: Llama 3.3 70B—used for Ask policy answers, rule extraction, and explanations). Get a key at https://console.groq.com. No OpenAI key is needed when using `USE_LOCAL_EMBEDDINGS=true` (recommended).

| Step | What | Where | Command / Action |
|------|------|--------|------------------|
| 1 | Create PostgreSQL DB | Your PostgreSQL host | `CREATE DATABASE compliance_db;` (or another name; use it in `DATABASE_URL`). |
| 2 | Backend virtual environment | `backend/` | `python -m venv venv` then activate (e.g. Windows: `.\venv\Scripts\Activate.ps1`; macOS/Linux: `source venv/bin/activate`). |
| 3 | Backend dependencies | `backend/` | `pip install -r requirements.txt` |
| 4 | Backend environment | `backend/` | Copy `backend/.env.example` to `backend/.env`. Set `DATABASE_URL` (PostgreSQL URL), `GROQ_API_KEY` (required for Llama 3.3 70B). Set `USE_LOCAL_EMBEDDINGS=true` for local RAG embeddings (recommended; no OpenAI key needed). |
| 5 | Run backend | `backend/` | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| 6 | Frontend environment | Project root | Create or edit `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| 7 | Frontend dependencies | Project root | `npm install` (if not already done) |
| 8 | Run frontend | Project root | `npm run dev` → open http://localhost:3000 |
| 9 | Connect external DB (optional) | Browser or Swagger | POST http://localhost:8000/database/connect with `host`, `username`, `password`, `db_name` to run scans against your data. |

**Notes:**

- **Default admin login:** Email `admin@company.com`, Password `Admin@123` (created on first backend run). Use these when the frontend is pointed at the backend.
- **API docs (Swagger):** http://localhost:8000/docs  
- **Health check:** http://localhost:8000/health  

The frontend is already wired to the backend via `NEXT_PUBLIC_API_URL`. All API calls go through `src/api/index.ts` and `src/lib/api-client.ts` (which sends `Authorization: Bearer <token>` from `localStorage` when set); no code change is needed to “connect” once the URL is set and both servers are running.

---

## 7. File Structure

**Frontend (project root):**

- `src/app/` – Next.js App Router: `(app)/` (protected routes), `login/`, landing `page.tsx`, `layout.tsx`, `globals.css`
- `src/app/(app)/` – Dashboard, upload, rules, ask-policy, policy-impact, violations, review, reports, profile, settings
- `src/components/` – layout (sidebar, header, notifications), dashboard, ui (shadcn)
- `src/contexts/` – auth, theme, toast
- `src/api/` – API client and endpoints (uses `NEXT_PUBLIC_API_URL`; all backend calls and response mapping)
- `src/lib/` – env (`config.apiUrl`), api-client (fetch with Bearer token), utils
- `src/types/` – shared TypeScript types

**Backend (`backend/`):**

- `app/main.py` – FastAPI app, CORS, router includes, exception handlers, health with checks
- `app/config.py` – Settings (env), RAG and API config
- `app/routes/` – auth, policy, dashboard, database, scan, violations, rules, reports, profile, metrics, settings, users, notifications, audit
- `app/services/` – RAG (rag_service, rag_cache, rag_metrics), LLM (llm_client), PDF (extract_text_from_pdf), rule_extractor (Groq), explanation_service (Groq), rule_engine, scan_service, external_db, policy_compare
- `app/models/` – SQLAlchemy models (Policy, Rule, User, Violation, AuditLog, Notification, ScanState, AppSettings)
- `app/database.py` – DB engine, session
- `backend/.env` – Not committed; copy from `.env.example`

---

## 8. Environment Variables and APIs (Reference)

**Backend (`backend/.env`):**

- **Required:** `DATABASE_URL` (PostgreSQL connection string), `GROQ_API_KEY` (for the LLM: Llama 3.3 70B Versatile—Ask policy, rule extraction, explanations).
- **Optional:** `USE_LOCAL_EMBEDDINGS=true` (default; RAG uses local embeddings, no OpenAI). `OPENAI_API_KEY` is only used for RAG embeddings when `USE_LOCAL_EMBEDDINGS=false`; the default setup does not require OpenAI. Other: `RAG_*` (see `backend/.env.example`), `REDIS_URL` (for cache), `GROQ_MODEL` (default `llama-3.3-70b-versatile`).

**Frontend (`.env.local` in project root):**

- `NEXT_PUBLIC_API_URL=http://localhost:8000` – Backend base URL; leave empty for mock-only mode.

**APIs:** Base URL is `http://localhost:8000`. There is no `/api/v1` prefix. Full API reference: Swagger at http://localhost:8000/docs.

---

## 9. Troubleshooting and Production-Style Run

**Troubleshooting:**

- Backend won’t start → Check `DATABASE_URL` and that the database exists. Ensure PostgreSQL is running.
- “No module named chromadb” (or similar) → From `backend/` with the same Python/venv active, run `pip install -r requirements.txt` again. Run the backend with that same environment.
- Frontend shows mock data → Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local` and restart the dev server (`npm run dev`).
- **LLM / RAG:** The main LLM is **Llama 3.3 70B via Groq**; set `GROQ_API_KEY` in `backend/.env`. OpenAI is optional and only used for RAG embeddings when `USE_LOCAL_EMBEDDINGS=false`. With the default `USE_LOCAL_EMBEDDINGS=true`, RAG runs entirely with local embeddings (no OpenAI key required).
- Ask policy returns “No indexed content” → Upload policies first, then use “Index existing policies” on the Ask policy page, or re-upload the PDF so the background index runs.
- Scan says “No external database connected” → Call POST `/database/connect` with your company DB credentials (e.g. from Settings → Database or Swagger).

**Production-style run:**

- Backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000` (omit `--reload`).
- Frontend: `npm run build` then `npm start`.

---

This handoff document is accurate to the current repo. For more detail, see the main [README.md](README.md) and [backend/README.md](backend/README.md).
