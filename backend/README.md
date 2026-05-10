# AI Compliance Platform – Backend

FastAPI backend for the AI compliance monitoring platform.

## Prerequisites

- Python 3.11+
- MongoDB (for `DATABASE_URL`)
  - **Windows 10 Install:** Download and install [MongoDB Community Server](https://www.mongodb.com/try/download/community). During install, ensure "Install MongoDB as a Service" is checked.
  - Alternatively, use a free cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
  - Default connection: `mongodb://localhost:27017/compliance_db`

## Setup

1. **Create and activate a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   # Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # Windows (cmd):
   .\venv\Scripts\activate.bat
   # macOS/Linux:
   source venv/bin/activate
   ```

2. **Install dependencies** (includes `chromadb` and `tiktoken` for RAG / Ask policy):
   ```bash
   pip install -r requirements.txt
   ```
   If you use a **venv** and see "No module named 'chromadb'" when running the app: **stop the backend** (no process using the venv), then run `pip install -r requirements.txt` again inside the venv. Or run the backend with the same Python that has chromadb installed (e.g. your system/Anaconda Python).

3. **Configure environment**:
   - Copy `.env.example` to `.env`
   - Set `DATABASE_URL` (MongoDB) and `OPENAI_API_KEY` (if using OpenAI for embeddings) in `.env`
   ```bash
   copy .env.example .env   # Windows
   # cp .env.example .env   # macOS/Linux
   ```
   Then edit `.env` and replace `your_openai_key_here` with your real OpenAI API key.

## Run the server

From the **backend** directory:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or without reload (production-style):

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Run the backend with RAG (Ask policy + Llama 3.3 70B)

1. **Prerequisites**
   - MongoDB running (locally or Atlas).
   - `.env` in the **backend** folder with:
     - `DATABASE_URL` (MongoDB connection string, e.g. `mongodb://localhost:27017/compliance_db`)
     - `OPENAI_API_KEY` (if not using local embeddings)
     - `GROQ_API_KEY` (for answers: Llama 3.3 70B)
     - Optional: `GROQ_MODEL=llama-3.3-70b-versatile`

2. **Install dependencies** (from the **backend** folder):
   ```bash
   pip install -r requirements.txt
   ```
   This installs `chromadb`, `tiktoken`, and the rest. If you use a venv and get "No module named 'chromadb'", run the backend with the same Python that has these packages (e.g. don’t activate venv, or install deps in the venv with the backend stopped).

3. **Start the backend** (from the **backend** folder):
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Leave this terminal open. You should see "Application startup complete" and "Uvicorn running on http://0.0.0.0:8000".

4. **Use RAG in the app**
   - Open the frontend (e.g. `npm run dev` in the project root) and sign in.
   - **Upload policy PDFs** (Upload Policy) so they get text extracted and indexed, **or**
   - Go to **Ask policy** and click **"Index existing policies"** if you already have policies with extracted text.
   - Then ask a question (e.g. "What is the data retention period?") with scope **All policies**. Answers use **Llama 3.3 70B** (Groq); search uses RAG (OpenAI embeddings).

- **`--reload`** – auto-reload on code changes (omit in production)
- **`--host 0.0.0.0`** – listen on all interfaces (optional; default is `127.0.0.1`)
- **`--port 8000`** – port (default is 8000)

Then open:

- **API docs (Swagger):** http://localhost:8000/docs  
- **Health check:** http://localhost:8000/health  

## Default login

A default admin user is created on first run:

- **Email:** `admin@company.com`
- **Password:** `Admin@123`

Use these credentials to sign in when the frontend is pointed at this backend (`NEXT_PUBLIC_API_URL=http://localhost:8000`).

## Sample policy PDFs (for demo and testing)

Two sample PDFs are available for upload and rule extraction:

| File | Generate with |
|------|----------------|
| `backend/sample-policy.pdf` | `python scripts/generate_sample_policy.py` |
| `backend/sample-hr-policy.pdf` | `python scripts/generate_sample_hr_policy.py` |

From the backend directory run the script; both require `reportlab`. Use them on the Upload policy page to see extracted rules and dashboard updates.

For judges: `Violations_Explainer.pdf` (generate with `python scripts/generate_violations_explainer_pdf.py`) explains what violations are and what the Violations section shows.

## Manual test checklist (backend + RAG + index + Ask)

Use this to confirm the backend, RAG, index loading, and Ask policy work end-to-end.

1. **Backend running**
   - Start: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` (from `backend/`).
   - Open http://localhost:8000/health — expect `{"status":"ok"}` or `"degraded"` and `checks` with `database`, `groq_api_key`, `scheduler`.

2. **Upload**
   - In the app, go to **Upload Policy**, upload a small PDF (e.g. `sample-policy.pdf`).
   - Expect "Upload complete" and **Extracted Rules** to load (usually within 1–2 min). RAG indexing runs in the background.

3. **Index loading**
   - Go to **Ask policy**. If "Indexed 0 of N" appears, click **Index existing policies** (or wait for auto-index).
   - Expect "Indexed N of N policies" when indexing finishes. First run may take 1–2 min (model download).

4. **Ask question**
   - Type a question (e.g. "What is the data retention period?") and click **Ask**.
   - Expect an answer from policy text (RAG or fallback). If you see "API connected" and "Indexed N of N", Ask uses RAG; otherwise it uses policy text fallback.

5. **Automated tests**
   - From `backend/`: `python -m pytest tests/test_health.py tests/test_rag.py tests/test_new_endpoints.py -v --tb=short`
   - Health and RAG tests verify `/health` and RAG service (get_rag_status, get_indexed_count, retrieve). First run can be slow (Chroma/embedding load).

## Run tests

From the **backend** directory:

```bash
python -m pytest tests/ -v --tb=short
```

Health, RAG, and endpoint tests are in `tests/test_health.py`, `tests/test_rag.py`, and `tests/test_new_endpoints.py`. Tests use a test MongoDB database and `USE_LOCAL_EMBEDDINGS=true`; no real OpenAI needed. First run may take 1–2 min if RAG/Chroma load.

With warnings treated as errors:

```bash
pytest tests/ -v -W error
```

## RAG (Ask policy)

- **Ask policy** uses RAG (chromadb + OpenAI embeddings for indexing/search). Set `OPENAI_API_KEY` in `.env` for RAG indexing. Ensure `chromadb` and `tiktoken` are installed (`pip install -r requirements.txt`).
- **LLM completion** (answers, rule extraction, violation explanations): when `GROQ_API_KEY` is set, the app uses **Groq** with **Llama 3.3 70B** (`llama-3.3-70b-versatile`). Otherwise it uses OpenAI (`gpt-4o-mini`). Set `GROQ_API_KEY` and optionally `GROQ_MODEL` in `.env` (get a key from https://console.groq.com).
- Use **Index existing policies** on the Ask policy page to index policies that already have extracted text.
- If indexing reports "Indexed 0 of N" with a hint, follow the hint (e.g. set OPENAI_API_KEY for embeddings, install deps, restart backend).

## Final version (tested)

- **Tests:** Passing (pytest).
- **Endpoints:** Health, auth (login, me, 2FA), profile/activity, users, policy (list, upload, ask, reindex), rules, violations, dashboard, scan, settings, reports, audit, notifications.
- **Dependencies:** See `requirements.txt` (includes FastAPI, MongoEngine, pymongo, chromadb, tiktoken, PyMuPDF, openai, etc.).
- **Run:** `uvicorn app.main:app --host 0.0.0.0 --port 8000` (ensure MongoDB is running and `.env` is configured).
