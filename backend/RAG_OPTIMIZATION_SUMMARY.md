# RAG Optimization – How It Works (Simple Summary)

## What Was Added

The "Ask policy" feature (where you ask questions about your compliance documents) was upgraded so it is **faster**, **uses fewer tokens**, and **stays within safe limits**.

---

## 1. Cleaning Text Before Storing (Semantic Compression)

**What it does:** Before we save policy text into the search index, we clean it.

- Remove repeated headers/footers (e.g. same line on every page).
- Remove page numbers (e.g. "Page 5", "5 / 12").
- Collapse extra spaces and trim.
- Optionally shorten long legal phrases.

**Why it helps:** Less junk text means better search and smaller, clearer chunks. Fewer tokens = cheaper and faster.

**Config:** `RAG_SEMANTIC_COMPRESSION=true` (default on). Optional: `RAG_NORMALIZE_RULES_TO_KV=false` (off by default).

---

## 2. Token Budget (Never Overflow the Model)

**What it does:** Before sending anything to the AI, we count how many tokens (roughly “words”) we’re using: system prompt + your question + policy excerpts. If that total would exceed the limit (e.g. 4096 tokens), we **drop the least important excerpts from the end** until we’re under the limit.

**Why it helps:** The model never gets more text than it can handle, so you avoid errors and timeouts.

**Config:** `RAG_ASK_MAX_CONTEXT_TOKENS=4096`, `RAG_ASK_MAX_TOKENS=500` (max answer length).

---

## 3. Smarter Search (Retrieval Optimization)

**What it does:**

- **Scores:** We now get a “relevance score” for each chunk. Low-score chunks are thrown away (below a threshold).
- **Dynamic top-k:** If the best chunk is very relevant, we use fewer chunks (e.g. 3). If not, we use more (e.g. 5). So we send “just enough” context.
- **Optional re-ranker:** You can turn on a second pass that re-ranks the top chunks with a small model and keeps only the best 3–5. Off by default.

**Why it helps:** You send only the most relevant bits to the AI, so answers are better and use fewer tokens.

**Config:** `RAG_MIN_SIMILARITY=0.5`, `RAG_TOP_K_MAX=10`, `RAG_TOP_K_MIN=3`, `RAG_HIGH_SIMILARITY_THRESHOLD=0.85`, `RAG_USE_RERANKER=false`, `RAG_RERANK_TOP_N=5`.

---

## 4. Caching (Same Question = Instant Answer)

**What it does:** We cache at three levels:

- **Full answer:** If you ask the exact same question again (same text + same policy filter), we return the previous answer without calling the AI or the vector DB.
- **Retrieved chunks:** If the same question is asked again, we can reuse the list of chunks we found (and only call the AI, not the vector DB).
- **Query embedding:** The “vector” for your question is cached so we don’t recompute it for the same question.

**Backend:** If you set `REDIS_URL`, we use Redis. Otherwise we use an in-memory cache with a time limit (e.g. 1 hour).

**Why it helps:** Repeated questions are much faster and put less load on the AI and the database.

**Config:** `RAG_CACHE_TTL_SECONDS=3600`, `RAG_CACHE_RESPONSE=true`, `RAG_CACHE_CHUNKS=true`, `RAG_CACHE_EMBEDDINGS=true`, `REDIS_URL=""` (optional).

---

## 5. Non-Blocking Ask (Async Pipeline)

**What it does:** The “Ask policy” API is now **async**. Heavy work (search + AI call) runs in a background thread so the server can handle other requests while waiting.

**Why it helps:** The server doesn’t get stuck on one long question; other users’ requests are not delayed.

---

## 6. Safe AI Settings

**What it does:** We use config for how the AI answers:

- **Max answer length:** e.g. 500 tokens so answers don’t run away.
- **Temperature:** e.g. 0.2 so answers stay factual and stable (good for compliance).

**Config:** `RAG_ASK_MAX_TOKENS=500`, `RAG_ASK_TEMPERATURE=0.2`.

---

## 7. Optional Streaming

**What it does:** You can ask for a **streaming** answer: `POST /policy/ask?stream=true`. The server sends the answer in small pieces (SSE) as the AI generates them, instead of waiting for the full answer.

**Why it helps:** The user sees text appearing as it’s generated, which feels faster.

---

## 8. Metrics (How Long Things Take)

**What it does:** For each “Ask” we record:

- Time to search (retrieval).
- Time for the AI to answer (LLM).
- Total time.
- How many tokens we sent (and optionally how many we got back).

We keep the last N requests in memory. An endpoint returns simple stats (e.g. average latency, p95).

**Endpoint:** `GET /metrics/rag` (with auth). Use `?recent=true` to get raw recent entries; otherwise you get aggregates.

**Config:** `RAG_METRICS_ENABLED=true`, `RAG_METRICS_BUFFER_SIZE=100`.

---

## 9. Optional Summaries for Long Documents

**What it does:** For **very long** policies (e.g. above 15,000 characters), we can:

- Split the text into sections.
- Generate a short summary per section (with the AI).
- Store these summaries in the same vector DB with a “summary” flag.

When you ask a **short, broad** question (e.g. ≤6 words), we can search **only in these summaries** instead of in the full chunks. That uses far fewer tokens.

**Config:** `RAG_USE_SUMMARIES=false` (off by default), `RAG_SUMMARY_MIN_CHARS=15000`.

---

## What’s Working End-to-End

| Feature | Status | Where it runs |
|--------|--------|----------------|
| Text cleaning before indexing | On (default) | When you upload/reindex a policy |
| Token budget before LLM | On | Every Ask request |
| Scored retrieval + threshold + dynamic k | On | Every Ask request |
| Optional re-ranker | Off by default | `retrieve()` when `RAG_USE_RERANKER=true` |
| Response cache | On | Ask: same question → cached answer |
| Chunks cache | On | Ask: same question → reuse chunks |
| Embedding cache | On | Same question text → reuse embedding |
| Async Ask | On | `POST /policy/ask` |
| LLM max_tokens / temperature from config | On | Ask + fallback |
| Streaming Ask | Optional | `POST /policy/ask?stream=true` |
| RAG metrics | On | Recorded per Ask; `GET /metrics/rag` |
| Section summaries for long docs | Off by default | Indexing when `RAG_USE_SUMMARIES=true` and doc is long; retrieval when query is “broad” |

---

## How to Test It Yourself

1. **Start backend:**  
   `cd backend && uvicorn app.main:app --reload --port 8000`

2. **Health:**  
   `GET http://localhost:8000/health`  
   Should return 200 and include `groq_api_key` (and optionally RAG) in checks.

3. **Ask policy (normal):**  
   Log in, then `POST /api/v1/policy/ask` with `{"query": "What is the data retention period?", "policy_id": null}`.  
   You should get an answer; second time with same body should be faster (response cache).

4. **Ask with streaming:**  
   Same URL with `?stream=true`. You should get SSE events (e.g. `data: {"content": "..."}`).

5. **Metrics:**  
   `GET /api/v1/metrics/rag` (with auth). You should get `count`, `avg_total_latency_ms`, etc. Use `?recent=true` for last N raw entries.

6. **Unit-style tests (no Chroma):**  
   `cd backend && python -m pytest tests/test_rag_optimization.py -v`  
   These test: sanitize_query, count_tokens, prepare_text_for_rag, trim_chunks_to_token_budget, cache key, metrics aggregates.

7. **Full RAG tests (need DB + env):**  
   `cd backend && python -m pytest tests/test_rag.py -v`  
   These hit get_rag_status, get_indexed_count, retrieve, etc.

---

## Simple One-Line Summary

**We clean policy text before storing it, cap how much text we send to the AI, search with scores and smart top-k, cache answers/chunks/embeddings, run Ask in the background so the server doesn’t block, use safe AI settings and optional streaming, record timing/token metrics, and optionally use short section summaries for long policies and broad questions.**
