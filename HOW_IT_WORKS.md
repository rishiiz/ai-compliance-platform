# How your AI Compliance Platform works

This document explains: **how the website works end-to-end**, **the sample PDF and what gets “detected”**, **where history is saved and shown**, **how rules are set**, and **what happens with malicious or malformed PDFs**.

---

## 1. How the website works (big picture)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   You       │     │  Frontend   │     │   Backend   │     │  Database   │
│   (Browser) │────▶│  (Next.js)  │────▶│  (FastAPI)  │────▶│ (PostgreSQL)│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │                    │
       │  Login             │  POST /auth/login  │  Check password    │
       │  Upload PDF        │  POST /policy/     │  Extract text      │
       │  View dashboard    │  upload            │  (PyMuPDF)         │
       │  Review violations │  GET /dashboard/   │  Extract rules     │
       │  etc.              │  summary, /rules,  │  (OpenAI)          │
       │                    │  /violations, etc.  │  Validate & store   │
       │                    │                    │  Write audit log   │
```

- **You** use the app in the browser (login, upload policy PDF, see dashboard, review violations, etc.).
- **Frontend** talks to the backend only when `NEXT_PUBLIC_API_URL` is set (e.g. `http://localhost:8000`).
- **Backend** does the real work: auth, PDF handling, rule extraction, scans, and writes everything to the **database**.
- **Database** stores: users, policies, rules, violations, audit log (history), notifications, settings.

So: the “brain” is the backend + database; the frontend is the UI that calls the API and shows the data.

---

## 2. Sample PDF and what “detection” means

You have a **sample PDF** at `backend/sample-policy.pdf`. It’s a normal policy document (data protection, encryption, retention, etc.).

In this app, **“detection” is not virus/malware detection**. It’s **compliance rule detection**:

1. **Upload**  
   You upload the PDF (e.g. from the Upload policy page).

2. **Text extraction**  
   The backend uses **PyMuPDF** to read **text only** from the PDF. No scripts run; no links are followed. Just text.

3. **Rule extraction**  
   That text is sent to **OpenAI** (e.g. GPT-4o-mini) with a fixed prompt. The model returns a **JSON list of compliance rules** (e.g. “encrypt data”, “retention 7 years”, “DPA for third parties”).

4. **Validation and storage**  
   Each rule is checked against a **strict schema** (entity, field, condition, operator, value, severity, optional policy_clause_text). Only valid rules are saved.

5. **What you see**  
   - **Upload page**: list of extracted rules right after upload.  
   - **Policies**: new policy with rule count.  
   - **Rules**: all rules from all policies.  
   - **Dashboard**: total policies, total rules, compliance score, recent violations (if any).  
   - **Notifications**: e.g. “Policy uploaded” with rule count.

So the sample PDF is there to **prove this flow**: upload → text → rules → stored → visible in the app. There is no “threat” in that PDF; the “detection” is **policy rules**, not malware.

---

## 3. History (audit) – where it’s saved and where it’s shown

**Where it’s saved**

- Every important action is written to the **audit log** in the database (table `audit_logs`).
- Each row has: `action_type`, `entity_type`, `entity_id`, `performed_by`, `timestamp`, `meta` (extra JSON).

**What gets logged (examples)**

- **Policy upload**: `action_type = "policy_uploaded"`, `entity_type = "policy"`, `meta` has policy name, filename, rules count.
- **Violation status change**: when you approve/dismiss a violation, `action_type` and `entity_type = "violation"`, etc.
- **Scan run**: when a compliance scan runs, scan result is logged.

**Where you can see it (APIs)**

- **GET /audit** – full audit log (optional filters: `entity_type`, `entity_id`).
- **GET /profile/activity** – same data, “recent activity” style (used for profile).
- **GET /violations/{id}/audit** – audit trail for a single violation (who changed status, when).

**In the UI today**

- **Review** page: each violation can show an audit trail; the backend supports it via `GET /violations/:id/audit`.
- **Profile** “Recent activity”: the backend has **GET /profile/activity**, but the profile page still uses **mock** list. To show real history, the frontend should call `GET /profile/activity` and render that list instead of the mock one.

So: **history is saved** in the DB and available via API; the only gap is wiring the Profile “Recent activity” section to `GET /profile/activity`.

---

## 4. How rules are set (no manual “rule builder” in app)

Rules are **not** set by hand in the UI. They are **derived from the policy PDF**:

1. **Source**: The text of the uploaded PDF.
2. **AI step**: OpenAI is asked to extract compliance rules and return a JSON array with fixed fields (entity, field, condition, operator, value, severity, policy_clause_text).
3. **Validation**: Each object is validated with **Pydantic** (`RuleDataSchema`):
   - `entity`, `field`, `operator`, `value`, `severity` required.
   - `condition` must be a **structured** object with `type` one of: `equality`, `boolean`, `deadline`, `comparison`.
   - `policy_clause_text` optional.
4. **Storage**: Only rules that pass validation are stored as rows in the `rules` table linked to the policy.

So “setting rules” in this app means: **upload a policy PDF → AI extracts rules → backend validates and stores them**. You can’t currently add or edit rules from the UI; that would require new endpoints and screens.

---

## 5. Malicious or malformed PDFs – what happens

The app does **not** execute PDF content. It only:

- Accepts the file as PDF.
- Reads bytes to a **temporary file**.
- Calls **PyMuPDF** to **extract text**.
- Sends that **text** to OpenAI.
- Validates and stores **structured rule objects**.

So the “attack surface” is: **wrong file type**, **broken PDF**, **huge file**, or **weird content that confuses the model or validation**.

**What is checked today**

| Check | Where | Result if it fails |
|-------|--------|---------------------|
| File extension | Backend `POST /policy/upload` | Rejects with 400: "File must be a PDF" |
| Valid PDF structure | PyMuPDF `fitz.open()` | Raises; backend returns 422 with message like "Invalid or corrupted PDF" |
| Text extraction | PyMuPDF `page.get_text()` | Raises; same 422 |
| Rule format (JSON) | Rule extractor | 422 "Invalid JSON from model" or similar |
| Rule schema | `validate_rule_data()` (Pydantic) | 422 "Rule at index X failed validation: ..." |

**What is *not* done (you could add later)**

- **File size limit**: The whole file is read into memory. A very large PDF could cause high memory use or timeouts. Adding a max size (e.g. 10 MB) in the upload route would help.
- **Virus/malware scan**: No antivirus scan. The app never executes the PDF; risk is mostly DoS (huge file) or abuse of OpenAI if someone uploads a huge or junk PDF.
- **Content sanitization**: The extracted **text** is sent to OpenAI as-is. If the PDF contained prompt-injection style text, the model could in theory follow it; the strict JSON + schema validation still limits what gets stored.

**Summary**

- **Malformed/corrupted PDF**: Rejected by PyMuPDF → 422, no policy or rules stored.
- **Non-PDF file**: Rejected by extension check → 400.
- **Malicious PDF (e.g. with scripts)**: Scripts are **not** run; only text is extracted. So classic PDF exploits don’t run here.
- **Weird or adversarial text**: May produce bad or no rules; invalid rules are rejected by schema and not stored.

---

## 6. Quick reference

| Question | Answer |
|----------|--------|
| How does the site work? | Browser → Next.js → FastAPI → PostgreSQL. Backend does auth, PDF → text → rules, scans, audit. |
| What does the sample PDF do? | Proves upload → extract text → extract rules → save → show in Policies/Rules/Dashboard. No malware detection. |
| Where is history saved? | In `audit_logs`; exposed by GET /audit and GET /profile/activity. |
| How are rules set? | Only from policy PDF: AI extracts rules, backend validates and stores. No UI to add rules by hand. |
| Malicious PDF? | Only .pdf accepted; only text extracted (no execution); invalid/corrupt PDF → 422; invalid rule JSON/schema → 422. |
| Show real history in UI? | Wire Profile “Recent activity” to GET /profile/activity and use that instead of the mock list. |

**Remediation:** Each violation can have AI-generated **suggested remediation** steps; shown on Violations and Review pages. **Policy impact:** Use **Policy Impact** (or GET /policy/compare) to compare two policy versions and see rule diff plus estimated new violations if you adopt the new policy (when DB connected).

If you want, next steps could be: (1) add a **file size limit** for uploads, and (2) **wire Profile “Recent activity”** to the real audit API so history shows there.
