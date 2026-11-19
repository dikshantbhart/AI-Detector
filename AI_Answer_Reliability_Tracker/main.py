"""
AI Answer Reliability Tracker — Advanced Desktop Application
Theme: Minimal Cream & Orange Theme
Palette:
  - Soft White:  #FFFDF8
  - Warm Cream:  #F7F2E8
  - Off White:   #F3EBDD
  - Soft Orange: #E9A15B
  - Deep Orange: #D97732
  - Dark Text:   #3D342C
Typography: Figtree (with Segoe UI fallback)
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
import hashlib
import csv
import webbrowser

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "reliability_tracker.db"

# ---------- THEME CONSTANTS ----------
COLOR_SOFT_WHITE = "#FFFDF8"
COLOR_WARM_CREAM = "#F7F2E8"
COLOR_OFF_WHITE  = "#F3EBDD"
COLOR_SOFT_ORANGE= "#E9A15B"
COLOR_DEEP_ORANGE= "#D97732"
COLOR_DARK_TEXT  = "#3D342C"
COLOR_MUTED_TEXT = "#6B6258"

STATUS_COLORS = {
    "Verified":   "#2C7A4B",
    "Unverified": "#D97732",
    "Disputed":   "#B9382F",
    "Rejected":   "#585049"
}

FONT_FAMILY = "Figtree"

def get_font(size=10, weight="normal"):
    return (FONT_FAMILY, size, weight)

# ---------- DATABASE ----------
def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def initialize_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS claims(
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
        CREATE TABLE IF NOT EXISTS sources(
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            credibility INTEGER NOT NULL DEFAULT 3 CHECK(credibility BETWEEN 1 AND 5),
            evidence TEXT DEFAULT '',
            added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS claim_sources(
            claim_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            relation_note TEXT DEFAULT '',
            PRIMARY KEY(claim_id,source_id),
            FOREIGN KEY(claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE,
            FOREIGN KEY(source_id) REFERENCES sources(source_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS verification_history(
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
          SELECT c.claim_id, c.claim_text, c.category, c.status, c.confidence,
                 c.created_at, c.updated_at, COUNT(cs.source_id) AS source_count
          FROM claims c LEFT JOIN claim_sources cs ON c.claim_id=cs.claim_id
          GROUP BY c.claim_id;
        CREATE TRIGGER IF NOT EXISTS trg_claim_update
          AFTER UPDATE OF status ON claims
          WHEN OLD.status <> NEW.status
          BEGIN
            INSERT INTO verification_history(claim_id,old_status,new_status,comment)
            VALUES(NEW.claim_id,OLD.status,NEW.status,'Status changed via audit trigger');
          END;
        """)
        existing = con.execute("SELECT user_id FROM users WHERE username='admin'").fetchone()
        if not existing:
            con.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                        ("admin", hash_password("admin123"), "admin"))

# ---------- APP ----------
class TrackerApp:
    def __init__(self, root):
        self.root = root
        self.user = None
        self.root.title("AI Answer Reliability Tracker — Minimal Cream & Orange Edition")
        self.root.geometry("1120x740")
        self.root.minsize(940, 620)
        self.root.configure(bg=COLOR_WARM_CREAM)

        self.apply_theme()
        self.login_screen()

    def apply_theme(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        # Base background configuration
        self.style.configure(".", background=COLOR_WARM_CREAM, foreground=COLOR_DARK_TEXT, font=get_font(10))

        # Frames
        self.style.configure("TFrame", background=COLOR_WARM_CREAM)
        self.style.configure("Card.TFrame", background=COLOR_SOFT_WHITE, relief="solid", borderwidth=1)
        self.style.configure("TopBar.TFrame", background=COLOR_SOFT_WHITE)

        # Labels
        self.style.configure("TLabel", background=COLOR_WARM_CREAM, foreground=COLOR_DARK_TEXT, font=get_font(10))
        self.style.configure("Muted.TLabel", foreground=COLOR_MUTED_TEXT, font=get_font(9))
        self.style.configure("Header.TLabel", background=COLOR_SOFT_WHITE, font=get_font(16, "bold"), foreground=COLOR_DARK_TEXT)
        self.style.configure("Brand.TLabel", background=COLOR_SOFT_WHITE, font=get_font(11, "bold"), foreground=COLOR_DEEP_ORANGE)

        # Buttons
        self.style.configure("TButton", background=COLOR_SOFT_WHITE, foreground=COLOR_DARK_TEXT,
                             font=get_font(9, "bold"), borderwidth=1, focuscolor=COLOR_DEEP_ORANGE, padding=6)
        self.style.map("TButton",
                       background=[("active", COLOR_OFF_WHITE), ("pressed", COLOR_SOFT_ORANGE)],
                       foreground=[("active", COLOR_DEEP_ORANGE)])

        self.style.configure("Primary.TButton", background=COLOR_DEEP_ORANGE, foreground=COLOR_SOFT_WHITE,
                             font=get_font(9, "bold"), borderwidth=0, padding=6)
        self.style.map("Primary.TButton",
                       background=[("active", "#B85F22"), ("pressed", "#9B4C15")],
                       foreground=[("active", COLOR_SOFT_WHITE)])

        # Notebook (Tabs)
        self.style.configure("TNotebook", background=COLOR_WARM_CREAM, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=COLOR_OFF_WHITE, foreground=COLOR_MUTED_TEXT,
                             padding=[14, 8], font=get_font(10, "bold"), borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[("selected", COLOR_SOFT_WHITE), ("active", COLOR_WARM_CREAM)],
                       foreground=[("selected", COLOR_DEEP_ORANGE)])

        # Treeview (Data tables)
        self.style.configure("Treeview", background=COLOR_SOFT_WHITE, foreground=COLOR_DARK_TEXT,
                             fieldbackground=COLOR_SOFT_WHITE, rowheight=30, font=get_font(9), borderwidth=0)
        self.style.configure("Treeview.Heading", background=COLOR_OFF_WHITE, foreground=COLOR_DARK_TEXT,
                             font=get_font(9, "bold"), relief="flat", padding=6)
        self.style.map("Treeview",
                       background=[("selected", COLOR_OFF_WHITE)],
                       foreground=[("selected", COLOR_DEEP_ORANGE)])

        # LabelFrame
        self.style.configure("TLabelframe", background=COLOR_SOFT_WHITE, relief="solid", borderwidth=1)
        self.style.configure("TLabelframe.Label", background=COLOR_SOFT_WHITE, foreground=COLOR_DARK_TEXT, font=get_font(10, "bold"))

    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def login_screen(self):
        self.clear()
        card = tk.Frame(self.root, bg=COLOR_SOFT_WHITE, bd=1, relief="solid", padx=40, pady=35)
        card.place(relx=0.5, rely=0.5, anchor="center")

        logo_label = tk.Label(card, text="🛡️", font=(FONT_FAMILY, 32), bg=COLOR_SOFT_WHITE, fg=COLOR_DEEP_ORANGE)
        logo_label.pack(pady=(0, 4))

        tk.Label(card, text="AI ANSWER RELIABILITY TRACKER", font=get_font(16, "bold"),
                 bg=COLOR_SOFT_WHITE, fg=COLOR_DARK_TEXT).pack(pady=(0, 4))
        tk.Label(card, text="Minimal Cream & Orange Edition • SQLite Persistence", font=get_font(9),
                 bg=COLOR_SOFT_WHITE, fg=COLOR_MUTED_TEXT).pack(pady=(0, 20))

        tk.Label(card, text="Username", font=get_font(10, "bold"), bg=COLOR_SOFT_WHITE, fg=COLOR_DARK_TEXT).pack(anchor="w")
        username_entry = tk.Entry(card, width=32, font=get_font(10), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT,
                                  relief="solid", bd=1, highlightthickness=1, highlightcolor=COLOR_DEEP_ORANGE)
        username_entry.pack(pady=(4, 12), ipady=5)
        username_entry.insert(0, "admin")

        tk.Label(card, text="Password", font=get_font(10, "bold"), bg=COLOR_SOFT_WHITE, fg=COLOR_DARK_TEXT).pack(anchor="w")
        password_entry = tk.Entry(card, width=32, show="•", font=get_font(10), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT,
                                  relief="solid", bd=1, highlightthickness=1, highlightcolor=COLOR_DEEP_ORANGE)
        password_entry.pack(pady=(4, 16), ipady=5)
        password_entry.insert(0, "admin123")

        def login():
            u = username_entry.get().strip()
            p = password_entry.get().strip()
            with connect() as con:
                row = con.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                                  (u, hash_password(p))).fetchone()
            if row:
                self.user = dict(row)
                self.main_screen()
            else:
                messagebox.showerror("Authentication Failed", "Invalid username or password.")

        btn = tk.Button(card, text="Sign In", command=login, font=get_font(10, "bold"),
                        bg=COLOR_DEEP_ORANGE, fg=COLOR_SOFT_WHITE, activebackground="#B85F22",
                        activeforeground=COLOR_SOFT_WHITE, relief="flat", bd=0, padx=16, pady=8, cursor="hand2")
        btn.pack(fill="x", pady=(8, 12))

        tk.Label(card, text="Demo Login: admin / admin123", font=get_font(8),
                 bg=COLOR_SOFT_WHITE, fg=COLOR_MUTED_TEXT).pack()

    def main_screen(self):
        self.clear()

        # Top Bar
        top = tk.Frame(self.root, bg=COLOR_SOFT_WHITE, bd=1, relief="solid", padx=20, pady=12)
        top.pack(fill="x")

        brand_frame = tk.Frame(top, bg=COLOR_SOFT_WHITE)
        brand_frame.pack(side="left")
        tk.Label(brand_frame, text="🛡️", font=(FONT_FAMILY, 18), bg=COLOR_SOFT_WHITE, fg=COLOR_DEEP_ORANGE).pack(side="left", padx=(0, 8))
        tk.Label(brand_frame, text="AI Answer Reliability Tracker", font=get_font(14, "bold"),
                 bg=COLOR_SOFT_WHITE, fg=COLOR_DARK_TEXT).pack(side="left")
        tk.Label(brand_frame, text=" | Minimal Cream & Orange Edition", font=get_font(10),
                 bg=COLOR_SOFT_WHITE, fg=COLOR_MUTED_TEXT).pack(side="left")

        user_frame = tk.Frame(top, bg=COLOR_SOFT_WHITE)
        user_frame.pack(side="right")
        tk.Label(user_frame, text=f"Signed in: {self.user['username']} ({self.user['role']})",
                 font=get_font(9, "bold"), bg=COLOR_OFF_WHITE, fg=COLOR_DARK_TEXT, padx=10, pady=4).pack(side="left", padx=10)

        logout_btn = tk.Button(user_frame, text="Logout", command=self.login_screen, font=get_font(9),
                               bg=COLOR_WARM_CREAM, fg=COLOR_DEEP_ORANGE, relief="solid", bd=1, padx=10, pady=2, cursor="hand2")
        logout_btn.pack(side="left")

        # Tabs Notebook
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=16, pady=12)

        self.dashboard_tab = ttk.Frame(self.nb, padding=14)
        self.nb.add(self.dashboard_tab, text="  Dashboard  ")

        self.claim_tab = ttk.Frame(self.nb, padding=14)
        self.nb.add(self.claim_tab, text="  Claims Explorer  ")

        self.source_tab = ttk.Frame(self.nb, padding=14)
        self.nb.add(self.source_tab, text="  Sources Repository  ")

        self.history_tab = ttk.Frame(self.nb, padding=14)
        self.nb.add(self.history_tab, text="  Verification Audit History  ")

        self.build_dashboard()
        self.build_claims()
        self.build_sources()
        self.build_history()

        # Bottom Bar
        bottom = tk.Frame(self.root, bg=COLOR_SOFT_WHITE, bd=1, relief="solid", padx=16, pady=8)
        bottom.pack(fill="x")

        export_btn = tk.Button(bottom, text="📥 Export Claims CSV", command=self.export_csv, font=get_font(9, "bold"),
                               bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT, relief="solid", bd=1, padx=12, pady=4, cursor="hand2")
        export_btn.pack(side="left")

        refresh_btn = tk.Button(bottom, text="🔄 Refresh All", command=self.refresh_all, font=get_font(9, "bold"),
                                bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT, relief="solid", bd=1, padx=12, pady=4, cursor="hand2")
        refresh_btn.pack(side="left", padx=8)

        tk.Label(bottom, text="Normalized SQLite • Cascade Integrity", font=get_font(8),
                 bg=COLOR_SOFT_WHITE, fg=COLOR_MUTED_TEXT).pack(side="right")

    def build_dashboard(self):
        for w in self.dashboard_tab.winfo_children():
            w.destroy()

        with connect() as con:
            total = con.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
            counts = {r["status"]: r["n"] for r in con.execute("SELECT status, COUNT(*) n FROM claims GROUP BY status")}
            avg = con.execute("SELECT COALESCE(AVG(confidence), 0) FROM claims WHERE status='Verified'").fetchone()[0]
            sources_total = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            recent = con.execute("SELECT claim_id, claim_text, status, confidence FROM claims ORDER BY created_at DESC LIMIT 6").fetchall()

        # KPI Metric Cards
        cards_frame = tk.Frame(self.dashboard_tab, bg=COLOR_WARM_CREAM)
        cards_frame.pack(fill="x", pady=(0, 12))

        kpis = [
            ("TOTAL CLAIMS", total, COLOR_DEEP_ORANGE),
            ("VERIFIED", counts.get("Verified", 0), STATUS_COLORS["Verified"]),
            ("UNVERIFIED", counts.get("Unverified", 0), STATUS_COLORS["Unverified"]),
            ("DISPUTED", counts.get("Disputed", 0), STATUS_COLORS["Disputed"]),
            ("AVG. CONFIDENCE", f"{avg:.1f}%", COLOR_DARK_TEXT),
            ("SOURCES", sources_total, COLOR_DEEP_ORANGE)
        ]

        for title, value, accent_color in kpis:
            box = tk.Frame(cards_frame, bg=COLOR_SOFT_WHITE, bd=1, relief="solid", padx=14, pady=12)
            box.pack(side="left", fill="both", expand=True, padx=4)

            # Left accent strip
            strip = tk.Frame(box, bg=accent_color, width=4)
            strip.place(x=0, y=0, relheight=1)

            tk.Label(box, text=title, font=get_font(8, "bold"), bg=COLOR_SOFT_WHITE, fg=COLOR_MUTED_TEXT).pack(anchor="w")
            tk.Label(box, text=str(value), font=get_font(18, "bold"), bg=COLOR_SOFT_WHITE, fg=accent_color).pack(anchor="w", pady=(2, 0))

        # Status distribution canvas
        chart_frame = tk.LabelFrame(self.dashboard_tab, text=" Status Distribution Ratio ", font=get_font(10, "bold"),
                                    bg=COLOR_SOFT_WHITE, fg=COLOR_DARK_TEXT, bd=1, relief="solid", padx=12, pady=10)
        chart_frame.pack(fill="x", pady=(0, 12))

        canvas = tk.Canvas(chart_frame, height=54, bg=COLOR_OFF_WHITE, highlightthickness=0)
        canvas.pack(fill="x", pady=4)

        x = 0
        total_for_chart = max(total, 1)
        canvas_width = 860

        for status in ["Verified", "Unverified", "Disputed", "Rejected"]:
            n = counts.get(status, 0)
            if n > 0:
                width = max(10, int(canvas_width * n / total_for_chart))
                canvas.create_rectangle(x, 0, x + width, 54, fill=STATUS_COLORS[status], outline="")
                if width > 35:
                    canvas.create_text(x + width/2, 27, text=f"{status}\n({n})", fill=COLOR_SOFT_WHITE, font=get_font(8, "bold"))
                x += width

        # Recent Claims
        recent_label = tk.Label(self.dashboard_tab, text="Recently Evaluated Claims", font=get_font(11, "bold"),
                                bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT)
        recent_label.pack(anchor="w", pady=(4, 6))

        tree = self.make_tree(self.dashboard_tab, ("ID", "Claim Statement", "Status", "Confidence"),
                              ("claim_id", "claim_text", "status", "confidence"), height=6)
        tree.column("claim_id", width=60, anchor="center")
        tree.column("claim_text", width=550)
        tree.column("status", width=120, anchor="center")
        tree.column("confidence", width=100, anchor="center")

        for r in recent:
            tree.insert("", "end", values=(r["claim_id"], r["claim_text"], r["status"], f"{r['confidence']}%"))

    def make_tree(self, parent, headers, keys, height=12):
        wrap = tk.Frame(parent, bg=COLOR_SOFT_WHITE, bd=1, relief="solid")
        wrap.pack(fill="both", expand=True)

        tree = ttk.Treeview(wrap, columns=keys, show="headings", height=height)
        for h, k in zip(headers, keys):
            tree.heading(k, text=h)
            tree.column(k, width=140, anchor="w")

        y = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=y.set)
        tree.pack(side="left", fill="both", expand=True)
        y.pack(side="right", fill="y")
        return tree

    def build_claims(self):
        bar = tk.Frame(self.claim_tab, bg=COLOR_WARM_CREAM)
        bar.pack(fill="x", pady=(0, 10))

        tk.Label(bar, text="Search:", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        ent = tk.Entry(bar, textvariable=self.search_var, width=26, font=get_font(9), bg=COLOR_SOFT_WHITE, relief="solid", bd=1)
        ent.pack(side="left", padx=(0, 10), ipady=3)
        ent.bind("<KeyRelease>", lambda e: self.load_claims())

        tk.Label(bar, text="Status:", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(side="left", padx=(0, 4))
        self.filter_var = tk.StringVar(value="All")
        status_cb = ttk.Combobox(bar, textvariable=self.filter_var, values=["All", "Unverified", "Verified", "Disputed", "Rejected"],
                                 state="readonly", width=13)
        status_cb.pack(side="left", padx=(0, 10))
        status_cb.bind("<<ComboboxSelected>>", lambda e: self.load_claims())

        # Action Buttons on Right
        btn_add = tk.Button(bar, text="+ Add Claim", command=self.add_claim_dialog, font=get_font(9, "bold"),
                            bg=COLOR_DEEP_ORANGE, fg=COLOR_SOFT_WHITE, relief="flat", padx=10, pady=4, cursor="hand2")
        btn_add.pack(side="right", padx=(4, 0))

        btn_edit = tk.Button(bar, text="Edit", command=self.edit_claim, font=get_font(9),
                             bg=COLOR_SOFT_WHITE, fg=COLOR_DARK_TEXT, relief="solid", bd=1, padx=10, pady=4, cursor="hand2")
        btn_edit.pack(side="right", padx=4)

        btn_status = tk.Button(bar, text="Change Status", command=self.change_status, font=get_font(9),
                               bg=COLOR_SOFT_WHITE, fg=COLOR_DEEP_ORANGE, relief="solid", bd=1, padx=10, pady=4, cursor="hand2")
        btn_status.pack(side="right", padx=4)

        btn_del = tk.Button(bar, text="Delete", command=self.delete_claim, font=get_font(9),
                            bg=COLOR_SOFT_WHITE, fg=STATUS_COLORS["Disputed"], relief="solid", bd=1, padx=10, pady=4, cursor="hand2")
        btn_del.pack(side="right", padx=4)

        self.claim_tree = self.make_tree(
            self.claim_tab,
            ("ID", "Claim Statement", "Category", "Status", "Confidence", "Sources", "Created"),
            ("claim_id", "claim_text", "category", "status", "confidence", "source_count", "created_at"),
            14
        )
        self.claim_tree.column("claim_id", width=50, anchor="center")
        self.claim_tree.column("claim_text", width=380)
        self.claim_tree.column("category", width=120)
        self.claim_tree.column("status", width=100, anchor="center")
        self.claim_tree.column("confidence", width=80, anchor="center")
        self.claim_tree.column("source_count", width=70, anchor="center")
        self.claim_tree.column("created_at", width=140)

        self.claim_tree.bind("<Double-1>", lambda e: self.edit_claim())
        self.load_claims()

    def load_claims(self):
        if not hasattr(self, "claim_tree"):
            return
        self.claim_tree.delete(*self.claim_tree.get_children())
        q = self.search_var.get().strip()
        st = self.filter_var.get()
        sql = "SELECT * FROM v_claim_summary WHERE (claim_text LIKE ? OR category LIKE ?)"
        args = [f"%{q}%", f"%{q}%"]
        if st != "All":
            sql += " AND status=?"
            args.append(st)
        sql += " ORDER BY claim_id DESC"
        with connect() as con:
            rows = con.execute(sql, args).fetchall()
        for r in rows:
            self.claim_tree.insert("", "end", values=(
                r["claim_id"], r["claim_text"], r["category"], r["status"],
                f"{r['confidence']}%", r["source_count"], r["created_at"]
            ))

    def selected_claim(self):
        sel = self.claim_tree.selection()
        if not sel:
            messagebox.showwarning("Selection Required", "Please select a claim from the table first.")
            return None
        return int(self.claim_tree.item(sel[0], "values")[0])

    def add_claim_dialog(self, claim_id=None):
        editing = claim_id is not None
        row = None
        if editing:
            with connect() as con:
                row = con.execute("SELECT * FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
            if not row:
                return

        win = tk.Toplevel(self.root)
        win.title("Edit Claim" if editing else "Add New Claim")
        win.geometry("560x490")
        win.configure(bg=COLOR_WARM_CREAM)
        win.transient(self.root)
        win.grab_set()

        frm = tk.Frame(win, bg=COLOR_WARM_CREAM, padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="Claim Statement *", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        text = tk.Text(frm, height=4, wrap="word", font=get_font(9), bg=COLOR_SOFT_WHITE, bd=1, relief="solid")
        text.pack(fill="x", pady=(4, 10))

        tk.Label(frm, text="Domain / Category", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        cat = tk.StringVar(value=row["category"] if editing else "General")
        tk.Entry(frm, textvariable=cat, font=get_font(9), bg=COLOR_SOFT_WHITE, bd=1, relief="solid").pack(fill="x", pady=(4, 10), ipady=3)

        tk.Label(frm, text="Confidence Rating (0–100 %)", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        conf = tk.IntVar(value=row["confidence"] if editing else 60)
        ttk.Spinbox(frm, from_=0, to=100, textvariable=conf, width=10).pack(anchor="w", pady=(4, 10))

        tk.Label(frm, text="Evaluation Notes / Initial Evidence", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        notes = tk.Text(frm, height=4, wrap="word", font=get_font(9), bg=COLOR_SOFT_WHITE, bd=1, relief="solid")
        notes.pack(fill="both", expand=True, pady=(4, 12))

        if editing:
            text.insert("1.0", row["claim_text"])
            notes.insert("1.0", row["notes"] or "")

        def save():
            c_text = text.get("1.0", "end").strip()
            c_cat = cat.get().strip() or "General"
            try:
                c_val = int(conf.get())
            except ValueError:
                messagebox.showerror("Validation Error", "Confidence must be an integer between 0 and 100.")
                return
            if not c_text:
                messagebox.showerror("Validation Error", "Claim text cannot be empty.")
                return
            if not (0 <= c_val <= 100):
                messagebox.showerror("Validation Error", "Confidence must be between 0 and 100.")
                return

            with connect() as con:
                if editing:
                    con.execute(
                        "UPDATE claims SET claim_text=?, category=?, confidence=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE claim_id=?",
                        (c_text, c_cat, c_val, notes.get("1.0", "end").strip(), claim_id)
                    )
                else:
                    con.execute(
                        "INSERT INTO claims(claim_text, category, confidence, notes, created_by) VALUES(?,?,?,?,?)",
                        (c_text, c_cat, c_val, notes.get("1.0", "end").strip(), self.user["user_id"])
                    )
            win.destroy()
            self.refresh_all()

        btn_save = tk.Button(frm, text="Save Claim Statement", command=save, font=get_font(10, "bold"),
                             bg=COLOR_DEEP_ORANGE, fg=COLOR_SOFT_WHITE, relief="flat", padx=16, pady=8, cursor="hand2")
        btn_save.pack(pady=4)

    def edit_claim(self):
        cid = self.selected_claim()
        if cid:
            self.add_claim_dialog(cid)

    def delete_claim(self):
        cid = self.selected_claim()
        if cid and messagebox.askyesno("Confirm Permanent Deletion", f"Permanently delete claim #{cid} and all its linked citations and audit history?"):
            with connect() as con:
                con.execute("DELETE FROM claims WHERE claim_id=?", (cid,))
            self.refresh_all()

    def change_status(self):
        cid = self.selected_claim()
        if not cid:
            return

        win = tk.Toplevel(self.root)
        win.title(f"Update Status — Claim #{cid}")
        win.geometry("420x290")
        win.configure(bg=COLOR_WARM_CREAM)
        win.transient(self.root)
        win.grab_set()

        frm = tk.Frame(win, bg=COLOR_WARM_CREAM, padx=20, pady=16)
        frm.pack(fill="both", expand=True)

        status = tk.StringVar(value="Verified")
        tk.Label(frm, text="New Verification Status", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        ttk.Combobox(frm, textvariable=status, values=["Unverified", "Verified", "Disputed", "Rejected"],
                     state="readonly").pack(fill="x", pady=(4, 10))

        tk.Label(frm, text="Verification Rationale / Audit Comment *", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        comment = tk.Text(frm, height=5, font=get_font(9), bg=COLOR_SOFT_WHITE, bd=1, relief="solid")
        comment.pack(fill="both", expand=True, pady=(4, 12))

        def save():
            comm = comment.get("1.0", "end").strip()
            if not comm:
                messagebox.showerror("Required Field", "Please provide a brief verification comment for the audit trail.")
                return

            with connect() as con:
                old = con.execute("SELECT status FROM claims WHERE claim_id=?", (cid,)).fetchone()["status"]
                new = status.get()
                con.execute("UPDATE claims SET status=?, updated_at=CURRENT_TIMESTAMP WHERE claim_id=?", (new, cid))
                con.execute("INSERT INTO verification_history(claim_id,old_status,new_status,comment,changed_by) VALUES(?,?,?,?,?)",
                            (cid, old, new, comm, self.user["user_id"]))
            win.destroy()
            self.refresh_all()

        btn_save = tk.Button(frm, text="Record Verification Decision", command=save, font=get_font(9, "bold"),
                             bg=COLOR_DEEP_ORANGE, fg=COLOR_SOFT_WHITE, relief="flat", padx=14, pady=6, cursor="hand2")
        btn_save.pack()

    def build_sources(self):
        bar = tk.Frame(self.source_tab, bg=COLOR_WARM_CREAM)
        bar.pack(fill="x", pady=(0, 10))

        btn_add = tk.Button(bar, text="+ Add Source", command=self.add_source_dialog, font=get_font(9, "bold"),
                            bg=COLOR_DEEP_ORANGE, fg=COLOR_SOFT_WHITE, relief="flat", padx=10, pady=4, cursor="hand2")
        btn_add.pack(side="left")

        btn_link = tk.Button(bar, text="🔗 Link Source to Claim", command=self.link_source, font=get_font(9),
                             bg=COLOR_SOFT_WHITE, fg=COLOR_DARK_TEXT, relief="solid", bd=1, padx=10, pady=4, cursor="hand2")
        btn_link.pack(side="left", padx=8)

        btn_open = tk.Button(bar, text="↗ Open URL", command=self.open_source, font=get_font(9),
                             bg=COLOR_SOFT_WHITE, fg=COLOR_DEEP_ORANGE, relief="solid", bd=1, padx=10, pady=4, cursor="hand2")
        btn_open.pack(side="left")

        btn_del = tk.Button(bar, text="Delete Source", command=self.delete_source, font=get_font(9),
                            bg=COLOR_SOFT_WHITE, fg=STATUS_COLORS["Disputed"], relief="solid", bd=1, padx=10, pady=4, cursor="hand2")
        btn_del.pack(side="right")

        self.source_tree = self.make_tree(
            self.source_tab,
            ("ID", "Publication / Source Name", "URL", "Credibility", "Added Date"),
            ("source_id", "source_name", "source_url", "credibility", "added_at"),
            14
        )
        self.source_tree.column("source_id", width=50, anchor="center")
        self.source_tree.column("source_name", width=240)
        self.source_tree.column("source_url", width=340)
        self.source_tree.column("credibility", width=100, anchor="center")
        self.source_tree.column("added_at", width=140)

        self.load_sources()

    def load_sources(self):
        self.source_tree.delete(*self.source_tree.get_children())
        with connect() as con:
            rows = con.execute("SELECT * FROM sources ORDER BY source_id DESC").fetchall()
        for r in rows:
            self.source_tree.insert("", "end", values=(
                r["source_id"], r["source_name"], r["source_url"], f"{r['credibility']} / 5 ⭐", r["added_at"]
            ))

    def selected_source(self):
        sel = self.source_tree.selection()
        if not sel:
            messagebox.showwarning("Selection Required", "Please select a source from the table first.")
            return None
        return int(self.source_tree.item(sel[0], "values")[0])

    def add_source_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Add New Verification Source")
        win.geometry("480x420")
        win.configure(bg=COLOR_WARM_CREAM)
        win.transient(self.root)
        win.grab_set()

        f = tk.Frame(win, bg=COLOR_WARM_CREAM, padx=20, pady=16)
        f.pack(fill="both", expand=True)

        name = tk.StringVar()
        url = tk.StringVar()
        cred = tk.IntVar(value=4)

        tk.Label(f, text="Source / Publication Name *", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        tk.Entry(f, textvariable=name, font=get_font(9), bg=COLOR_SOFT_WHITE, bd=1, relief="solid").pack(fill="x", pady=(4, 10), ipady=3)

        tk.Label(f, text="Canonical URL *", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        tk.Entry(f, textvariable=url, font=get_font(9), bg=COLOR_SOFT_WHITE, bd=1, relief="solid").pack(fill="x", pady=(4, 10), ipady=3)

        tk.Label(f, text="Credibility Score (1 to 5)", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        ttk.Spinbox(f, from_=1, to=5, textvariable=cred, width=10).pack(anchor="w", pady=(4, 10))

        tk.Label(f, text="Evidence / Methodology Excerpt", font=get_font(9, "bold"), bg=COLOR_WARM_CREAM, fg=COLOR_DARK_TEXT).pack(anchor="w")
        evidence = tk.Text(f, height=4, font=get_font(9), bg=COLOR_SOFT_WHITE, bd=1, relief="solid")
        evidence.pack(fill="both", expand=True, pady=(4, 12))

        def save():
            n = name.get().strip()
            u = url.get().strip()
            if not n or not u:
                messagebox.showerror("Validation Error", "Source Name and URL are both required.")
                return
            if not u.lower().startswith(("http://", "https://")):
                messagebox.showerror("Validation Error", "URL must start with http:// or https://")
                return

            with connect() as con:
                con.execute("INSERT INTO sources(source_name, source_url, credibility, evidence) VALUES(?,?,?,?)",
                            (n, u, cred.get(), evidence.get("1.0", "end").strip()))
            win.destroy()
            self.load_sources()

        btn_save = tk.Button(f, text="Save Source to Catalog", command=save, font=get_font(10, "bold"),
                             bg=COLOR_DEEP_ORANGE, fg=COLOR_SOFT_WHITE, relief="flat", padx=16, pady=8, cursor="hand2")
        btn_save.pack()

    def link_source(self):
        cid = self.selected_claim()
        sid = self.selected_source()
        if not cid or not sid:
            return
        try:
            with connect() as con:
                con.execute("INSERT INTO claim_sources(claim_id, source_id) VALUES(?,?)", (cid, sid))
            messagebox.showinfo("Citation Linked", f"Source #{sid} successfully linked to Claim #{cid}.")
            self.refresh_all()
        except sqlite3.IntegrityError:
            messagebox.showinfo("Already Linked", "This source is already linked to that claim.")

    def open_source(self):
        sid = self.selected_source()
        if sid:
            with connect() as con:
                url = con.execute("SELECT source_url FROM sources WHERE source_id=?", (sid,)).fetchone()["source_url"]
            webbrowser.open(url)

    def delete_source(self):
        sid = self.selected_source()
        if sid and messagebox.askyesno("Confirm Deletion", f"Permanently delete source #{sid} and all associated links?"):
            with connect() as con:
                con.execute("DELETE FROM sources WHERE source_id=?", (sid,))
            self.load_sources()
            self.load_claims()

    def build_history(self):
        bar = tk.Frame(self.history_tab, bg=COLOR_WARM_CREAM)
        bar.pack(fill="x", pady=(0, 10))

        btn_refresh = tk.Button(bar, text="🔄 Refresh Audit Log", command=self.load_history, font=get_font(9),
                                bg=COLOR_SOFT_WHITE, fg=COLOR_DARK_TEXT, relief="solid", bd=1, padx=10, pady=4, cursor="hand2")
        btn_refresh.pack(side="left")

        self.history_tree = self.make_tree(
            self.history_tab,
            ("History ID", "Claim ID", "Previous Status", "New Status", "Verification Remark", "Audited At"),
            ("history_id", "claim_id", "old_status", "new_status", "comment", "changed_at"),
            16
        )
        self.history_tree.column("history_id", width=70, anchor="center")
        self.history_tree.column("claim_id", width=70, anchor="center")
        self.history_tree.column("old_status", width=110, anchor="center")
        self.history_tree.column("new_status", width=110, anchor="center")
        self.history_tree.column("comment", width=340)
        self.history_tree.column("changed_at", width=140)

        self.load_history()

    def load_history(self):
        self.history_tree.delete(*self.history_tree.get_children())
        with connect() as con:
            rows = con.execute("SELECT * FROM verification_history ORDER BY history_id DESC").fetchall()
        for r in rows:
            self.history_tree.insert("", "end", values=(
                r["history_id"], r["claim_id"], r["old_status"] or "Initial", r["new_status"],
                r["comment"], r["changed_at"]
            ))

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="AI_Answer_Reliability_Report.csv"
        )
        if not path:
            return
        with connect() as con:
            rows = con.execute("SELECT * FROM v_claim_summary ORDER BY claim_id ASC").fetchall()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Claim ID", "Claim Statement", "Category", "Verification Status", "Confidence (%)", "Source Count", "Created Date", "Last Updated"])
            for r in rows:
                writer.writerow([
                    r["claim_id"], r["claim_text"], r["category"], r["status"],
                    r["confidence"], r["source_count"], r["created_at"], r["updated_at"]
                ])
        messagebox.showinfo("Export Successful", f"Reliability report successfully exported to:\n{path}")

    def refresh_all(self):
        self.build_dashboard()
        self.load_claims()
        self.load_sources()
        self.load_history()

if __name__ == "__main__":
    initialize_db()
    root = tk.Tk()
    app = TrackerApp(root)
    root.mainloop()
