# DEVELOPER ASSESSMENT 1: Make AI See Only What This User Should See
## BFS Traversal + 5-Check Filter Pipeline — Knowledge Graph to Candidate Set
### BRAHMO — Full-Stack Developer Assessment

**Time:** 5-8 hours | **Demo:** 20-25 minutes | **Deadline:** 72 hours
**Stack:** Supabase + Python (FastAPI) + React + Tailwind CSS
**Tools:** Use ANY AI tool — no paid subscriptions required (see Setup Guide)
**Deliverables:** Working demo + source code + architecture notes

---

## THE STORY THAT STARTED THIS (Why This Matters)

Supra Multi-Specialty Hospital in Hyderabad has 180 beds across 6 departments. Over 3 years, they've accumulated 842 knowledge nodes — drug safety protocols, clinical decisions, department-specific anti-patterns, patient-level constraints. Everything from "Never prescribe NSAIDs to anticoagulated patients" to "Ortho Ward uses Paracetamol 650mg QDS as first-line post-TKR pain."

Nurse Priya works the Ortho Ward night shift. She opens an AI session to ask about post-operative pain management for a patient. The AI should know Supra's specific Ortho protocols — but it must NOT see Cardiology's experimental drug trial data (department isolation), must NOT see the HOD's admin-level decisions (permission ceiling), must NOT see the expired 2023 Sepsis Protocol that was superseded last month (temporal validity), and must NOT waste tokens telling the AI that "Paracetamol is an analgesic" (derivable from general knowledge).

842 nodes exist. Priya should see exactly 28.

Every enterprise AI tool today — Microsoft Copilot, Glean, Notion AI — shows either EVERYTHING (security disaster) or requires manual tagging (never maintained). Nobody builds a system where the AI automatically knows the RIGHT 28 nodes for THIS user at THIS moment.

**Your job:** Build the pipeline that takes 842 knowledge nodes and filters them to exactly the right 28 for Nurse Priya — with ZERO configuration, ZERO manual tagging, ZERO security gaps. The filtering happens in under 500ms, entirely without any LLM, and produces a clean candidate set that downstream systems consume.

---

## WHAT YOU'RE BUILDING (2-minute read)

A Rules Engine pipeline that traverses a Directed Acyclic Graph (DAG) of knowledge nodes upward from a user's entry point, injects globally-relevant nodes, then applies 5 sequential checks to filter the result down to a candidate set of 20-30 nodes — all deterministically, with ZERO LLM involvement.

**The data flow:**
```
Nurse Priya opens AI session (role: VIEWER, ceiling: Level 10, dept: Ortho Ward)
  → Permission Compiler runs ONCE at session start (~15ms):
    └── Builds O(1) lookup: {level: can_read, can_write} for all 15 levels
  → Entry Point Resolver (~5ms):
    └── Maps Priya's dept to her DAG leaf node (Ortho Ward, Level 10)
  → BFS Traversal walks UP the DAG (~50ms):
    ├── Starts at Ortho Ward (Level 10)
    ├── Walks to Orthopaedics Dept (Level 8)
    ├── Walks to Clinical Division (Level 5)
    ├── Walks to Supra Hospital (Level 1)
    ├── Multi-parent: "Post-TKR Protocol" → Ortho AND General Surgery
    ├── Visited set prevents re-processing
    └── Collects ~450 reachable nodes
  → Zone 2 Injection (~10ms):
    └── 185 GLOBAL nodes injected into reachable set → ~500 nodes
  → Five-Check Sequential Filter (~200ms):
    ├── Check 1 ISOLATION:  org_id = 'supra'              → 500 remain
    ├── Check 2 COMPLIANCE: NOT MNPI-tagged                → 488 remain
    ├── Check 3 PERMISSION: hierarchy_level >= 10 (ceiling) → 312 remain
    ├── Check 4 TEMPORAL:   not expired, not superseded     → 298 remain
    └── Check 5 DERIVABILITY: score < 0.7 (org-specific)   → 28 remain
  → Candidate Set output: 28 annotated nodes with metadata
    └── Each node carries: type, importance, distance, zone, compression_hint
```

**What we provide:** 50 seed knowledge nodes across 6 departments, 7 user profiles with different roles/ceilings, DAG hierarchy definition (15 levels), edge relationships, compliance tags — all in Setup Guide.

**What you figure out (25-30%):** BFS implementation strategy, permission compilation data structure, derivability scoring approach, how to handle multi-parent DAG nodes, performance optimization for the 5-check pipeline.

---

## HOW TO THINK ABOUT THIS (Read Before You Code)

### Mental Model

This system enforces a FUNDAMENTAL RULE of the BRAHMO architecture: **The Rules Engine (L2) uses ZERO LLM.** Every decision is binary — yes/no, pass/fail, include/exclude. An LLM making permission decisions is a SECURITY FAILURE. A deterministic engine making relevance judgments is a quality failure. Your pipeline is entirely deterministic.

Think of it as a series of progressively tighter sieves:

**Sieve 1 — BFS Reach:** "Which nodes can this user physically reach by walking up the DAG from their position?" This is structural — determined by graph topology, not content.

**Sieve 2 — Zone 2 Injection:** "Which globally-important nodes must be in EVERY session regardless of traversal path?" Drug safety constraints, hospital-wide policies. These bypass the BFS but still go through all 5 checks.

**Sieve 3-7 — Five Checks:** Each check takes the OUTPUT of the previous check as input. Sequential, not parallel. Check 3 cannot run until Check 2 has excluded its nodes — because a compliance-excluded node should never even reach the permission check.

**The output** is NOT the final context the AI sees. It's a CANDIDATE SET — a filtered, annotated list that a downstream Composition Agent (not built in this assessment) will compress and assemble into the actual prompt. Your job ends at producing the candidate set.

### Decision Priority

| Priority | Component | Why | Time Allocation |
|---|---|---|---|
| 1 | Five-check filter pipeline | The CORE — this is what makes BRAHMO secure | 30% |
| 2 | BFS traversal with DAG handling | Graph structure determines reach | 20% |
| 3 | Permission compilation | O(1) lookup is the performance enabler | 15% |
| 4 | Visualization + demo UI | Must make filtering VISIBLE — show the funnel | 20% |
| 5 | Innovation | Your 25-30% | 15% |

**The single most important thing:** The pipeline must produce DIFFERENT results for DIFFERENT users querying the SAME graph. Nurse Priya (VIEWER, L10, Ortho) sees 28 nodes. Dr. Vikram (HOD, L4, Ortho) sees 74 nodes from the same graph. Admin Suresh (ADMIN, L1) sees 298 nodes. If all three see the same nodes, the pipeline is broken.

### What NOT to Overthink

- Don't build the Composition Agent (the downstream system that compresses candidate nodes into an AI prompt) — your job ends at the candidate set
- Don't build a full authentication system — use simple user selection (dropdown) for the demo
- Don't build a knowledge node editor — nodes are pre-seeded
- Don't use an LLM anywhere in the pipeline — this is the ZERO-LLM layer
- Don't build real-time graph updates — the graph is static for this assessment

---

## WHAT YOUR FINISHED PRODUCT LOOKS LIKE

**Main View — Pipeline Visualization:**
```
┌──────────────────────────────────────────────────────────────────┐
│  BRAHMO Rules Engine — BFS + 5-Check Filter Pipeline             │
│                                                                  │
│  User: [▼ Nurse Priya — VIEWER, L10, Ortho Ward]                │
│  Entry Point: Ortho Ward (Level 10)                              │
│  [Run Pipeline]                                                  │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ TOTAL   │ →  │  BFS    │ →  │ +Zone 2 │ →  │ 5-CHECK │       │
│  │  842    │    │  ~315   │    │  ~500   │    │   28    │       │
│  │ nodes   │    │reachable│    │combined │    │ final   │       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│                                                                  │
│  FILTER FUNNEL:                                                  │
│  ████████████████████████████████████████  500 after BFS+Zone2   │
│  ███████████████████████████████████████   488 after ISOLATION    │
│  ████████████████████████████████████      488 after COMPLIANCE   │
│  ██████████████████████                    312 after PERMISSION   │
│  █████████████████████                     298 after TEMPORAL     │
│  ████                                       28 after DERIVABILITY │
│                                                                  │
│  Pipeline time: 287ms | Zero LLM calls | Deterministic           │
│                                                                  │
├───────────────────────┬──────────────────────────────────────────┤
│ DAG VISUALIZATION     │ CANDIDATE SET (28 nodes)                 │
│                       │                                          │
│ [L1] Supra Hospital   │ 🔴 CONSTRAINT (8 nodes)                 │
│  ├─[L3] Clinical      │  ├── Drug interaction: Warfarin+NSAIDs   │
│  │  ├─[L5] Ortho Dept │  ├── Post-op vitals q15min first 4hrs   │
│  │  │  ├─[L8] Ortho   │  └── ... 6 more                         │
│  │  │  │  Ward ←PRIYA │ 🟡 DECISION (11 nodes)                  │
│  │  │  └─[L8] Surg    │  ├── Paracetamol 650mg QDS post-TKR     │
│  │  └─[L5] Medicine   │  └── ... 10 more                        │
│  └─[L3] Admin         │ 🟠 ANTI_PATTERN (4 nodes)               │
│                       │  ├── Never discharge TKR < 48 hours      │
│ ● Priya's reachable   │  └── ... 3 more                         │
│ ○ Not reachable       │ 🔵 FACT (5 nodes)                       │
│ ◆ Zone 2 (global)     │  ├── Supra uses Zimmer implants         │
│                       │  └── ... 4 more                         │
│                       │                                          │
│                       │ Each node shows:                         │
│                       │  importance | distance | zone | type     │
└───────────────────────┴──────────────────────────────────────────┘
```

**Comparison View — Same Graph, Different Users:**
```
┌─────────────────┬─────────────────┬─────────────────┐
│ Nurse Priya     │ Dr. Vikram      │ Admin Suresh    │
│ VIEWER, L10     │ HOD, L4         │ ADMIN, L1       │
│ Ortho Ward      │ Ortho Dept      │ Full Hospital   │
├─────────────────┼─────────────────┼─────────────────┤
│ BFS reach: 315  │ BFS reach: 420  │ BFS reach: 842  │
│ +Zone 2:  500   │ +Zone 2:  540   │ +Zone 2:  842   │
│ After 5ck: 28   │ After 5ck: 74   │ After 5ck: 298  │
│ Time: 287ms     │ Time: 312ms     │ Time: 445ms     │
│                 │                 │                 │
│ ✗ L4 HOD nodes  │ ✓ L4 HOD nodes  │ ✓ All nodes     │
│ ✗ Cardio nodes  │ ✗ Cardio nodes  │ ✓ Cardio nodes  │
│ ✗ MNPI nodes    │ ✗ MNPI nodes    │ ✓ MNPI nodes    │
│ ✓ Ortho Ward    │ ✓ Full Ortho    │ ✓ Everything    │
│ ✓ Drug safety   │ ✓ Drug safety   │ ✓ Drug safety   │
└─────────────────┴─────────────────┴─────────────────┘
```

---

## DEMO SCENARIOS (Run all 4)

### Scenario 1: "The Core Pipeline" (Nurse Priya — VIEWER)
**User:** Nurse Priya (VIEWER, ceiling L10, Ortho Ward)
**What to show:** Full pipeline execution. 842 → BFS reach → Zone 2 injection → 5 checks → 28 nodes. Narrate each check with numbers: "Check 3 removed 176 nodes Priya can't see because her ceiling is Level 10 — all HOD-level and admin-level nodes excluded." Show the filter funnel visualization. Show the final candidate set with node types and metadata.

**What we're evaluating:** Does the candidate set contain ONLY Ortho-relevant and global nodes? Are Cardiology nodes absent? Are admin-level nodes absent? Is the superseded Sepsis Protocol v2 absent (temporal check)? Are derivable facts excluded?

### Scenario 2: "Same Graph, Different User" (Dr. Vikram — HOD)
**User:** Dr. Vikram (HOD, ceiling L4, Ortho Department)
**What to show:** Switch user in dropdown. Re-run pipeline on the SAME graph. Dr. Vikram sees 74 nodes — all of Priya's 28 PLUS nodes at levels 4-9 that Priya couldn't see. Show the comparison: "Priya sees 28, Vikram sees 74 from the same graph — 46 additional nodes that require HOD-level access."

**Critical test:** The pipeline code is identical. Only the user profile changes. The BFS entry point changes (Vikram enters at L4 Ortho Dept, not L10 Ortho Ward), the permission ceiling changes, but the checks are the same code path.

### Scenario 3: "Silent Exclusion + Security" (Cross-department isolation)
**User:** Nurse Priya again
**What to show:** Priya's candidate set contains ZERO Cardiology nodes, ZERO Paediatrics nodes, ZERO ICU nodes — even though they exist in the graph. But there is NO error message, NO "access denied," NO indication these nodes exist. Show: Priya's query returns 28 nodes. The response doesn't say "12 nodes were hidden" — it says nothing. This is SILENT EXCLUSION.

**Why this matters:** If the system returns "3 nodes were restricted," an attacker knows those nodes exist. Silent exclusion means unauthorized nodes are invisible — not denied, but absent.

### Scenario 4: "Zone 2 Saves Lives" (Global drug safety)
**User:** Nurse Priya
**What to show:** Among Priya's 28 nodes, highlight the ones that came from Zone 2 (GLOBAL). These are drug safety constraints like "Never combine Warfarin with NSAIDs" — they apply to EVERY department. Show: even though Priya's BFS only traversed the Ortho branch, Zone 2 injection added hospital-wide drug safety nodes. These nodes STILL passed all 5 checks (they're not MNPI-tagged, they're within Priya's permission ceiling, they're not expired, they're not derivable). Remove Zone 2 injection → show what Priya's set looks like WITHOUT drug safety nodes. The gap is the argument for Zone 2.

---

## SURPRISE TEST (CRITICAL — READ THIS)

After your 4 demos, we add a **NEW user profile** you haven't seen — maybe a Pharmacist (VIEWER, L12, Pharmacy), or a Quality Officer (QUALITY, L6, Cross-department), or an External Auditor (AUDITOR, L3, read-only, MNPI-allowed).

**What we're testing:**
- Your pipeline handles a new role without code changes — because the 5 checks are driven by USER PROFILE DATA, not hardcoded role logic
- The BFS entry point changes correctly for the new user's department
- The permission ceiling filters differently based on the new user's level
- Compliance filtering respects the new user's compliance clearance (auditor can see MNPI)

**HOW WE DETECT HARDCODING:**
- If switching to Pharmacist produces 28 nodes (same as Priya) → you hardcoded the output
- If the pipeline takes the same time regardless of user → you're not actually traversing
- If adding a new department requires code changes → your BFS isn't reading from the graph
- If MNPI filtering is hardcoded to exclude for all users → the auditor scenario breaks

**The Scalability Question:**
"This hospital has 842 nodes. A hospital chain has 15,000 nodes across 12 hospitals. What changes in your pipeline?"

**Right answer:** "The BFS traversal is bounded by the user's reachable subgraph — Priya's traversal touches ~315 nodes regardless of total graph size. Checks 1-4 execute as SQL WHERE clauses in the database — they scale with indexes. Derivability is a pre-computed score, not computed at query time. The pipeline time stays under 500ms because it's proportional to reachable nodes, not total nodes."

**Wrong answer:** "I'd need to optimize the database..." (means you're fetching all nodes first)

---

## WHAT 10/10 LOOKS LIKE

*"The funnel visualization immediately made me understand what the pipeline does — 842 goes in, 28 comes out, and I can see exactly where each check removed nodes. Switching from Priya to Vikram and seeing the count change from 28 to 74 in real time was the 'aha' moment. The silent exclusion demo was subtle but powerful — Priya's response looks complete, not filtered. I checked: zero Cardiology nodes, zero admin nodes, zero expired protocols. The Zone 2 demo proved why global injection matters — without it, drug safety constraints were missing. And the surprise user worked on the first try. This is the kind of permission-aware filtering that Copilot and Glean don't do."*

---

## OPEN-ENDED THINKING GUIDE (Your 25-30%)

### Problem 1: "How do you compute derivability without an LLM?"

The derivability filter excludes nodes that an AI can answer from general knowledge — "Paracetamol is an analgesic" wastes tokens because the AI already knows this. But the Rules Engine (L2) uses ZERO LLM. How do you score derivability? Options: pre-computed embeddings compared against a medical knowledge base, heuristic rules (e.g., if node content matches a Wikipedia heading, it's derivable), keyword density analysis, or a hybrid. What's your approach? How do you handle the edge case: "Standard dose of Paracetamol is 650mg" (derivable — AI knows this) vs "Supra uses Paracetamol 650mg QDS as first-line post-TKR pain" (not derivable — organization-specific)?

### Problem 2: "What if a node belongs to TWO departments?"

A "Post-TKR Protocol" node is relevant to BOTH Orthopaedics and General Surgery. In the DAG, it has two parents — it's reachable from both departments. When Priya (Ortho) does BFS, she reaches it via Ortho. When a Surgery nurse does BFS, they reach it via Surgery. But without a visited set, a traversal could process it twice. And in the permission check — which department's ceiling applies? Show how your DAG handles multi-parent nodes correctly.

### Problem 3: "Checks 1-4 in the database vs application code"

Checks 1-4 (isolation, compliance, permission, temporal) are all binary SQL conditions: `WHERE org_id = X AND NOT ('MNPI' = ANY(compliance_tags)) AND hierarchy_level >= Y AND (valid_until IS NULL OR valid_until > NOW())`. Should you run these as SQL WHERE clauses (database does the work) or fetch all nodes and filter in Python (application does the work)?

The correct answer: DATABASE. But show WHY — if you fetch all 842 nodes to Python and filter, you've violated GAP 5 (restricted data retrieved before permission check). Even if you discard restricted nodes in Python, they traveled over the network. RLS policies or SQL WHERE clauses ensure restricted data never leaves the database.

### Problem 4: "What happens when the graph has cycles?"

The knowledge graph is a DAG — Directed ACYCLIC Graph. But what if someone accidentally creates a cycle (Node A → Node B → Node C → Node A)? Your BFS must not infinite-loop. The visited set handles this — but do you also validate on insert that cycles can't be created? Show your cycle prevention strategy.

### Problem 5: "Permission compilation — why O(1) matters"

Priya has a permission ceiling of Level 10. For each of the 500 nodes after BFS+Zone2, you need to check: "Is this node's hierarchy level within Priya's ceiling?" If you query the database for EACH node's permission, that's 500 DB queries (N+1 problem). If you compile permissions ONCE at session start into a hashmap `{level: {can_read: bool}}`, each check is an O(1) dictionary lookup. Show: the data structure, how it's compiled, and the performance difference.

---

## EVALUATION CRITERIA

| Criteria | Weight | 10/10 looks like |
|----------|:------:|-----------------|
| **Pipeline correctness** | 30% | All 5 checks execute in correct order. Output of check N is input to check N+1. Different users produce DIFFERENT candidate sets from the same graph. Zero unauthorized nodes in ANY candidate set. |
| **Security model** | 25% | Silent exclusion (no errors, no indication of hidden nodes). Permission check BEFORE data retrieval (GAP 5). No LLM in the pipeline. Compliance tags enforced. MNPI nodes invisible to non-cleared users. |
| **DAG + BFS implementation** | 20% | Multi-parent nodes handled correctly (visited set). BFS walks upward from leaf. Zone 2 injection at correct pipeline position (after BFS, before checks). Cycle prevention present. |
| **Demo impact + visualization** | 15% | Filter funnel makes the pipeline intuitive. User comparison is visually dramatic. Pipeline timing displayed. Node metadata visible in candidate set. |
| **Innovation** | 10% | Solves a real problem from thinking guide. Shows performance awareness. Demonstrates understanding of why each architectural choice matters. |

---

## COMMON PITFALLS

- ❌ Using an LLM anywhere in the filter pipeline → fundamental rule violation, auto-fail
- ❌ Fetching all 842 nodes to application memory, then filtering in Python → GAP 5 violation (restricted data retrieved before permission check)
- ❌ Running the 5 checks in parallel → Check 3 output depends on Check 2 output; sequential is mandatory
- ❌ No visited set in BFS → multi-parent node processed twice, or infinite loop on accidental cycle
- ❌ Returning HTTP 403 or "access denied" for unauthorized nodes → must be SILENT exclusion (node absent, not denied)
- ❌ Forgetting Zone 2 injection → drug safety constraints missing from Priya's session
- ❌ Hardcoding the output per user → switching users must re-run the actual pipeline
- ❌ Same candidate set for all users → pipeline isn't actually filtering
- ❌ Derivability check calling an LLM → must use pre-computed scores, NOT runtime LLM analysis
- ❌ Per-node database query during traversal → N+1 query disaster; compile permissions ONCE

---

## PRE-DEMO CHECKLIST

```
□ 50 knowledge nodes loaded in Supabase (run: SELECT COUNT(*) FROM knowledge_nodes)
□ 7 user profiles loaded with different roles, ceilings, departments
□ DAG hierarchy (15 levels) correctly defined with parent-child edges
□ BFS traversal walks upward from entry point (verify: Priya reaches Ortho→Clinical→Hospital)
□ Zone 2 nodes (GLOBAL) injected after BFS, before 5 checks
□ Check 1 (Isolation): only org_id = 'supra' nodes remain
□ Check 2 (Compliance): MNPI-tagged nodes excluded for non-cleared users
□ Check 3 (Permission): nodes above user's ceiling excluded
□ Check 4 (Temporal): expired and superseded nodes excluded
□ Check 5 (Derivability): high-derivability nodes excluded
□ Priya sees ~28 nodes, Vikram sees ~74, Suresh sees ~298
□ Priya's set contains ZERO Cardiology/Paeds/ICU nodes
□ No error messages or "access denied" — silent exclusion only
□ Filter funnel visualization shows numbers at each stage
□ Pipeline timing displayed (should be < 500ms)
□ Try switching to a user NOT in your demos — does the pipeline work?
□ Clean git, README, architecture.md
```

---

## FAQ

**Q: Do I need to build the full knowledge graph with 842 nodes?**
A: No. We provide 50 seed nodes across 6 departments. Your pipeline must work correctly with these 50. The numbers in the scenario (842 → 28) describe the production system — your demo shows the same PATTERN at smaller scale (50 → ~12 for Priya, ~25 for Vikram).

**Q: What database should I use?**
A: Supabase (PostgreSQL). The RLS (Row-Level Security) capabilities are important — Checks 1-4 can be implemented as RLS policies or SQL WHERE clauses. Supabase's free tier is sufficient.

**Q: How do I implement the derivability score?**
A: For this assessment, pre-compute and store a `derivability_score` (0.0-1.0) on each node during seed data loading. In production, this would be a batch job. The heuristic is yours to design — simple approaches (keyword matching against common medical terms, content length analysis) are acceptable. If you ADD a more sophisticated approach, that's innovation.

**Q: Should I implement RLS policies or application-level filtering?**
A: Either approach is acceptable for the demo. RLS is architecturally correct (enforces at database level). Application-level filtering is faster to build. If you implement RLS, explain why it's better. If you use application-level, acknowledge the tradeoff and explain how you'd move to RLS in production.

**Q: What does the candidate set output look like?**
A: A JSON array of annotated nodes. Each node includes: `id`, `type`, `content`, `importance`, `zone`, `hierarchy_level`, `distance_from_entry` (computed during BFS), `compression_hint` (FULL/COMPRESSED/CONSTRAINT_ONLY based on distance). This is the interface contract with the downstream Composition Agent.

**Q: Do I need to handle real-time graph updates?**
A: No. The graph is static for this assessment. Nodes are pre-seeded. Focus on the query-time pipeline, not graph mutation.

**Q: Can I use pgvector or embeddings?**
A: Not required for the core pipeline (the Rules Engine is ZERO-LLM, ZERO-embedding). If you use embeddings for derivability scoring as an INNOVATION, that's acceptable — but it runs as a pre-computation batch job, not at query time in the pipeline.

---

## DAY-OF-DEMO

- **Format:** Video call. Screen share. App running before call starts.
- **Duration:** 20-25 minutes. Punctual.
- **Have ready:** Pipeline pre-loaded with seed data. All 7 users available in dropdown. Funnel visualization rendering.
- **The money moment:** Switch from Priya (28 nodes) to Vikram (74 nodes) to Suresh (298 nodes) in real time and watch the funnel visualization change. If the evaluator thinks "the same code, the same graph, completely different results based on who's asking," you've succeeded.
- **Surprise test:** We give you a new user profile. Your pipeline must handle it with ZERO code changes.
- **Questions we'll ask:** "Why are checks sequential, not parallel?" "What happens at 15,000 nodes?" "Show me a node Priya CAN'T see but Vikram CAN — why?" "What if someone bypasses the API and queries the database directly?"

---

## DEMO STRUCTURE (20-25 minutes)

1. **[2 min]** Architecture: DAG → BFS → Zone 2 → 5-Check → Candidate Set. Show the data flow diagram. Emphasize: ZERO LLM.
2. **[5 min]** Scenario 1: Full Priya pipeline. Narrate each check with numbers. Show the funnel. Show the candidate set.
3. **[4 min]** Scenario 2: Switch to Vikram. Show the count change. Highlight the 46 additional nodes Vikram sees. Explain WHY (lower ceiling, different entry point).
4. **[3 min]** Scenario 3: Silent exclusion. Show Priya's result looks complete — no indication of hidden nodes. Verify zero cross-department leakage.
5. **[3 min]** Scenario 4: Zone 2 demo. Toggle Zone 2 injection off → show missing drug safety nodes. Toggle on → they appear. The case for global injection.
6. **[3 min]** Your innovation — which problem from the thinking guide did you solve?
7. **[5 min]** Surprise user + scalability question + our questions

---

*Version: 1.0 | BRAHMO Core — Knowledge Infrastructure*
*Seed data, user profiles, DAG hierarchy, and setup instructions are in the separate Setup Guide document.*
