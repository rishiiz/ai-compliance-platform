-- Create the policy_documents table in your company MySQL database (e.g. compliance_db).
-- Run this in MySQL Workbench, command line, or any MySQL client connected to your company DB.
-- After connecting in Settings → Database, the dashboard and "Ask about compliance" use this table.

CREATE TABLE IF NOT EXISTS policy_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NULL,
    content TEXT NOT NULL
);

-- Optional: sample rows so "Ask about compliance" can answer questions
INSERT INTO policy_documents (title, content) VALUES
    ('Data retention', 'Data retention periods must not exceed 7 years. Personal data shall be deleted or anonymized after 7 years unless a longer period is required by law.'),
    ('Training', 'All employees must complete security and compliance training within 30 days of joining.'),
    ('DPA', 'Third-party processors must sign Data Processing Agreements (DPAs) before any data transfer.');
