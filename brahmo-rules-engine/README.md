# BRAHMO Rules Engine — BFS + 5-Check Filter Pipeline

A deterministic (zero-LLM) pipeline that filters a hospital knowledge graph down
to the exact candidate set a given user is allowed to see: BFS traversal upward
through a 15-level DAG, Zone 2 (global) injection, then five sequential
pass/fail checks (isolation, compliance, permission, temporal, derivability).

See `../ASSESSMENT_01_BFS_Traversal_5Check_Filter.md` and
`../ASSESSMENT_01_SETUP_GUIDE.md` for the full spec, and `../IMPLEMENTATION_PLAN.md`
for the design plan this was built from. `docs/architecture.md` explains the
concrete decisions made while building it.

## 1. Setup

### 1.1 Supabase project

1. Create a free project at [supabase.com](https://supabase.com).
2. Open the SQL Editor and run `supabase/schema.sql`, then `supabase/seed.sql`.
3. Verify: `SELECT COUNT(*) FROM knowledge_nodes` → 50, `SELECT COUNT(*) FROM users` → 7.
4. Settings → API → copy the **Project URL** and **service_role** key.

### 1.2 Environment

```bash
cp .env.example .env.local   # already done in this repo — just fill in the blanks
```

Fill in `.env.local` at the repo root:

- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — used by the FastAPI backend (service role key, never exposed to the browser).
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` — not required by the current frontend (it talks to the FastAPI backend, not Supabase directly) but included for completeness / future direct-client use.

Also copy the `NEXT_PUBLIC_*` values into `frontend/.env.local` (Next.js only reads env files from its own directory) — a starter one already exists there with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` filled in.

### 1.3 Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload --port 8000
```

Verify: `curl localhost:8000/health` → `{"status":"ok"}`, `curl localhost:8000/api/users` → 7 users.

### 1.4 Frontend

```bash
cd frontend
npm install
npm run dev   # → http://localhost:3000
```

### 1.5 Tests

```bash
source venv/bin/activate
cd backend
pytest tests/ -v
```

`test_bfs.py`, `test_permission_compiler.py`, `test_five_checks.py` are pure
(no DB needed) and always run. `test_pipeline.py` is an end-to-end integration
suite against your live Supabase project — it auto-skips until `.env.local`
is filled in.

## 2. Using the demo

1. Open `http://localhost:3000`.
2. **Pipeline tab**: pick a user, hit "Run Pipeline". Watch the funnel narrow,
   the DAG viewer highlight reachable/Zone-2/unreachable nodes, and the
   candidate set populate.
3. Toggle "Zone 2 injection" off/on to demonstrate why global safety nodes matter.
4. **Comparison tab**: select 2-3 users, run them together, see the same graph
   produce different candidate sets and department-visibility checklists.

## 3. Project layout

```
backend/    FastAPI app + pipeline modules (permission compiler, BFS, zone2,
            5-check filter, candidate assembler, orchestrator)
frontend/   Next.js + Tailwind demo UI
supabase/   schema.sql + seed.sql (50 nodes, 7 users, 15-level hierarchy)
docs/       architecture.md — design rationale
```
