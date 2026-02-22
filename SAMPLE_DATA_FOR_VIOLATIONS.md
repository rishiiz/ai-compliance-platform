# How to Get Violations When You Connect the Database (Dollar)

Violations appear when the scan finds **rows in your company database (Dollar) that break the rules** from your uploaded policies.

- **If Dollar has no tables** (or tables with different names), the scan skips those rules and you see no violations.
- **If the tables exist but every row satisfies the rules**, you get 0 violations.
- **To see violations**, you need tables that match the rules **and** some rows that **fail** the rule.

---

## What the scan does

1. Loads rules from your uploaded policies (e.g. “compliance_verified must be true”, “retention_period_years ≤ 7”).
2. For each rule it runs a query on **Dollar** like:  
   `SELECT * FROM "table_name" WHERE NOT (rule_condition)`  
   So **violations** = rows where the rule condition is **false**.
3. Those rows are stored as violations and show in the dashboard and Review.

So: **violations = rows in Dollar that do not satisfy the rule.**

---

## Tables and columns the rules expect

Rules are extracted from your policy PDFs (or use fallback rules). They refer to:

- **`policy_docs`** – often used for document-level checks, e.g.:
  - `compliance_verified` (boolean)
  - `retention_period_years` (number)
  - `dpa_signed` (boolean)
- **`employees`** – if your policies mention training, access review, etc.:
  - `training_completed`, `date_of_joining`, `last_access_review_date`, `current_date`, etc.

If Dollar doesn’t have these tables/columns, those rules are skipped (no error, no violations for them).

---

## Sample data in Dollar that will produce violations

Run this in **pgAdmin → Dollar → Query Tool** to create `policy_docs` and insert rows that **violate** typical rules (so the scan will report them).

```sql
-- Create policy_docs if you don't have it yet
CREATE TABLE IF NOT EXISTS policy_docs (
    id SERIAL PRIMARY KEY,
    name TEXT,
    compliance_verified BOOLEAN DEFAULT false,
    retention_period_years INTEGER,
    dpa_signed BOOLEAN DEFAULT false
);

-- Insert rows that VIOLATE rules (so the scan finds violations)
-- Rule: "compliance_verified must be true"  -> row with false = violation
INSERT INTO policy_docs (name, compliance_verified, retention_period_years, dpa_signed)
VALUES
    ('Doc A', false, 3, true),   -- violation: compliance_verified false
    ('Doc B', true, 10, true),   -- violation: retention > 7 years
    ('Doc C', true, 2, false);   -- violation: dpa_signed false
```

After you run this:

1. In the app, connect to **Dollar** (Settings → Database).
2. Upload a policy (or use existing rules).
3. Click **Run scan now**.

You should see violations for the rows that fail each rule (e.g. Doc A for compliance_verified, Doc B for retention, Doc C for dpa_signed).

---

## Optional: employees table (for training / access-review rules)

If your policies produce rules on an `employees` table, create it and add rows that break the rule, for example:

```sql
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name TEXT,
    training_completed BOOLEAN DEFAULT false,
    date_of_joining DATE,
    last_access_review_date DATE,
    current_date DATE DEFAULT CURRENT_DATE
);

-- Example: employee who didn’t complete training within 30 days of joining
INSERT INTO employees (name, training_completed, date_of_joining, last_access_review_date, current_date)
VALUES
    ('Alice', false, '2024-01-01', NULL, CURRENT_DATE);
```

Then run the scan again; any rule that expects “training completed within 30 days” (or similar) should report a violation for that row.

---

## Summary

| You want | What to do in Dollar |
|----------|----------------------|
| **To see violations** | Have tables that match the rules (e.g. `policy_docs`) and insert rows that **do not** satisfy the rule (e.g. `compliance_verified = false`, `retention_period_years > 7`). |
| **To see no violations** | Either empty tables or only rows that satisfy every rule. |
| **Rules skipped** | Table or column doesn’t exist in Dollar; create the table/columns or ignore that rule. |

Run the `policy_docs` script above in Dollar, then run a scan — you should get violations.

---

## Why "Ask about compliance" says "No relevant policy content" even when the DB is connected

**Scan** and **Ask** both use the same company database (Dollar), but they use **different tables**:

| Feature | What it uses in Dollar | Purpose |
|--------|------------------------|--------|
| **Scan** | Tables like `employees`, `policy_docs` (from rules) | Runs SQL to find rows that **violate** rules → violations list |
| **Ask** | Table **`policy_documents`** with a **`content`** column | Searches **policy text** (paragraphs) to answer questions like "What is the data retention period?" |

So:

- **Violations show** = Dollar is connected and has data in tables the **scan** uses (e.g. `employees`, `policy_docs`).
- **"No relevant policy content found"** = The **Ask** feature looks for a table named **`policy_documents`** and a column **`content`** containing full policy text. If that table doesn’t exist, or is empty, or has no `content` column, Ask has nothing to search and shows that message.

**Fix:** Create in Dollar a table **`policy_documents`** with at least an **`id`** and a **`content`** (TEXT) column, and insert rows with actual policy text. Then "Ask about compliance" will find that text and Groq can answer.

---

## Sample data for "Ask about compliance"

Run this in **pgAdmin → Dollar → Query Tool** so questions like "What is the data retention period?" get answers:

```sql
-- Table for Ask about compliance (policy text search). Name must be policy_documents.
CREATE TABLE IF NOT EXISTS policy_documents (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT
);

-- Insert policy text so Ask can find it (e.g. for "data retention period")
INSERT INTO policy_documents (title, content)
VALUES
    ('Data retention', 'Data retention periods must not exceed 7 years. Personal data shall be deleted or anonymized after 7 years unless a longer period is required by law.'),
    ('Training', 'All employees must complete security and compliance training within 30 days of joining.'),
    ('DPA', 'Third-party processors must sign Data Processing Agreements (DPAs) before any data transfer.');
```

After this:

1. Keep Dollar connected (Settings → Database).
2. Go to **Ask about compliance** and ask e.g. **"What is the data retention period?"**

The app will search `policy_documents.content` for words from your question, return the matching row(s), and Groq will answer from that text — so you should no longer see "No relevant policy content found."
