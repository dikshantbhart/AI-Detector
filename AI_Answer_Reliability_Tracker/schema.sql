-- ====================================================================
-- AI Answer Reliability Tracker — Database Schema & Initial Seeds
-- Relational Database: SQLite 3
-- Concepts: Foreign Keys, Cascade Deletes, Indexes, Views, Triggers
-- ====================================================================

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------------------
-- 1. USERS TABLE
-- Handles authentication, roles (admin / user / analyst), and audit trails
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 2. CLAIMS TABLE
-- Stores atomic AI-generated assertions, category, status, and confidence
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims (
    claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_text TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'General',
    status TEXT NOT NULL DEFAULT 'Unverified'
        CHECK(status IN ('Unverified', 'Verified', 'Disputed', 'Rejected')),
    confidence INTEGER NOT NULL DEFAULT 0 CHECK(confidence BETWEEN 0 AND 100),
    notes TEXT DEFAULT '',
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- --------------------------------------------------------------------
-- 3. SOURCES TABLE
-- Catalogs corroborating / refuting evidence citations with credibility
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    credibility INTEGER NOT NULL DEFAULT 3 CHECK(credibility BETWEEN 1 AND 5),
    evidence TEXT DEFAULT '',
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 4. CLAIM_SOURCES JUNCTION TABLE (Many-to-Many Mapping)
-- Connects multiple sources to one claim, and one source to many claims
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_sources (
    claim_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    relation_note TEXT DEFAULT '',
    PRIMARY KEY(claim_id, source_id),
    FOREIGN KEY(claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE,
    FOREIGN KEY(source_id) REFERENCES sources(source_id) ON DELETE CASCADE
);

-- --------------------------------------------------------------------
-- 5. VERIFICATION_HISTORY TABLE
-- Permanent chronological ledger of all status transitions & remarks
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verification_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    comment TEXT DEFAULT '',
    changed_by INTEGER,
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE,
    FOREIGN KEY(changed_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- --------------------------------------------------------------------
-- 6. INDEXES FOR QUERY OPTIMIZATION
-- Speeds up filtering and searching on large datasets
-- --------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_claim_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claim_category ON claims(category);
CREATE INDEX IF NOT EXISTS idx_claim_created ON claims(created_at);

-- --------------------------------------------------------------------
-- 7. SQL VIEW: v_claim_summary
-- Aggregate view calculating total linked sources & average credibility
-- --------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_claim_summary AS
SELECT 
    c.claim_id,
    c.claim_text,
    c.category,
    c.status,
    c.confidence,
    c.notes,
    c.created_by,
    u.username AS author_name,
    c.created_at,
    c.updated_at,
    COUNT(cs.source_id) AS source_count,
    ROUND(AVG(s.credibility), 1) AS avg_source_credibility
FROM claims c
LEFT JOIN users u ON c.created_by = u.user_id
LEFT JOIN claim_sources cs ON c.claim_id = cs.claim_id
LEFT JOIN sources s ON cs.source_id = s.source_id
GROUP BY c.claim_id;

-- --------------------------------------------------------------------
-- 8. SQL TRIGGER: trg_claim_update
-- Automatically logs status updates to verification_history
-- --------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_claim_update
AFTER UPDATE OF status ON claims
WHEN OLD.status <> NEW.status
BEGIN
    INSERT INTO verification_history(claim_id, old_status, new_status, comment)
    VALUES(NEW.claim_id, OLD.status, NEW.status, 'Status updated via automated trigger');
END;

-- ====================================================================
-- SEED DATA (Demo Users, Sources, Claims & Audit Logs)
-- ====================================================================

-- Demo Admin (Password: admin123 -> SHA-256)
INSERT OR IGNORE INTO users (user_id, username, password_hash, role)
VALUES (1, 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin');

-- Demo Analyst (Password: analyst123 -> SHA-256)
INSERT OR IGNORE INTO users (user_id, username, password_hash, role)
VALUES (2, 'analyst', '82a201b1df400c4decdfe8d8e578c78be4bd276ad41680d2389d38c201620d43', 'analyst');

-- Corroborating Sources
INSERT OR IGNORE INTO sources (source_id, source_name, source_url, credibility, evidence) VALUES
(1, 'NASA Climate Science Portal', 'https://climate.nasa.gov/evidence/', 5, 'Peer-reviewed global temperature records and satellite observations.'),
(2, 'Nature Biotechnology Journal', 'https://www.nature.com/nbt/', 5, 'Leading peer-reviewed journal on biological tech and genomics.'),
(3, 'World Health Organization (WHO)', 'https://www.who.int/news-room/fact-sheets', 5, 'Official global health guidelines and epidemiological studies.'),
(4, 'MIT Technology Review', 'https://www.technologyreview.com', 4, 'High-credibility tech journalism with technical review by industry fellows.'),
(5, 'Unverified Tech Forum Post', 'https://forum.example.com/ai-rumors/409', 1, 'Anonymous community user rumor with no citations or reproducible code.');

-- Sample AI Claims
INSERT OR IGNORE INTO claims (claim_id, claim_text, category, status, confidence, notes, created_by) VALUES
(1, 'Global surface temperatures in 2023 were the warmest on record since modern records began in 1880.', 'Climate Science', 'Verified', 96, 'Validated against multiple independent datasets from NASA GISTEMP and NOAA GlobalTemp.', 1),
(2, 'CRISPR-Cas9 gene editing has achieved complete hereditary eradication of all human cardiovascular diseases.', 'Biotechnology', 'Disputed', 34, 'Promising targeted in-vitro and mouse trials exist, but complete hereditary eradication is unsupported hype.', 1),
(3, 'LLMs possess internal conscious metacognition and feel subjective pain when generating responses.', 'Artificial Intelligence', 'Rejected', 12, 'Mathematical next-token predictor architectures lack neurobiological substrate or metacognitive state.', 1),
(4, 'Quantum computing algorithms can break standard RSA-2048 encryption using Shor''s algorithm once fault-tolerant physical qubits reach sufficient scale.', 'Quantum Computing', 'Verified', 91, 'Mathematically proven by Peter Shor; physical fault-tolerant engineering remains in active progress worldwide.', 1),
(5, 'Consuming 5000mg of Vitamin C daily permanently cures the common cold within 2 hours.', 'Health & Medicine', 'Rejected', 8, 'Contradicted by double-blind clinical trials published in Cochrane systematic reviews.', 1),
(6, 'Multi-modal generative models achieve near-human zero-shot performance on diverse multimodal benchmarks like MMLU.', 'Artificial Intelligence', 'Unverified', 65, 'Requires deeper benchmark contamination analysis and standardized blind evaluations across frontier models.', 1);

-- Link Claims to Sources
INSERT OR IGNORE INTO claim_sources (claim_id, source_id, relation_note) VALUES
(1, 1, 'Direct temperature anomaly data matches the 1.2C above baseline assertion.'),
(2, 2, 'Paper specifies limitations and off-target risks in somatic tissue.'),
(3, 4, 'Technical architectural breakdown of transformer attention mechanisms.'),
(4, 4, 'Analysis on post-quantum cryptography transition timelines.'),
(5, 3, 'Clinical summary stating mega-dose Vitamin C does not reduce cold duration significantly.'),
(6, 4, 'Benchmarking review highlighting data leakage vulnerabilities.');

-- Verification Audit Trail
INSERT OR IGNORE INTO verification_history (history_id, claim_id, old_status, new_status, comment, changed_by) VALUES
(1, 1, 'Unverified', 'Verified', 'Confirmed via NASA/NOAA peer-reviewed joint release.', 1),
(2, 2, 'Unverified', 'Disputed', 'Downgraded due to exaggerated medical claims in AI output.', 1),
(3, 3, 'Unverified', 'Rejected', 'Debunked based on fundamental neural network mechanics.', 1),
(4, 4, 'Unverified', 'Verified', 'Cross-verified with theoretical quantum computer science literature.', 1),
(5, 5, 'Unverified', 'Rejected', 'Clinical trial evidence directly refutes the claim.', 1);
