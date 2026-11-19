"""
AI Answer Reliability Tracker - Advanced Web & API Server
Built with Python standard library (http.server, sqlite3, hashlib, json, csv).
Zero external dependencies required.
"""

import sys
import os
import json
import sqlite3
import hashlib
import csv
import io
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "reliability_tracker.db"
STATIC_DIR = BASE_DIR / "static"

# ---------- DATABASE INITIALIZATION & UTILITIES ----------

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_database():
    with get_db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS claims (
            claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_text TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General',
            status TEXT NOT NULL DEFAULT 'Unverified'
                CHECK(status IN ('Unverified','Verified','Disputed','Rejected')),
            confidence INTEGER NOT NULL DEFAULT 0 CHECK(confidence BETWEEN 0 AND 100),
            notes TEXT DEFAULT '',
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(user_id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS sources (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            credibility INTEGER NOT NULL DEFAULT 3 CHECK(credibility BETWEEN 1 AND 5),
            evidence TEXT DEFAULT '',
            added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS claim_sources (
            claim_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            relation_note TEXT DEFAULT '',
            PRIMARY KEY(claim_id, source_id),
            FOREIGN KEY(claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE,
            FOREIGN KEY(source_id) REFERENCES sources(source_id) ON DELETE CASCADE
        );

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

        CREATE INDEX IF NOT EXISTS idx_claim_status ON claims(status);
        CREATE INDEX IF NOT EXISTS idx_claim_category ON claims(category);

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

        CREATE TRIGGER IF NOT EXISTS trg_claim_update
        AFTER UPDATE OF status ON claims
        WHEN OLD.status <> NEW.status
        BEGIN
            INSERT INTO verification_history(claim_id, old_status, new_status, comment)
            VALUES(NEW.claim_id, OLD.status, NEW.status, 'Status updated via automated trigger');
        END;
        """)

        # Seed admin user if not present
        existing_admin = con.execute("SELECT user_id FROM users WHERE username='admin'").fetchone()
        if not existing_admin:
            con.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", hash_password("admin123"), "admin")
            )

        # Seed demo user
        existing_analyst = con.execute("SELECT user_id FROM users WHERE username='analyst'").fetchone()
        if not existing_analyst:
            con.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("analyst", hash_password("analyst123"), "analyst")
            )

        # Seed realistic claims and sources if the claims table is empty
        claim_count = con.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        if claim_count == 0:
            seed_initial_data(con)

def seed_initial_data(con):
    admin_id = con.execute("SELECT user_id FROM users WHERE username='admin'").fetchone()[0]

    # Sample sources
    sources_data = [
        ("NASA Climate Science Portal", "https://climate.nasa.gov/evidence/", 5, "Peer-reviewed global temperature records and satellite observations."),
        ("Nature Biotechnology Journal", "https://www.nature.com/nbt/", 5, "Leading peer-reviewed journal on biological tech and genomics."),
        ("World Health Organization (WHO)", "https://www.who.int/news-room/fact-sheets", 5, "Official global health guidelines and epidemiological studies."),
        ("MIT Technology Review", "https://www.technologyreview.com", 4, "High-credibility tech journalism with technical review by industry fellows."),
        ("Unverified Tech Forum Post", "https://forum.example.com/ai-rumors/409", 1, "Anonymous community user rumor with no citations or reproducible code.")
    ]
    con.executemany(
        "INSERT INTO sources (source_name, source_url, credibility, evidence) VALUES (?, ?, ?, ?)",
        sources_data
    )

    # Sample claims
    claims_data = [
        (
            "Global surface temperatures in 2023 were the warmest on record since modern records began in 1880.",
            "Climate Science",
            "Verified",
            96,
            "Validated against multiple independent datasets from NASA GISTEMP and NOAA GlobalTemp.",
            admin_id
        ),
        (
            "CRISPR-Cas9 gene editing has achieved complete hereditary eradication of all human cardiovascular diseases.",
            "Biotechnology",
            "Disputed",
            34,
            "Promising targeted in-vitro and mouse trials exist, but complete hereditary eradication is unsupported hype.",
            admin_id
        ),
        (
            "LLMs possess internal conscious metacognition and feel subjective pain when generating responses.",
            "Artificial Intelligence",
            "Rejected",
            12,
            "Mathematical next-token predictor architectures lack neurobiological substrate or metacognitive state.",
            admin_id
        ),
        (
            "Quantum computing algorithms can break standard RSA-2048 encryption using Shor's algorithm once fault-tolerant physical qubits reach sufficient scale.",
            "Quantum Computing",
            "Verified",
            91,
            "Mathematically proven by Peter Shor; physical fault-tolerant engineering remains in active progress worldwide.",
            admin_id
        ),
        (
            "Consuming 5000mg of Vitamin C daily permanently cures the common cold within 2 hours.",
            "Health & Medicine",
            "Rejected",
            8,
            "Contradicted by double-blind clinical trials published in Cochrane systematic reviews.",
            admin_id
        ),
        (
            "Multi-modal generative models achieve near-human zero-shot performance on diverse multimodal benchmarks like MMLU.",
            "Artificial Intelligence",
            "Unverified",
            65,
            "Requires deeper benchmark contamination analysis and standardized blind evaluations across frontier models.",
            admin_id
        )
    ]
    con.executemany(
        "INSERT INTO claims (claim_text, category, status, confidence, notes, created_by) VALUES (?, ?, ?, ?, ?, ?)",
        claims_data
    )

    # Link claims to sources
    links = [
        (1, 1, "Direct temperature anomaly data matches the 1.2C above baseline assertion."),
        (2, 2, "Paper specifies limitations and off-target risks in somatic tissue."),
        (3, 4, "Technical architectural breakdown of transformer attention mechanisms."),
        (4, 4, "Analysis on post-quantum cryptography transition timelines."),
        (5, 3, "Clinical summary stating mega-dose Vitamin C does not reduce cold duration significantly."),
        (6, 4, "Benchmarking review highlighting data leakage vulnerabilities.")
    ]
    con.executemany(
        "INSERT INTO claim_sources (claim_id, source_id, relation_note) VALUES (?, ?, ?)",
        links
    )

    # Initial verification history logs
    histories = [
        (1, "Unverified", "Verified", "Confirmed via NASA/NOAA peer-reviewed joint release.", admin_id),
        (2, "Unverified", "Disputed", "Downgraded due to exaggerated medical claims in AI output.", admin_id),
        (3, "Unverified", "Rejected", "Debunked based on fundamental neural network mechanics.", admin_id),
        (4, "Unverified", "Verified", "Cross-verified with theoretical quantum computer science literature.", admin_id),
        (5, "Unverified", "Rejected", "Clinical trial evidence directly refutes the claim.", admin_id)
    ]
    con.executemany(
        "INSERT INTO verification_history (claim_id, old_status, new_status, comment, changed_by) VALUES (?, ?, ?, ?, ?)",
        histories
    )

# ---------- IN-MEMORY SESSION STORE ----------
SESSIONS = {}

# ---------- REQUEST HANDLER ----------

class TrackerHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]} -> {args[2]}\n")

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status=400):
        self.send_json({"error": message, "success": False}, status=status)

    def get_session_user(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            return SESSIONS.get(token)
        cookie = self.headers.get("Cookie", "")
        for item in cookie.split(";"):
            if "session_token=" in item:
                token = item.split("session_token=")[1].strip()
                return SESSIONS.get(token)
        return None

    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return {}
            raw = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw)
        except Exception:
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    # ---------- GET ROUTER ----------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Static files
        if path == "/" or path == "/index.html":
            self.serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        elif path == "/style.css":
            self.serve_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            return
        elif path == "/app.js":
            self.serve_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        elif path == "/favicon.svg":
            self.serve_file(STATIC_DIR / "favicon.svg", "image/svg+xml")
            return

        # API Endpoints
        if path == "/api/me":
            user = self.get_session_user()
            if user:
                self.send_json({"user": user, "authenticated": True})
            else:
                self.send_json({"user": None, "authenticated": False})
            return

        if path == "/api/dashboard":
            self.handle_dashboard()
            return

        if path == "/api/claims":
            self.handle_get_claims(query)
            return

        if path.startswith("/api/claims/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                self.handle_get_claim_detail(int(parts[2]))
                return

        if path == "/api/sources":
            self.handle_get_sources()
            return

        if path == "/api/history":
            self.handle_get_history(query)
            return

        if path == "/api/export/csv":
            self.handle_export_csv()
            return

        # 404 for unknown path
        self.send_error_json(f"Endpoint not found: {path}", 404)

    # ---------- POST ROUTER ----------
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/login":
            data = self.read_json_body()
            if not data:
                self.send_error_json("Invalid JSON body")
                return
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", "")).strip()
            if not username or not password:
                self.send_error_json("Username and password are required")
                return

            with get_db() as con:
                row = con.execute(
                    "SELECT user_id, username, role, created_at FROM users WHERE username=? AND password_hash=?",
                    (username, hash_password(password))
                ).fetchone()

            if row:
                user = dict(row)
                token = hashlib.sha256(f"{user['user_id']}-{datetime.now().isoformat()}".encode()).hexdigest()
                SESSIONS[token] = user
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", f"session_token={token}; Path=/; HttpOnly; SameSite=Lax")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                res = {"success": True, "token": token, "user": user}
                self.wfile.write(json.dumps(res).encode("utf-8"))
            else:
                self.send_error_json("Invalid username or password", 401)
            return

        if path == "/api/logout":
            token = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
            if token in SESSIONS:
                del SESSIONS[token]
            self.send_json({"success": True, "message": "Logged out successfully"})
            return

        if path == "/api/claims":
            self.handle_create_claim()
            return

        if path.startswith("/api/claims/") and path.endswith("/status"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[2].isdigit():
                self.handle_change_status(int(parts[2]))
                return

        if path.startswith("/api/claims/") and path.endswith("/sources"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[2].isdigit():
                self.handle_link_source(int(parts[2]))
                return

        if path == "/api/sources":
            self.handle_create_source()
            return

        self.send_error_json(f"Endpoint not found: {path}", 404)

    # ---------- PUT ROUTER ----------
    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/claims/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                self.handle_update_claim(int(parts[2]))
                return

        if path.startswith("/api/sources/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                self.handle_update_source(int(parts[2]))
                return

        self.send_error_json(f"Endpoint not found: {path}", 404)

    # ---------- DELETE ROUTER ----------
    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/claims/"):
            parts = path.strip("/").split("/")
            # DELETE /api/claims/{id}
            if len(parts) == 3 and parts[2].isdigit():
                self.handle_delete_claim(int(parts[2]))
                return
            # DELETE /api/claims/{claim_id}/sources/{source_id}
            if len(parts) == 5 and parts[2].isdigit() and parts[3] == "sources" and parts[4].isdigit():
                self.handle_unlink_source(int(parts[2]), int(parts[4]))
                return

        if path.startswith("/api/sources/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                self.handle_delete_source(int(parts[2]))
                return

        self.send_error_json(f"Endpoint not found: {path}", 404)

    # ---------- HANDLER IMPLEMENTATIONS ----------

    def serve_file(self, filepath: Path, content_type: str):
        if not filepath.exists():
            self.send_error_json(f"File not found: {filepath.name}", 404)
            return
        content = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_dashboard(self):
        with get_db() as con:
            total_claims = con.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
            status_counts_rows = con.execute("SELECT status, COUNT(*) as cnt FROM claims GROUP BY status").fetchall()
            status_counts = {"Verified": 0, "Unverified": 0, "Disputed": 0, "Rejected": 0}
            for row in status_counts_rows:
                status_counts[row["status"]] = row["cnt"]

            avg_conf = con.execute("SELECT COALESCE(AVG(confidence), 0) FROM claims WHERE status='Verified'").fetchone()[0]
            total_sources = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            avg_source_cred = con.execute("SELECT COALESCE(AVG(credibility), 0) FROM sources").fetchone()[0]

            recent_claims = con.execute("""
                SELECT c.claim_id, c.claim_text, c.category, c.status, c.confidence, c.created_at,
                       COUNT(cs.source_id) as source_count
                FROM claims c
                LEFT JOIN claim_sources cs ON c.claim_id = cs.claim_id
                GROUP BY c.claim_id
                ORDER BY c.created_at DESC
                LIMIT 5
            """).fetchall()

            categories_rows = con.execute("SELECT category, COUNT(*) as cnt FROM claims GROUP BY category ORDER BY cnt DESC LIMIT 5").fetchall()

        self.send_json({
            "total_claims": total_claims,
            "status_counts": status_counts,
            "avg_verified_confidence": round(float(avg_conf), 1),
            "total_sources": total_sources,
            "avg_source_credibility": round(float(avg_source_cred), 1),
            "recent_claims": [dict(r) for r in recent_claims],
            "top_categories": [dict(r) for r in categories_rows]
        })

    def handle_get_claims(self, query):
        q = query.get("q", [""])[0].strip()
        status = query.get("status", ["All"])[0].strip()
        category = query.get("category", ["All"])[0].strip()

        sql = "SELECT * FROM v_claim_summary WHERE 1=1"
        args = []

        if q:
            sql += " AND (claim_text LIKE ? OR category LIKE ? OR notes LIKE ?)"
            pattern = f"%{q}%"
            args.extend([pattern, pattern, pattern])

        if status and status != "All":
            sql += " AND status = ?"
            args.append(status)

        if category and category != "All":
            sql += " AND category = ?"
            args.append(category)

        sql += " ORDER BY claim_id DESC"

        with get_db() as con:
            rows = con.execute(sql, args).fetchall()
            # Also get distinct categories for filter dropdown
            cats = [r["category"] for r in con.execute("SELECT DISTINCT category FROM claims ORDER BY category").fetchall()]

        self.send_json({
            "claims": [dict(r) for r in rows],
            "categories": cats,
            "count": len(rows)
        })

    def handle_get_claim_detail(self, claim_id: int):
        with get_db() as con:
            claim = con.execute("SELECT * FROM v_claim_summary WHERE claim_id = ?", (claim_id,)).fetchone()
            if not claim:
                self.send_error_json("Claim not found", 404)
                return

            # Linked sources
            sources = con.execute("""
                SELECT s.source_id, s.source_name, s.source_url, s.credibility, s.evidence, cs.relation_note
                FROM sources s
                JOIN claim_sources cs ON s.source_id = cs.source_id
                WHERE cs.claim_id = ?
                ORDER BY s.credibility DESC
            """, (claim_id,)).fetchall()

            # Verification history
            history = con.execute("""
                SELECT vh.history_id, vh.old_status, vh.new_status, vh.comment, vh.changed_at, u.username as changed_by_name
                FROM verification_history vh
                LEFT JOIN users u ON vh.changed_by = u.user_id
                WHERE vh.claim_id = ?
                ORDER BY vh.changed_at DESC
            """, (claim_id,)).fetchall()

        self.send_json({
            "claim": dict(claim),
            "sources": [dict(s) for s in sources],
            "history": [dict(h) for h in history]
        })

    def handle_create_claim(self):
        user = self.get_session_user()
        data = self.read_json_body()
        if not data:
            self.send_error_json("Invalid JSON payload")
            return

        claim_text = str(data.get("claim_text", "")).strip()
        category = str(data.get("category", "General")).strip() or "General"
        confidence = data.get("confidence", 0)
        notes = str(data.get("notes", "")).strip()

        if not claim_text:
            self.send_error_json("Claim text is required and cannot be empty")
            return

        try:
            confidence = int(confidence)
            if not (0 <= confidence <= 100):
                raise ValueError()
        except (ValueError, TypeError):
            self.send_error_json("Confidence must be an integer between 0 and 100")
            return

        user_id = user["user_id"] if user else None

        with get_db() as con:
            cursor = con.execute(
                "INSERT INTO claims (claim_text, category, confidence, notes, created_by) VALUES (?, ?, ?, ?, ?)",
                (claim_text, category, confidence, notes, user_id)
            )
            new_id = cursor.lastrowid

            # If user provided initial sources to link
            source_ids = data.get("source_ids", [])
            for sid in source_ids:
                try:
                    con.execute("INSERT INTO claim_sources (claim_id, source_id) VALUES (?, ?)", (new_id, int(sid)))
                except sqlite3.IntegrityError:
                    pass

        self.send_json({"success": True, "claim_id": new_id, "message": "Claim registered successfully"}, status=201)

    def handle_update_claim(self, claim_id: int):
        data = self.read_json_body()
        if not data:
            self.send_error_json("Invalid JSON payload")
            return

        claim_text = str(data.get("claim_text", "")).strip()
        category = str(data.get("category", "General")).strip() or "General"
        confidence = data.get("confidence", 0)
        notes = str(data.get("notes", "")).strip()

        if not claim_text:
            self.send_error_json("Claim text is required")
            return

        try:
            confidence = int(confidence)
            if not (0 <= confidence <= 100):
                raise ValueError()
        except (ValueError, TypeError):
            self.send_error_json("Confidence must be an integer between 0 and 100")
            return

        with get_db() as con:
            check = con.execute("SELECT claim_id FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
            if not check:
                self.send_error_json("Claim not found", 404)
                return

            con.execute("""
                UPDATE claims 
                SET claim_text = ?, category = ?, confidence = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE claim_id = ?
            """, (claim_text, category, confidence, notes, claim_id))

        self.send_json({"success": True, "message": "Claim updated successfully"})

    def handle_delete_claim(self, claim_id: int):
        with get_db() as con:
            check = con.execute("SELECT claim_id FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
            if not check:
                self.send_error_json("Claim not found", 404)
                return
            con.execute("DELETE FROM claims WHERE claim_id = ?", (claim_id,))
        self.send_json({"success": True, "message": "Claim deleted along with associated audit history and links"})

    def handle_change_status(self, claim_id: int):
        user = self.get_session_user()
        data = self.read_json_body()
        if not data:
            self.send_error_json("Invalid JSON payload")
            return

        new_status = str(data.get("status", "")).strip()
        comment = str(data.get("comment", "")).strip() or "Status updated by user"

        if new_status not in ["Unverified", "Verified", "Disputed", "Rejected"]:
            self.send_error_json("Invalid status. Allowed values: Unverified, Verified, Disputed, Rejected")
            return

        user_id = user["user_id"] if user else None

        with get_db() as con:
            current = con.execute("SELECT status FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
            if not current:
                self.send_error_json("Claim not found", 404)
                return

            old_status = current["status"]

            # Update status in claims table
            con.execute(
                "UPDATE claims SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE claim_id = ?",
                (new_status, claim_id)
            )

            # Insert verification history log with user context
            con.execute("""
                INSERT INTO verification_history (claim_id, old_status, new_status, comment, changed_by)
                VALUES (?, ?, ?, ?, ?)
            """, (claim_id, old_status, new_status, comment, user_id))

        self.send_json({"success": True, "message": f"Status updated to '{new_status}' with audit log"})

    def handle_get_sources(self):
        with get_db() as con:
            rows = con.execute("""
                SELECT s.source_id, s.source_name, s.source_url, s.credibility, s.evidence, s.added_at,
                       COUNT(cs.claim_id) as linked_claims_count
                FROM sources s
                LEFT JOIN claim_sources cs ON s.source_id = cs.source_id
                GROUP BY s.source_id
                ORDER BY s.source_id DESC
            """).fetchall()
        self.send_json({"sources": [dict(r) for r in rows], "count": len(rows)})

    def handle_create_source(self):
        data = self.read_json_body()
        if not data:
            self.send_error_json("Invalid JSON payload")
            return

        name = str(data.get("source_name", "")).strip()
        url = str(data.get("source_url", "")).strip()
        credibility = data.get("credibility", 3)
        evidence = str(data.get("evidence", "")).strip()

        if not name or not url:
            self.send_error_json("Source name and URL are required")
            return

        if not (url.lower().startswith("http://") or url.lower().startswith("https://")):
            self.send_error_json("URL must start with http:// or https://")
            return

        try:
            credibility = int(credibility)
            if not (1 <= credibility <= 5):
                raise ValueError()
        except (ValueError, TypeError):
            self.send_error_json("Credibility must be an integer between 1 and 5")
            return

        with get_db() as con:
            cursor = con.execute(
                "INSERT INTO sources (source_name, source_url, credibility, evidence) VALUES (?, ?, ?, ?)",
                (name, url, credibility, evidence)
            )
            sid = cursor.lastrowid

        self.send_json({"success": True, "source_id": sid, "message": "Source added successfully"}, status=201)

    def handle_update_source(self, source_id: int):
        data = self.read_json_body()
        if not data:
            self.send_error_json("Invalid JSON payload")
            return

        name = str(data.get("source_name", "")).strip()
        url = str(data.get("source_url", "")).strip()
        credibility = data.get("credibility", 3)
        evidence = str(data.get("evidence", "")).strip()

        if not name or not url:
            self.send_error_json("Source name and URL are required")
            return

        if not (url.lower().startswith("http://") or url.lower().startswith("https://")):
            self.send_error_json("URL must start with http:// or https://")
            return

        try:
            credibility = int(credibility)
            if not (1 <= credibility <= 5):
                raise ValueError()
        except (ValueError, TypeError):
            self.send_error_json("Credibility must be between 1 and 5")
            return

        with get_db() as con:
            check = con.execute("SELECT source_id FROM sources WHERE source_id = ?", (source_id,)).fetchone()
            if not check:
                self.send_error_json("Source not found", 404)
                return
            con.execute("""
                UPDATE sources 
                SET source_name = ?, source_url = ?, credibility = ?, evidence = ?
                WHERE source_id = ?
            """, (name, url, credibility, evidence, source_id))

        self.send_json({"success": True, "message": "Source updated successfully"})

    def handle_delete_source(self, source_id: int):
        with get_db() as con:
            check = con.execute("SELECT source_id FROM sources WHERE source_id = ?", (source_id,)).fetchone()
            if not check:
                self.send_error_json("Source not found", 404)
                return
            con.execute("DELETE FROM sources WHERE source_id = ?", (source_id,))
        self.send_json({"success": True, "message": "Source and associated links removed successfully"})

    def handle_link_source(self, claim_id: int):
        data = self.read_json_body()
        if not data:
            self.send_error_json("Invalid JSON payload")
            return

        source_id = data.get("source_id")
        relation_note = str(data.get("relation_note", "")).strip()

        if not source_id:
            self.send_error_json("source_id is required")
            return

        try:
            source_id = int(source_id)
        except ValueError:
            self.send_error_json("source_id must be an integer")
            return

        with get_db() as con:
            # Check existence
            c_check = con.execute("SELECT claim_id FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
            s_check = con.execute("SELECT source_id FROM sources WHERE source_id = ?", (source_id,)).fetchone()
            if not c_check or not s_check:
                self.send_error_json("Claim or source does not exist", 404)
                return

            try:
                con.execute(
                    "INSERT INTO claim_sources (claim_id, source_id, relation_note) VALUES (?, ?, ?)",
                    (claim_id, source_id, relation_note)
                )
            except sqlite3.IntegrityError:
                con.execute(
                    "UPDATE claim_sources SET relation_note = ? WHERE claim_id = ? AND source_id = ?",
                    (relation_note, claim_id, source_id)
                )

        self.send_json({"success": True, "message": "Source successfully linked to claim"})

    def handle_unlink_source(self, claim_id: int, source_id: int):
        with get_db() as con:
            con.execute("DELETE FROM claim_sources WHERE claim_id = ? AND source_id = ?", (claim_id, source_id))
        self.send_json({"success": True, "message": "Link removed successfully"})

    def handle_get_history(self, query):
        claim_id = query.get("claim_id", [None])[0]
        sql = """
            SELECT vh.history_id, vh.claim_id, c.claim_text, vh.old_status, vh.new_status,
                   vh.comment, vh.changed_at, u.username as changed_by_name
            FROM verification_history vh
            JOIN claims c ON vh.claim_id = c.claim_id
            LEFT JOIN users u ON vh.changed_by = u.user_id
        """
        args = []
        if claim_id and claim_id.isdigit():
            sql += " WHERE vh.claim_id = ?"
            args.append(int(claim_id))
        sql += " ORDER BY vh.changed_at DESC"

        with get_db() as con:
            rows = con.execute(sql, args).fetchall()

        self.send_json({"history": [dict(r) for r in rows], "count": len(rows)})

    def handle_export_csv(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Claim ID",
            "Claim Statement",
            "Category",
            "Verification Status",
            "Confidence (%)",
            "Linked Sources Count",
            "Avg Source Credibility",
            "Author",
            "Created Date",
            "Last Updated Date",
            "Evidence / Notes"
        ])

        with get_db() as con:
            rows = con.execute("SELECT * FROM v_claim_summary ORDER BY claim_id ASC").fetchall()
            for r in rows:
                writer.writerow([
                    r["claim_id"],
                    r["claim_text"],
                    r["category"],
                    r["status"],
                    r["confidence"],
                    r["source_count"],
                    r["avg_source_credibility"] or 0,
                    r["author_name"] or "System",
                    r["created_at"],
                    r["updated_at"],
                    r["notes"] or ""
                ])

        csv_data = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="AI_Answer_Reliability_Report.csv"')
        self.send_header("Content-Length", str(len(csv_data)))
        self.end_headers()
        self.wfile.write(csv_data)

# ---------- MAIN SERVER ENTRY ----------

def run_server(port=8000):
    init_database()
    server_address = ("127.0.0.1", port)
    try:
        httpd = HTTPServer(server_address, TrackerHandler)
    except OSError:
        # Try alternate port if 8000 is busy
        port = 8080
        server_address = ("127.0.0.1", port)
        httpd = HTTPServer(server_address, TrackerHandler)

    print(f"============================================================")
    print(f" AI Answer Reliability Tracker - Advanced Edition")
    print(f" Minimal Cream & Orange Theme | Figtree Typography")
    print(f" Web Server running at: http://127.0.0.1:{port}/")
    print(f" Default Credentials: admin / admin123")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully.")
        httpd.server_close()

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
