# AI Answer Reliability Tracker — Advanced Edition

> **Meta Description:**  
> A rigorous evidence-based platform and relational evaluation framework to audit, track, and score AI-generated assertions, confidence metrics, and source credibility verifications with SQLite persistence, Minimal Cream & Orange styling, Figtree typography, and fully responsive layouts.

---

## 🎨 Theme & Visual Design System

The application is built around the **Minimal Cream & Orange Theme** with a strict 4px/8px design grid, high contrast, and accessible typography.

| Color Name | Hex Code | Purpose / UI Application |
|---|---|---|
| **Soft White** | `#FFFDF8` | Card backgrounds, modal panels, high-contrast surfaces |
| **Warm Cream** | `#F7F2E8` | Primary background, app surface, secondary table hover states |
| **Off White** | `#F3EBDD` | Borders, subtle dividers, inactive tabs, chart track backdrops |
| **Soft Orange** | `#E9A15B` | Secondary accents, star ratings, subtle highlight badges |
| **Deep Orange** | `#D97732` | Primary brand accent, primary CTA buttons, active tab indicators |
| **Dark Text** | `#3D342C` | High-contrast body typography, headers, primary data text |

### Typography
- **Primary Font:** **Figtree** (Google Fonts `https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700;800&display=swap`)
- **Scale:**
  - Display / H1: `1.85rem` (700/800 bold), letter spacing `-0.025em`
  - H2 / Section Titles: `1.4rem` (700 bold), letter spacing `-0.015em`
  - H3 / Card Titles: `1.12rem` (600/700 semi-bold)
  - Body Text: `0.95rem` (400 regular), line height `1.6`
  - Microcopy / Badges: `0.76rem` - `0.82rem` (600/700 bold)

### Responsive Media Queries (`media querry full done`)
- **Large Screens (> 1200px):** Expansive 2-column analytics grid, side-by-side inspector views.
- **Laptops & Desktops (1025px - 1200px):** Dynamic dashboard realignment and fluid table column sizing.
- **Tablets (641px - 1024px):** 2-column KPI card grid, flexible wrap for filter toolbars, adaptive modal dialogs.
- **Mobile Devices (<= 640px):** Single-column stacked layouts, horizontal scrollable tables, full-width touch targets (minimum 44px height), responsive full-sheet modals.
- **Print Mode (`@media print`):** Clean, ink-efficient audit reports without navigation chrome.

---

## 🚀 Quick Start Guide

### Option 1: Web Application (Recommended)
No external pip dependencies required (runs on Python's built-in `http.server`, `sqlite3`, `hashlib`, `json`, and `csv`).

1. Double-click **`run.bat`** (or open PowerShell / CMD in the project folder and run):
   ```cmd
   python app.py
   # or
   py -3.10 app.py
   ```
2. Open your web browser at:
   **`http://127.0.0.1:8000/`**
3. Login Credentials:
   - **Username:** `admin` &bull; **Password:** `admin123`
   - *Alternate Analyst Account:* `analyst` &bull; **Password:** `analyst123`

### Option 2: Tkinter Desktop Application
To run the redesigned desktop GUI adhering to the Minimal Cream & Orange palette:
```cmd
python AI_Answer_Reliability_Tracker/main.py
# or
py -3.10 AI_Answer_Reliability_Tracker/main.py
```

---

## 🏗️ Phase-by-Phase Architecture (Step-by-Step)

### Phase 1: Database Foundation & Relational Schema
- SQLite engine with foreign key enforcement (`PRAGMA foreign_keys = ON;`).
- Normalized 3NF tables: `users`, `claims`, `sources`, `claim_sources` (composite primary key), and `verification_history`.
- Automated status audit trigger (`trg_claim_update`) and aggregate summary view (`v_claim_summary`).

### Phase 2: Design Tokens & Typography Integration
- Implemented Google Font **Figtree** with preconnect loading.
- Applied CSS custom variables for `#FFFDF8`, `#F7F2E8`, `#F3EBDD`, `#E9A15B`, `#D97732`, and `#3D342C`.
- Strict 8pt grid alignment for buttons, cards, modals, and tables.

### Phase 3: Analytics Dashboard
- Metric KPI cards: Total Claims, Verified count & %, Unverified, Disputed, Avg. Verified Confidence, Linked Sources.
- Dynamic SVG status distribution chart with color-coded segments and hover ratio indicators.
- Category distribution summary and recent claims table.

### Phase 4: Claims Explorer & Filtering
- Live search with debounced querying over claim text, categories, and evaluation notes.
- Multi-criteria filtering by Status and Category.
- Full CRUD operations with modal dialogs and inputs validation.

### Phase 5: Sources & Many-to-Many Evidence Mapping
- Sources catalog with credibility scoring (1 to 5 stars) and canonical URL validation.
- Interactive Claim Inspector allowing users to link multiple sources to one claim, add relation notes, or unlink citations.

### Phase 6: Verification Workflow & Audit History
- Verification status transitions (`Unverified` &rarr; `Verified` / `Disputed` / `Rejected`).
- Immutable chronological verification history ledger tracking auditor identity, old and new status, and remarks.

### Phase 7: Reporting & Export
- Real-time UTF-8 CSV report generation (`AI_Answer_Reliability_Report.csv`) containing complete claim metadata and credibility averages.
