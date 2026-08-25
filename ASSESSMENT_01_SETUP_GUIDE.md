# SETUP GUIDE: BFS Traversal + 5-Check Filter Pipeline
## Rules Engine: Environment Setup + Seed Data + Schema

---

## ENVIRONMENT SETUP

### What You Need Installed

| Tool | Why |
|------|-----|
| Node.js (v18+) OR Python (3.11+) | Runtime — choose one |
| Git | Version control + submission |
| VS Code (recommended) | Code editor |
| Supabase account (free) | PostgreSQL database with RLS |
| No LLM API key needed | This pipeline uses ZERO LLM |

### Mac Setup (Python path)

```bash
# Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python + Node.js
brew install python@3.11 node

# Verify
python3 --version   # 3.11+
node --version      # v18+
git --version       # 2.x+

# Create project
mkdir brahmo-rules-engine
cd brahmo-rules-engine && git init

# Python backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn supabase python-dotenv

# React frontend
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir --no-import-alias
cd frontend && npm install @supabase/supabase-js

# Create .env
cd ..
echo "SUPABASE_URL=your_url" > .env
echo "SUPABASE_KEY=your_key" >> .env

# Start backend
uvicorn main:app --reload --port 8000

# Start frontend (separate terminal)
cd frontend && npm run dev   # → http://localhost:3000
```

### Mac Setup (Node.js path)

```bash
# Install Node.js
brew install node

# Create project
mkdir brahmo-rules-engine
cd brahmo-rules-engine && git init

# Initialize
npx create-next-app@latest . --typescript --tailwind --app --src-dir --no-import-alias

# Install dependencies
npm install @supabase/supabase-js

# Create .env.local
echo "NEXT_PUBLIC_SUPABASE_URL=your_url" > .env.local
echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=your_key" >> .env.local

# Start
npm run dev   # → http://localhost:3000
```

### Windows Setup

```powershell
# Install Python from https://python.org (check "Add to PATH")
# Install Node.js from https://nodejs.org (LTS)
# Install Git from https://git-scm.com

# Verify in PowerShell
python --version    # 3.11+
node --version      # v18+
git --version       # 2.x+

# Create project
mkdir brahmo-rules-engine
cd brahmo-rules-engine
git init

# Option A: Python backend + React frontend (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install fastapi uvicorn supabase python-dotenv

npx create-next-app@latest frontend --typescript --tailwind --app --src-dir --no-import-alias
cd frontend
npm install @supabase/supabase-js

# Option B: Full Node.js
npx create-next-app@latest . --typescript --tailwind --app --src-dir --no-import-alias
npm install @supabase/supabase-js
```

### Supabase Setup

```
1. Go to supabase.com → Sign up (free)
2. Create project: "brahmo-rules-engine"
3. Wait ~2 minutes for provisioning
4. Settings → API → Copy Project URL + anon key → paste into .env
5. SQL Editor → Run the schema SQL below (creates all tables)
6. SQL Editor → Run the seed data SQL below (loads 50 nodes + 7 users)
7. Verify: SELECT COUNT(*) FROM knowledge_nodes → 50
8. Verify: SELECT COUNT(*) FROM users → 7
```

---

## AI STARTER PROMPT

Copy this into your preferred AI coding tool to scaffold the project:

```
I'm building a Rules Engine pipeline for BRAHMO — a knowledge graph
filtering system. It traverses a DAG of knowledge nodes and applies
5 sequential checks to produce a candidate set for a specific user.
ZERO LLM is used anywhere in this pipeline.

TECH STACK: FastAPI (Python) OR Next.js API routes + React + Supabase + Tailwind CSS

CORE MODULES:

1. Permission Compiler:
   At session start, compile user's permissions into O(1) lookup.
   Input: user record (role, ceiling_level, department, org_id, compliance_clearance[])
   Output: dictionary {level_number: {can_read: bool, can_write: bool}}
   For VIEWER: can_read levels >= ceiling, can_write nothing
   For EDITOR: can_read levels >= ceiling, can_write levels >= write_ceiling
   For HOD: can_read all levels, can_write levels >= their ceiling
   For ADMIN: can_read and can_write all levels
   CRITICAL: Compile ONCE per session. Use for all 500+ permission checks.

2. Entry Point Resolver:
   Map user's department to their DAG leaf node (entry point).
   Input: user.department → look up hierarchy_levels WHERE dept matches
   Output: the node_id that is the user's starting position for BFS
   Nurse Priya (Ortho Ward) → Level 10, Ortho Ward node
   Dr. Vikram (Ortho Dept) → Level 4 is his ceiling but entry is at HOD level

3. BFS Traversal (upward through DAG):
   Start at entry point, walk UP the DAG via parent_ids edges.
   Use a queue (FIFO) and a visited set (prevent re-processing).
   Multi-parent: if a node has parent_ids = [A, B], it's reachable
   from both paths — process it ONCE (visited set).
   Output: Set of all reachable node IDs + distance from entry.
   DO NOT fetch node content yet — just IDs and distances.

4. Zone 2 Injector:
   After BFS, inject all nodes WHERE zone = 'GLOBAL' (Zone 2).
   These are hospital-wide safety constraints that apply regardless
   of the user's traversal path.
   Inject BEFORE the 5 checks — Zone 2 nodes still need filtering.
   Some Zone 2 nodes may be MNPI, expired, or above ceiling.

5. Five-Check Sequential Filter:
   Each check takes the previous check's output as input.
   
   Check 1 — ISOLATION: WHERE org_id = user.org_id
     Ensures multi-tenant isolation. In single-org demo, all pass.
   
   Check 2 — COMPLIANCE: WHERE NOT (compliance_tags && user.blocked_tags)
     Array overlap check. MNPI-tagged nodes excluded for non-cleared users.
     ADMIN and AUDITOR roles may have compliance clearance.
   
   Check 3 — PERMISSION: WHERE hierarchy_level >= user.ceiling_level
     Uses the compiled permission dictionary. O(1) per node.
     Nurse at L10 can't see L4 HOD decisions.
   
   Check 4 — TEMPORAL: WHERE status != 'SUPERSEDED'
     AND (valid_until IS NULL OR valid_until > NOW())
     Excludes expired and replaced nodes.
   
   Check 5 — DERIVABILITY: WHERE derivability_score < 0.7
     Excludes nodes the AI can answer from general knowledge.
     Threshold 0.7 is configurable per org.
   
   CRITICAL: Sequential. Output of check N = input to check N+1.
   CRITICAL: These should ideally run as SQL WHERE clauses, not
   fetch-all-then-filter in Python. GAP 5: permission before retrieval.

6. Candidate Set Assembler:
   Take the surviving nodes and annotate each with:
   - type (CONSTRAINT/DECISION/ANTI_PATTERN/FACT)
   - importance (0.0-1.0)
   - distance_from_entry (from BFS — 0 = entry point, 1 = parent, etc.)
   - zone (ADDRESSED/GLOBAL/FLOATING)
   - compression_hint: distance 0-1 → FULL, distance 2 → COMPRESSED,
     distance 3+ → CONSTRAINT_ONLY
   Output: JSON array of annotated nodes = the candidate set.

7. Frontend:
   - User selector dropdown (7 users pre-loaded)
   - [Run Pipeline] button
   - Filter funnel visualization: bar chart showing count at each stage
   - DAG tree visualization: show reachable vs unreachable nodes
   - Candidate set table: node details with type, importance, distance
   - Comparison view: side-by-side results for 2-3 users
   - Pipeline timing display (total ms, per-check breakdown)

DATABASE (Supabase):
   See schema SQL below — tables already designed for you.
   
Start with Permission Compiler + BFS, then add checks 1-5 one at a time.
Test after EACH check by verifying the count drops correctly.
```

---

## PROJECT STRUCTURE

```
brahmo-rules-engine/
├── README.md
├── .env                          ← DO NOT commit
├── .env.example                  ← Commit with placeholder values
├── docs/
│   └── architecture.md           ← Your pipeline design + decisions
│
├── backend/                      ← Python (FastAPI) OR Node.js API routes
│   ├── main.py                   ← FastAPI app entry point
│   ├── pipeline/
│   │   ├── permission_compiler.py
│   │   ├── entry_point_resolver.py
│   │   ├── bfs_traversal.py
│   │   ├── zone2_injector.py
│   │   ├── five_check_filter.py
│   │   └── candidate_assembler.py
│   ├── models/
│   │   ├── user.py
│   │   ├── node.py
│   │   └── candidate_set.py
│   └── tests/
│       ├── test_bfs.py
│       ├── test_five_checks.py
│       └── test_pipeline.py
│
├── frontend/                     ← Next.js + React + Tailwind
│   ├── src/
│   │   ├── app/
│   │   │   └── page.tsx          ← Main pipeline demo page
│   │   ├── components/
│   │   │   ├── UserSelector.tsx
│   │   │   ├── FilterFunnel.tsx  ← Bar chart showing count at each stage
│   │   │   ├── DAGViewer.tsx     ← Tree visualization
│   │   │   ├── CandidateTable.tsx
│   │   │   └── ComparisonView.tsx
│   │   └── lib/
│   │       ├── supabase.ts
│   │       └── types.ts
│   └── package.json
│
└── supabase/
    ├── schema.sql                ← Table definitions
    └── seed.sql                  ← 50 nodes + 7 users + edges
```

---

## TIME MANAGEMENT (8 hours)

| Phase | Hours | Focus |
|-------|:-----:|-------|
| Setup + read assessment thoroughly | 0.5 | Environment, Supabase, understand requirements |
| Schema + seed data loading | 0.5 | Run SQL, verify data, understand DAG shape |
| Permission compiler + entry point resolver | 1.0 | O(1) lookup structure, department mapping |
| BFS traversal with visited set | 1.5 | MOST CRITICAL — correct upward traversal, multi-parent handling |
| Five-check sequential filter | 1.5 | One check at a time, verify count drops at each stage |
| Zone 2 injection | 0.5 | Insert at correct pipeline position |
| Frontend (funnel + DAG + comparison) | 1.5 | Visualize the pipeline, user switching, timing display |
| Test all scenarios + innovation | 0.5 | Verify per-user differences, add your improvements |

---

## DATABASE SCHEMA

Run this in Supabase SQL Editor:

```sql
-- ============================================================
-- BRAHMO Rules Engine — Database Schema
-- ============================================================

-- Organizations
CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    segment TEXT NOT NULL CHECK (segment IN ('hospital', 'law_firm', 'software')),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Hierarchy Levels (15-level DAG structure)
CREATE TABLE hierarchy_levels (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id),
    level_number INTEGER NOT NULL CHECK (level_number BETWEEN 1 AND 15),
    level_name TEXT NOT NULL,
    department TEXT,           -- NULL for cross-department levels
    parent_ids TEXT[] DEFAULT '{}',  -- DAG: multiple parents allowed
    zone INTEGER NOT NULL DEFAULT 1 CHECK (zone IN (1, 2, 3)),
    -- Zone 1 = Addressed (dept-specific), Zone 2 = Global, Zone 3 = Floating
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, level_number, department)
);

-- Knowledge Nodes
CREATE TABLE knowledge_nodes (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id),
    hierarchy_level_id TEXT NOT NULL REFERENCES hierarchy_levels(id),
    type TEXT NOT NULL CHECK (type IN ('CONSTRAINT', 'DECISION', 'ANTI_PATTERN', 'FACT')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    importance DECIMAL(3,2) NOT NULL CHECK (importance BETWEEN 0.0 AND 1.0),
    zone INTEGER NOT NULL DEFAULT 1 CHECK (zone IN (1, 2, 3)),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN (
        'ACTIVE', 'REVIEW_REQUIRED', 'SUPERSEDED', 'EXPIRED', 'LEGAL_HOLD'
    )),
    derivability_score DECIMAL(3,2) NOT NULL DEFAULT 0.0 CHECK (derivability_score BETWEEN 0.0 AND 1.0),
    compliance_tags TEXT[] DEFAULT '{}',  -- e.g., {'MNPI', 'PHI', 'CONFIDENTIAL'}
    valid_until TIMESTAMPTZ,             -- NULL = no expiry
    superseded_by TEXT REFERENCES knowledge_nodes(id),
    department TEXT,                      -- which department this node belongs to
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Edges (typed relationships between nodes)
CREATE TABLE edges (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    source_id TEXT NOT NULL REFERENCES knowledge_nodes(id),
    target_id TEXT NOT NULL REFERENCES knowledge_nodes(id),
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'SUPPORTS', 'CONTRADICTS', 'SUPERSEDES', 'DERIVED_FROM', 'REQUIRES'
    )),
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'HOD', 'EDITOR', 'VIEWER', 'QUALITY', 'AUDITOR')),
    department TEXT NOT NULL,
    ceiling_level INTEGER NOT NULL CHECK (ceiling_level BETWEEN 1 AND 15),
    write_ceiling INTEGER,  -- NULL for VIEWER (no write)
    compliance_clearance TEXT[] DEFAULT '{}',  -- e.g., {'MNPI'} for auditors
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log (append-only)
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    node_id TEXT REFERENCES knowledge_nodes(id),
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    actor_id TEXT REFERENCES users(id),
    org_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_nodes_org ON knowledge_nodes(org_id);
CREATE INDEX idx_nodes_zone ON knowledge_nodes(zone);
CREATE INDEX idx_nodes_status ON knowledge_nodes(status);
CREATE INDEX idx_nodes_dept ON knowledge_nodes(department);
CREATE INDEX idx_nodes_hierarchy ON knowledge_nodes(hierarchy_level_id);
CREATE INDEX idx_nodes_compliance ON knowledge_nodes USING GIN(compliance_tags);
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_hierarchy_org ON hierarchy_levels(org_id);
CREATE INDEX idx_hierarchy_parent ON hierarchy_levels USING GIN(parent_ids);
```

---

## SEED DATA — ORGANIZATION + HIERARCHY

```sql
-- ============================================================
-- Organization
-- ============================================================
INSERT INTO organizations (id, name, segment, config) VALUES
('supra', 'Supra Multi-Specialty Hospital', 'hospital', 
 '{"derivability_threshold": 0.7, "max_candidate_set": 50, "token_budget": 4000}');

-- ============================================================
-- 15-Level Hierarchy (DAG structure)
-- ============================================================
INSERT INTO hierarchy_levels (id, org_id, level_number, level_name, department, parent_ids, zone) VALUES
-- Level 1: Hospital Root
('HL-01', 'supra', 1, 'Hospital', NULL, '{}', 1),

-- Level 3: Divisions
('HL-03-CLIN', 'supra', 3, 'Clinical Division', NULL, '{"HL-01"}', 1),
('HL-03-ADMIN', 'supra', 3, 'Administrative Division', NULL, '{"HL-01"}', 1),

-- Level 5: Departments
('HL-05-ORTHO', 'supra', 5, 'Orthopaedics Department', 'ortho', '{"HL-03-CLIN"}', 1),
('HL-05-MED', 'supra', 5, 'General Medicine Department', 'medicine', '{"HL-03-CLIN"}', 1),
('HL-05-CARDIO', 'supra', 5, 'Cardiology Department', 'cardiology', '{"HL-03-CLIN"}', 1),
('HL-05-PAEDS', 'supra', 5, 'Paediatrics Department', 'paediatrics', '{"HL-03-CLIN"}', 1),
('HL-05-SURG', 'supra', 5, 'Surgery Department', 'surgery', '{"HL-03-CLIN"}', 1),
('HL-05-ICU', 'supra', 5, 'ICU Department', 'icu', '{"HL-03-CLIN"}', 1),

-- Level 8: Sub-departments / Specialties
('HL-08-ORTHO-GEN', 'supra', 8, 'Ortho General', 'ortho', '{"HL-05-ORTHO"}', 1),
('HL-08-ORTHO-TKR', 'supra', 8, 'Ortho TKR Unit', 'ortho', '{"HL-05-ORTHO"}', 1),
('HL-08-MED-GEN', 'supra', 8, 'Medicine General', 'medicine', '{"HL-05-MED"}', 1),
('HL-08-CARDIO-CCU', 'supra', 8, 'Cardiac Care Unit', 'cardiology', '{"HL-05-CARDIO"}', 1),

-- Level 10: Wards
('HL-10-ORTHO-W', 'supra', 10, 'Ortho Ward', 'ortho', '{"HL-08-ORTHO-GEN"}', 1),
('HL-10-MED-W', 'supra', 10, 'Medicine Ward', 'medicine', '{"HL-08-MED-GEN"}', 1),
('HL-10-PAEDS-W', 'supra', 10, 'Paediatrics Ward', 'paediatrics', '{"HL-05-PAEDS"}', 1),

-- Level 12: Patient-level (examples)
('HL-12-RAJAN', 'supra', 12, 'Patient: Rajan', 'ortho', '{"HL-10-ORTHO-W"}', 1),
('HL-12-PADMA', 'supra', 12, 'Patient: Padma', 'medicine', '{"HL-10-MED-W"}', 1),

-- Multi-parent example: Post-TKR Protocol belongs to BOTH Ortho and Surgery
('HL-08-POST-TKR', 'supra', 8, 'Post-TKR Protocol Area', 'ortho', '{"HL-05-ORTHO", "HL-05-SURG"}', 1),

-- Zone 2: Global (hospital-wide, bypass BFS but go through 5 checks)
('HL-GLOBAL', 'supra', 3, 'Global Constraints', NULL, '{"HL-01"}', 2);
```

---

## SEED DATA — 7 USERS

```sql
INSERT INTO users (id, org_id, name, role, department, ceiling_level, write_ceiling, compliance_clearance) VALUES
('U-PRIYA',  'supra', 'Nurse Priya',       'VIEWER',  'ortho',     10, NULL, '{}'),
('U-VIKRAM', 'supra', 'Dr. Vikram (HOD)',   'HOD',     'ortho',      4, 4,    '{}'),
('U-ANANYA', 'supra', 'Dr. Ananya',         'EDITOR',  'medicine',   8, 8,    '{}'),
('U-SHARMA', 'supra', 'Dr. Sharma (HOD)',   'HOD',     'medicine',   4, 4,    '{}'),
('U-RAVI',   'supra', 'Pharmacist Ravi',    'VIEWER',  'pharmacy',  12, NULL, '{}'),
('U-SUNITA', 'supra', 'Dr. Sunita (QA)',    'QUALITY', 'quality',    6, 8,    '{"MNPI"}'),
('U-SURESH', 'supra', 'Admin Suresh',       'ADMIN',   'admin',      1, 1,    '{"MNPI", "PHI", "CONFIDENTIAL"}');
```

---

## SEED DATA — 50 KNOWLEDGE NODES

```sql
-- ============================================================
-- ZONE 2: GLOBAL NODES (10 nodes — injected for ALL users)
-- These bypass BFS but go through all 5 checks
-- ============================================================

INSERT INTO knowledge_nodes (id, org_id, hierarchy_level_id, type, title, content, importance, zone, status, derivability_score, compliance_tags, department) VALUES

('N-G01', 'supra', 'HL-GLOBAL', 'CONSTRAINT', 'Warfarin-NSAID Interaction',
 'CRITICAL: Never prescribe NSAIDs (ibuprofen, aspirin, diclofenac) to patients on Warfarin. Risk of life-threatening GI bleed. Alternative: Paracetamol for pain, PPI cover if anti-inflammatory needed. Supra policy: automatic pharmacy flag on co-prescription.',
 0.98, 2, 'ACTIVE', 0.15, '{}', NULL),

('N-G02', 'supra', 'HL-GLOBAL', 'CONSTRAINT', 'Penicillin Allergy Cross-Reactivity',
 'Patients with documented penicillin allergy: 10% cross-reactivity with 1st-gen cephalosporins, <2% with 3rd-gen. Supra protocol: use azithromycin as first-line alternative. Always check allergy band before ANY antibiotic.',
 0.95, 2, 'ACTIVE', 0.20, '{}', NULL),

('N-G03', 'supra', 'HL-GLOBAL', 'CONSTRAINT', 'Blood Transfusion Two-Person Verification',
 'ALL blood transfusions require two-person verification of patient identity, blood type, and unit number. Single-person verification = protocol violation. Supra incident 2024: near-miss due to single verification.',
 0.97, 2, 'ACTIVE', 0.10, '{}', NULL),

('N-G04', 'supra', 'HL-GLOBAL', 'CONSTRAINT', 'Hand Hygiene 5-Moment Compliance',
 'WHO 5-moment hand hygiene compliance is mandatory. Supra target: 95%. Current: 88%. Alcohol-based handrub at every bed. Non-compliance is a reportable incident.',
 0.90, 2, 'ACTIVE', 0.75, '{}', NULL),

('N-G05', 'supra', 'HL-GLOBAL', 'ANTI_PATTERN', 'Verbal Orders Without Documentation',
 'NEVER accept verbal orders for medication changes without written/electronic confirmation within 1 hour. Supra incident 2023: wrong dose administered due to verbal order mishearing. Exception: cardiac arrest situations only.',
 0.92, 2, 'ACTIVE', 0.12, '{}', NULL),

('N-G06', 'supra', 'HL-GLOBAL', 'CONSTRAINT', 'Patient Identification Two-Identifier Rule',
 'Verify patient identity with TWO identifiers (name + DOB, or name + hospital ID) before any procedure, medication, or blood draw. Wristband check mandatory.',
 0.93, 2, 'ACTIVE', 0.80, '{}', NULL),

('N-G07', 'supra', 'HL-GLOBAL', 'FACT', 'Supra Hospital Emergency Codes',
 'Code Blue: cardiac arrest. Code Red: fire. Code Pink: infant abduction. Code Grey: combative patient. Code Orange: mass casualty. All staff must know codes for their floor.',
 0.70, 2, 'ACTIVE', 0.18, '{}', NULL),

('N-G08', 'supra', 'HL-GLOBAL', 'CONSTRAINT', 'Antibiotic Stewardship 72-Hour Review',
 'All empiric antibiotics must be reviewed at 72 hours. De-escalate based on culture results. Supra policy: pharmacy auto-alerts at 72 hours if no review documented.',
 0.88, 2, 'ACTIVE', 0.25, '{}', NULL),

('N-G09', 'supra', 'HL-GLOBAL', 'CONSTRAINT', 'Fall Risk Assessment on Admission',
 'Every patient assessed for fall risk using Morse Fall Scale on admission and every shift change. Score >= 45: high risk, bed alarm required.',
 0.85, 2, 'ACTIVE', 0.55, '{}', NULL),

('N-G10', 'supra', 'HL-GLOBAL', 'FACT', 'Supra Formulary Preferred Brands',
 'Supra formulary preferred brands: Paracetamol (Calpol/Dolo), Omeprazole (Omez), Amoxicillin (Mox), Metformin (Glycomet). Use formulary brand unless clinical reason documented.',
 0.65, 2, 'ACTIVE', 0.30, '{}', NULL),

-- ============================================================
-- ORTHOPAEDICS NODES (15 nodes — Priya's department)
-- ============================================================

('N-O01', 'supra', 'HL-05-ORTHO', 'CONSTRAINT', 'Post-Op Vitals Monitoring',
 'Post-operative vitals must be recorded every 15 minutes for first 4 hours, then hourly for 24 hours. Supra ortho-specific: include neurovascular check (pulse, sensation, movement) for all limb surgeries.',
 0.94, 1, 'ACTIVE', 0.35, '{}', 'ortho'),

('N-O02', 'supra', 'HL-08-ORTHO-TKR', 'DECISION', 'Paracetamol First-Line Post-TKR',
 'Supra Ortho uses Paracetamol 650mg QDS as first-line post-TKR pain management. Escalation: Tramadol 50mg if VAS > 6. AVOID NSAIDs due to bleeding risk at surgical site. Decision by Dr. Vikram, Jan 2025.',
 0.88, 1, 'ACTIVE', 0.08, '{}', 'ortho'),

('N-O03', 'supra', 'HL-08-ORTHO-TKR', 'ANTI_PATTERN', 'Never Discharge TKR Under 48 Hours',
 'Do NOT discharge TKR patients before 48 hours post-op. Past incident: patient discharged at 36 hours developed DVT at home. Minimum 48 hours with physiotherapy assessment before discharge.',
 0.91, 1, 'ACTIVE', 0.10, '{}', 'ortho'),

('N-O04', 'supra', 'HL-05-ORTHO', 'DECISION', 'Zimmer Implant Preference',
 'Supra Ortho Department uses Zimmer Biomet as preferred TKR implant vendor. Alternative: Smith & Nephew for revision cases only. Decision based on 3-year outcomes review, Dr. Vikram, 2024.',
 0.72, 1, 'ACTIVE', 0.05, '{}', 'ortho'),

('N-O05', 'supra', 'HL-10-ORTHO-W', 'FACT', 'Ortho Ward Bed Capacity',
 'Ortho Ward: 45 beds. 12 post-surgical, 8 traction, 25 general ortho. Usual occupancy: 85-90%. Peak (winter fractures): 100%+, overflow to Medicine Ward.',
 0.50, 1, 'ACTIVE', 0.40, '{}', 'ortho'),

('N-O06', 'supra', 'HL-05-ORTHO', 'CONSTRAINT', 'DVT Prophylaxis Protocol',
 'ALL ortho surgical patients receive DVT prophylaxis: Enoxaparin 40mg SC daily starting 12 hours post-op. Duration: 14 days for TKR, 28 days for THR. Contraindication: active bleeding, platelet <50K.',
 0.93, 1, 'ACTIVE', 0.30, '{}', 'ortho'),

('N-O07', 'supra', 'HL-08-ORTHO-GEN', 'DECISION', 'Fracture X-Ray Protocol',
 'All suspected fractures: minimum 2 views (AP + lateral). Joint involvement: add oblique view. Growth plate involvement in paediatrics: compare with contralateral side. Digital X-ray preferred over CR.',
 0.75, 1, 'ACTIVE', 0.60, '{}', 'ortho'),

('N-O08', 'supra', 'HL-10-ORTHO-W', 'FACT', 'Ortho Ward Nurse-Patient Ratio',
 'Ortho Ward nurse-patient ratio: 1:6 (day), 1:8 (night). Post-surgical first 24 hours: 1:4. ICU-step-down patients: 1:2 until stable.',
 0.55, 1, 'ACTIVE', 0.35, '{}', 'ortho'),

('N-O09', 'supra', 'HL-08-POST-TKR', 'CONSTRAINT', 'Post-TKR Physiotherapy Start',
 'Physiotherapy MUST begin within 24 hours of TKR. Day 1: ankle pumps, static quads. Day 2: CPM machine, assisted standing. Delay beyond 24 hours increases stiffness risk significantly.',
 0.90, 1, 'ACTIVE', 0.20, '{}', 'ortho'),

('N-O10', 'supra', 'HL-05-ORTHO', 'ANTI_PATTERN', 'Weight-Bearing Before X-Ray Confirmation',
 'NEVER allow weight-bearing on a fractured limb before X-ray confirmation of alignment. Past incident: patient with tibial fracture allowed to stand, causing displacement requiring surgery.',
 0.89, 1, 'ACTIVE', 0.15, '{}', 'ortho'),

-- HOD-level Ortho nodes (visible to Vikram L4, NOT to Priya L10)
('N-O11', 'supra', 'HL-05-ORTHO', 'DECISION', 'Ortho Department Budget Allocation 2026',
 'FY 2026 budget: ₹4.2 Cr. Implants: 45%, Staffing: 30%, Equipment: 15%, Training: 10%. New arthroscopy equipment approved Q3. Budget review: Dr. Vikram quarterly.',
 0.70, 1, 'ACTIVE', 0.05, '{"MNPI"}', 'ortho'),

('N-O12', 'supra', 'HL-05-ORTHO', 'DECISION', 'Ortho Vendor Negotiation Strategy',
 'Renegotiate Zimmer contract in July 2026. Target: 12% discount on volume commitment of 200+ implants. Fallback: Smith & Nephew willing to offer 15% below current Zimmer price.',
 0.65, 1, 'ACTIVE', 0.03, '{"MNPI", "CONFIDENTIAL"}', 'ortho'),

-- Patient-level nodes
('N-O13', 'supra', 'HL-12-RAJAN', 'FACT', 'Patient Rajan: Warfarin History',
 'Rajan, 68M. On Warfarin 5mg daily for AF. INR target 2.0-3.0. GI bleed history 2024 (NSAID interaction). STRICTLY NO NSAIDs. Current INR: 2.4 (last checked 3 days ago).',
 0.88, 1, 'ACTIVE', 0.02, '{}', 'ortho'),

('N-O14', 'supra', 'HL-12-RAJAN', 'CONSTRAINT', 'Patient Rajan: Absolute NSAID Contraindication',
 'ABSOLUTE CONTRAINDICATION: No ibuprofen, no aspirin, no diclofenac for patient Rajan. Previous GI bleed 2024 was NSAID-induced while on Warfarin. Use Paracetamol ONLY for pain.',
 0.99, 1, 'ACTIVE', 0.01, '{}', 'ortho'),

('N-O15', 'supra', 'HL-10-ORTHO-W', 'DECISION', 'Ortho Night Shift Handover Protocol',
 'Night shift handover: 15-minute structured handover using SBAR format. Include: pending labs, new admissions past 4 hours, patients for morning surgery, any clinical concerns. Must be documented in ward log.',
 0.72, 1, 'ACTIVE', 0.45, '{}', 'ortho'),

-- ============================================================
-- GENERAL MEDICINE NODES (8 nodes — Ananya's department, NOT Priya's)
-- ============================================================

('N-M01', 'supra', 'HL-05-MED', 'CONSTRAINT', 'Diabetic Fasting Protocol',
 'Supra Medicine: for diabetic patients observing religious fasts — adjust insulin timing, NOT dose. Pre-fast: shift long-acting insulin to evening. During fast: monitor BG q4h. Break fast immediately if BG < 70.',
 0.90, 1, 'ACTIVE', 0.15, '{}', 'medicine'),

('N-M02', 'supra', 'HL-05-MED', 'DECISION', 'Sepsis Protocol v3 2026',
 'Supra Sepsis Bundle v3 (2026): blood cultures before antibiotics, lactate within 1 hour, 30mL/kg crystalloid for hypotension, vasopressors if MAP <65 after fluids. Updated from v2 which had 3-hour lactate window.',
 0.95, 1, 'ACTIVE', 0.25, '{}', 'medicine'),

('N-M03', 'supra', 'HL-08-MED-GEN', 'ANTI_PATTERN', 'Insulin Sliding Scale Alone',
 'Do NOT use insulin sliding scale as sole glycemic management. Past incident: patient with DKA had only sliding scale, no basal insulin — readmitted in 48 hours. Always include basal insulin.',
 0.87, 1, 'ACTIVE', 0.30, '{}', 'medicine'),

('N-M04', 'supra', 'HL-12-PADMA', 'FACT', 'Patient Padma: DM Fasting Patterns',
 'Padma, 62F. Type 2 DM on Metformin 1000mg BD + Glimepiride 2mg. Observes Ekadashi fasting (twice monthly). Adjusted protocol: skip Glimepiride on fast days, continue Metformin with evening meal.',
 0.82, 1, 'ACTIVE', 0.02, '{}', 'medicine'),

('N-M05', 'supra', 'HL-10-MED-W', 'DECISION', 'Medicine Ward IV Antibiotic Audit',
 'Weekly IV antibiotic audit by pharmacy team. Target: 80% appropriate prescribing. Current: 74%. Common errors: not stepping down to oral at 48-72 hours when clinically stable.',
 0.68, 1, 'ACTIVE', 0.20, '{}', 'medicine'),

('N-M06', 'supra', 'HL-05-MED', 'CONSTRAINT', 'Contrast Allergy Pre-Treatment',
 'Patients with documented contrast allergy: pre-treat with Hydrocortisone 200mg IV + Chlorpheniramine 10mg IV, 1 hour before procedure. Alternative imaging (MRI/ultrasound) preferred when feasible.',
 0.88, 1, 'ACTIVE', 0.35, '{}', 'medicine'),

('N-M07', 'supra', 'HL-05-MED', 'FACT', 'Medicine Department Specialty Clinics',
 'Medicine outpatient specialty clinics: DM clinic (Mon/Wed), Hypertension clinic (Tue/Thu), Respiratory clinic (Fri). Each clinic: 2 consultants, 1 registrar, 1 nurse.',
 0.45, 1, 'ACTIVE', 0.50, '{}', 'medicine'),

('N-M08', 'supra', 'HL-05-MED', 'DECISION', 'Sepsis Protocol v2 2024 (SUPERSEDED)',
 'OLD: Supra Sepsis Bundle v2 (2024): blood cultures before antibiotics, lactate within 3 hours. SUPERSEDED by v3 (2026) which tightened lactate window to 1 hour.',
 0.95, 1, 'SUPERSEDED', 0.25, '{}', 'medicine'),

-- ============================================================
-- CARDIOLOGY NODES (5 nodes — NOT reachable by Ortho users)
-- ============================================================

('N-C01', 'supra', 'HL-05-CARDIO', 'CONSTRAINT', 'Cardiac Catheterization Consent',
 'Written informed consent required minimum 4 hours before cardiac catheterization. Consent must include: procedure risks (0.1% mortality, 1% vascular complication), alternatives, and expected outcomes.',
 0.92, 1, 'ACTIVE', 0.30, '{}', 'cardiology'),

('N-C02', 'supra', 'HL-08-CARDIO-CCU', 'DECISION', 'CCU Troponin Protocol',
 'Serial troponin at 0, 3, 6 hours for STEMI rule-out. High-sensitivity troponin: if 0h < 5 ng/L AND no risk factors → early rule-out at 1 hour. Supra uses Abbott hs-cTnI assay.',
 0.90, 1, 'ACTIVE', 0.35, '{}', 'cardiology'),

('N-C03', 'supra', 'HL-05-CARDIO', 'ANTI_PATTERN', 'Discharge Without ECHO After First MI',
 'NEVER discharge a first MI patient without echocardiography. Past incident: patient discharged after NSTEMI without ECHO, returned in 2 weeks with CHF. Ejection fraction was 30%.',
 0.93, 1, 'ACTIVE', 0.15, '{}', 'cardiology'),

('N-C04', 'supra', 'HL-05-CARDIO', 'FACT', 'Cardiology Research Trial: ATOM-2026',
 'Ongoing trial: ATOM-2026 (Atorvastatin Optimization in MI). 50 patients enrolled. Comparing 40mg vs 80mg post-MI. PI: Dr. Mehta. IRB approved March 2026. CONFIDENTIAL until publication.',
 0.60, 1, 'ACTIVE', 0.05, '{"MNPI", "CONFIDENTIAL"}', 'cardiology'),

('N-C05', 'supra', 'HL-05-CARDIO', 'DECISION', 'Dual Antiplatelet Duration Post-Stent',
 'Supra Cardiology: DAPT (Aspirin + Clopidogrel/Ticagrelor) for 12 months post-DES. High bleeding risk: consider 6 months. Ultra-high ischemic risk: extend to 36 months. Decision documented per patient.',
 0.87, 1, 'ACTIVE', 0.40, '{}', 'cardiology'),

-- ============================================================
-- PAEDIATRICS NODES (3 nodes)
-- ============================================================

('N-P01', 'supra', 'HL-05-PAEDS', 'CONSTRAINT', 'Paediatric Drug Dose Weight-Based',
 'ALL paediatric drug doses must be weight-based (mg/kg). NEVER use adult fixed doses for children. Supra policy: weight documented on EVERY drug chart. Pharmacy double-checks paediatric prescriptions.',
 0.96, 1, 'ACTIVE', 0.50, '{}', 'paediatrics'),

('N-P02', 'supra', 'HL-10-PAEDS-W', 'DECISION', 'Paeds Ward Visiting Hours Extension',
 'Paeds Ward: parents allowed 24/7 (no visiting hour restriction). One parent can stay overnight. This policy improved parent satisfaction from 72% to 94% and reduced child anxiety scores.',
 0.60, 1, 'ACTIVE', 0.15, '{}', 'paediatrics'),

('N-P03', 'supra', 'HL-05-PAEDS', 'ANTI_PATTERN', 'Penicillin in Known Allergy Child',
 'CRITICAL: Patient Aadhya (3.5F) has documented penicillin allergy (anaphylaxis at 18 months). DO NOT prescribe amoxicillin, ampicillin, or any penicillin-class antibiotic. Use azithromycin.',
 0.99, 1, 'ACTIVE', 0.05, '{}', 'paediatrics'),

-- ============================================================
-- HOSPITAL-WIDE ADMIN NODES (4 nodes — visible only to ADMIN L1)
-- ============================================================

('N-A01', 'supra', 'HL-01', 'DECISION', 'Hospital Expansion Plan 2026-2028',
 'Board-approved: 80 additional beds by Q4 2027. New Oncology wing (40 beds), ICU expansion (20 beds), Ortho upgrade (20 beds). Total investment: ₹85 Cr. Contractor: L&T. STRICTLY CONFIDENTIAL.',
 0.80, 1, 'ACTIVE', 0.02, '{"MNPI", "CONFIDENTIAL"}', NULL),

('N-A02', 'supra', 'HL-01', 'DECISION', 'Staff Salary Restructuring 2026',
 'HR approved: 12% salary increase for nurses (effective July 2026), 8% for technicians. Consultant revision: performance-linked component increased from 15% to 25%. Board resolution #2026-014.',
 0.75, 1, 'ACTIVE', 0.01, '{"MNPI", "CONFIDENTIAL"}', NULL),

('N-A03', 'supra', 'HL-03-ADMIN', 'FACT', 'Hospital Accreditation Status',
 'NABH accreditation: valid until March 2027. Next assessment: October 2026. Gap areas: medication error reporting (82% vs 95% target), hand hygiene compliance (88% vs 95% target).',
 0.70, 1, 'ACTIVE', 0.20, '{}', NULL),

('N-A04', 'supra', 'HL-01', 'CONSTRAINT', 'Legal Case: Rajan Medico-Legal Hold',
 'LEGAL HOLD: All records related to patient Rajan (2024 GI bleed incident) are under medico-legal hold. NO modification, NO deletion, NO status change. Case: Rajan vs Supra, High Court Hyderabad.',
 0.95, 1, 'LEGAL_HOLD', 0.01, '{"CONFIDENTIAL"}', NULL),

-- ============================================================
-- HIGH-DERIVABILITY NODES (5 nodes — should be EXCLUDED by Check 5)
-- These contain knowledge the AI already has from training
-- ============================================================

('N-D01', 'supra', 'HL-05-ORTHO', 'FACT', 'What is a Total Knee Replacement',
 'Total knee replacement (TKR) is a surgical procedure where damaged knee joint surfaces are replaced with artificial components. Also called total knee arthroplasty (TKA).',
 0.40, 1, 'ACTIVE', 0.92, '{}', 'ortho'),

('N-D02', 'supra', 'HL-05-MED', 'FACT', 'Paracetamol Mechanism of Action',
 'Paracetamol (acetaminophen) is an analgesic and antipyretic. Mechanism: inhibits prostaglandin synthesis in the CNS. Standard adult dose: 500-1000mg every 4-6 hours, max 4g/day.',
 0.35, 1, 'ACTIVE', 0.95, '{}', 'medicine'),

('N-D03', 'supra', 'HL-GLOBAL', 'FACT', 'Normal Vital Sign Ranges Adult',
 'Normal adult vital signs: HR 60-100 bpm, BP 120/80 mmHg (normal), RR 12-20/min, SpO2 >95%, Temp 36.1-37.2°C. Variations normal for age, activity, and medication.',
 0.30, 1, 'ACTIVE', 0.98, '{}', NULL),

('N-D04', 'supra', 'HL-05-ORTHO', 'FACT', 'What is Deep Vein Thrombosis',
 'Deep vein thrombosis (DVT) is a blood clot in a deep vein, usually in the legs. Risk factors: surgery, immobility, cancer, pregnancy. Symptoms: leg swelling, pain, warmth.',
 0.35, 1, 'ACTIVE', 0.93, '{}', 'ortho'),

('N-D05', 'supra', 'HL-05-MED', 'FACT', 'What is Type 2 Diabetes Mellitus',
 'Type 2 diabetes mellitus is a chronic condition where the body becomes resistant to insulin or does not produce enough insulin. Most common form of diabetes. Risk factors: obesity, sedentary lifestyle, family history.',
 0.30, 1, 'ACTIVE', 0.96, '{}', 'medicine');
```

---

## SEED DATA — EDGES

```sql
-- ============================================================
-- Typed Edges Between Nodes
-- ============================================================

INSERT INTO edges (source_id, target_id, edge_type) VALUES
-- SUPPORTS relationships
('N-O02', 'N-O01', 'SUPPORTS'),      -- Paracetamol decision supports post-op vitals
('N-O06', 'N-O01', 'SUPPORTS'),      -- DVT prophylaxis supports post-op monitoring
('N-O09', 'N-O03', 'SUPPORTS'),      -- PT start supports no-early-discharge
('N-G01', 'N-O14', 'SUPPORTS'),      -- Global Warfarin rule supports Rajan constraint

-- DERIVED_FROM relationships
('N-O03', 'N-O01', 'DERIVED_FROM'),  -- TKR discharge rule derived from post-op protocol
('N-O14', 'N-G01', 'DERIVED_FROM'),  -- Rajan NSAID ban derived from global Warfarin rule
('N-M02', 'N-M08', 'SUPERSEDES'),    -- Sepsis v3 supersedes Sepsis v2

-- CONTRADICTS
('N-D01', 'N-O02', 'SUPPORTS'),      -- Generic TKR info supports specific Supra TKR decision

-- REQUIRES
('N-O02', 'N-O06', 'REQUIRES'),      -- Paracetamol protocol requires DVT prophylaxis in place
('N-C02', 'N-C01', 'REQUIRES');      -- Troponin protocol requires cath consent process
```

---

## EXPECTED PIPELINE RESULTS (Verify Your Implementation)

### Nurse Priya (VIEWER, L10, Ortho Ward)

| Stage | Count | What Happens |
|-------|:-----:|-------------|
| Total graph | 50 | All nodes in database |
| BFS from Ortho Ward (L10) | ~20 | Reaches: Ortho Ward → Ortho Gen → Ortho Dept → Clinical → Hospital. Includes TKR unit, Post-TKR (multi-parent). Excludes Medicine, Cardio, Paeds, ICU, Surgery |
| +Zone 2 (GLOBAL) | ~30 | 10 global nodes added |
| Check 1: Isolation | ~30 | All pass (single org) |
| Check 2: Compliance | ~28 | N-O11 (MNPI), N-O12 (MNPI+CONFIDENTIAL) excluded — Priya has no compliance clearance |
| Check 3: Permission | ~22 | Nodes at levels < 10 (above Priya's ceiling) that she can't reach are already excluded by BFS. Remaining HOD-level nodes excluded |
| Check 4: Temporal | ~21 | N-M08 (SUPERSEDED Sepsis v2) excluded if it somehow was in set |
| Check 5: Derivability | ~15 | N-D01 (0.92), N-D03 (0.98), N-D04 (0.93) excluded — AI already knows this |
| **Final candidate set** | **~15** | Only Ortho-relevant + global safety nodes, all current, all org-specific |

### Dr. Vikram (HOD, L4, Ortho Department)

| Stage | Count | Notes |
|-------|:-----:|-------|
| BFS from Ortho Dept (L5) | ~25 | Deeper reach: sees L4-level department decisions |
| +Zone 2 | ~35 | Same 10 globals |
| After 5 checks | ~22 | Sees N-O11 (budget) but NOT N-O12 (MNPI+CONFIDENTIAL — needs ADMIN clearance). Sees more ortho nodes than Priya |

### Admin Suresh (ADMIN, L1, Full Hospital)

| Stage | Count | Notes |
|-------|:-----:|-------|
| BFS from Hospital (L1) | 50 | Reaches ALL nodes (enters at root) |
| +Zone 2 | 50 | Already included |
| After 5 checks | ~40 | Has MNPI+PHI+CONFIDENTIAL clearance. Only derivability + temporal exclude nodes. Sees N-A01, N-A02, N-O11, N-O12, N-C04. |

---

## CANDIDATE SET OUTPUT FORMAT

Your pipeline should output a JSON array like this:

```json
{
  "user": "U-PRIYA",
  "user_name": "Nurse Priya",
  "role": "VIEWER",
  "ceiling_level": 10,
  "entry_point": "HL-10-ORTHO-W",
  "pipeline_timing": {
    "permission_compile_ms": 12,
    "bfs_ms": 45,
    "zone2_inject_ms": 8,
    "check1_isolation_ms": 3,
    "check2_compliance_ms": 5,
    "check3_permission_ms": 4,
    "check4_temporal_ms": 3,
    "check5_derivability_ms": 15,
    "total_ms": 95
  },
  "funnel": {
    "total_nodes": 50,
    "after_bfs": 20,
    "after_zone2": 30,
    "after_check1": 30,
    "after_check2": 28,
    "after_check3": 22,
    "after_check4": 21,
    "after_check5": 15
  },
  "candidate_set": [
    {
      "id": "N-G01",
      "type": "CONSTRAINT",
      "title": "Warfarin-NSAID Interaction",
      "content": "CRITICAL: Never prescribe NSAIDs...",
      "importance": 0.98,
      "zone": 2,
      "hierarchy_level": 3,
      "department": null,
      "distance_from_entry": 4,
      "compression_hint": "CONSTRAINT_ONLY"
    },
    {
      "id": "N-O02",
      "type": "DECISION",
      "title": "Paracetamol First-Line Post-TKR",
      "content": "Supra Ortho uses Paracetamol 650mg QDS...",
      "importance": 0.88,
      "zone": 1,
      "hierarchy_level": 8,
      "department": "ortho",
      "distance_from_entry": 1,
      "compression_hint": "FULL"
    }
  ]
}
```

---

## SUBMISSION CHECKLIST

```
□ README.md with setup instructions
□ .env.example (no real keys)
□ supabase/schema.sql runs without errors
□ supabase/seed.sql loads all 50 nodes + 7 users
□ Permission compiler produces O(1) lookup structure
□ BFS correctly traverses upward from entry point
□ Visited set prevents multi-parent re-processing
□ Zone 2 nodes injected after BFS, before 5 checks
□ All 5 checks run sequentially (output of N → input of N+1)
□ Priya sees ~15 nodes, Vikram sees ~22, Suresh sees ~40
□ Priya's set: ZERO Cardiology/Paeds/ICU/Medicine-only nodes
□ Priya's set: ZERO MNPI-tagged nodes (no compliance clearance)
□ Priya's set: ZERO superseded nodes (Sepsis v2 excluded)
□ Priya's set: ZERO high-derivability nodes (generic knowledge excluded)
□ Silent exclusion: no error messages, no "access denied"
□ Filter funnel visualization shows count at each stage
□ Pipeline timing displayed
□ User switching re-runs actual pipeline (not hardcoded)
□ Candidate set includes metadata (type, importance, distance, compression_hint)
□ docs/architecture.md explains BFS strategy + filter ordering rationale
□ Clean git history
□ Try a user NOT in your 4 demos — does the pipeline work?
```

---

## FREE TIER SUFFICIENCY

| Resource | Free Tier | Sufficient? |
|---|---|---|
| **Supabase** | 500 MB storage, 50K rows | YES — 50 nodes + 7 users is trivial |
| **LLM API** | Not needed | This pipeline uses ZERO LLM |
| **Vercel (optional)** | Free hobby tier | YES — for frontend hosting if desired |

**Total cost to complete this assessment: $0**

---

*Setup Guide v1.0 — BFS Traversal + 5-Check Filter Pipeline*
