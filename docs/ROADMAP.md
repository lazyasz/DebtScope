# DebtScope Product Roadmap: Seeded Demo to Multi-Tenant Engineering Intelligence Platform

This roadmap defines the iterative transformation of DebtScope from a static, seeded prototype into an enterprise-grade, multi-tenant technical debt intelligence SaaS.

---

## Phase Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ P0: Audit, Findings & Architectural Alignment (Current)                                          │
│     Investigate discrepancies, data leakage, missing inputs, and author roadmap/decisions docs.   │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ P1: Core Foundation & Multi-Tenancy                                                              │
│     Postgres + Alembic, Users/Workspaces/Memberships, Google OAuth + HTTP-only cookies,          │
│     Tenant-scoping queries, Demo Workspace isolation.                                             │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ P2: Real Repository Ingestion & Mining Worker                                                    │
│     Background DB-backed jobs, GitHub App & clone worker, Git history mining, multi-language     │
│     lizard AST analysis, provenance tagging, dynamic confidence scoring.                         │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ P3: Real-Data Scoring & Single Source of Truth                                                   │
│     ML integration with real SZZ defect predictor, Business Rules engine, formula single         │
│     source of truth, elimination of frontend silent fallbacks, honest confidence UI.            │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ P4: Atlassian Jira Integration (3LO)                                                             │
│     OAuth 2.0 3LO token lifecycle, issue-to-commit linking, Jira-derived customer impact and      │
│     urgency, two-way ticket write-back for priority items.                                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ P5: Notion Integration & Executive Reporting                                                     │
│     OAuth 2.0 integration, "Service Criticality" database ingestion, bi-directional export of    │
│     refactoring reports and sprint debt matrices.                                                │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ P6: Production Hardening, Verification & Deployment                                              │
│     Docker Compose orchestration, CI pipelines, security audits, verification on 3 real-world    │
│     repositories (pallets/flask, frontend React/TS repo, private repo), updated docs.             │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Phase Breakdown

### Phase 0: Audit, Findings & Architectural Alignment
* **Goal**: Document all systemic code-to-doc discrepancies, data leakage in ML training, input fabrications, and establish baseline ADRs and manual credential workflows.
* **Tasks**:
  1. Complete code audit across `backend/services/priority_service.py`, `ml_engine/src/model_trainer.py`, `backend/services/repo_scanner_service.py`, and `frontend/src/charts/PriorityMatrix.jsx`.
  2. Create [docs/ROADMAP.md](file:///c:/Users/dhruv/.gemini/antigravity-ide/scratch/DebtScope/docs/ROADMAP.md) detailing tasks, dependencies, and definitions of done.
  3. Create [docs/DECISIONS.md](file:///c:/Users/dhruv/.gemini/antigravity-ide/scratch/DebtScope/docs/DECISIONS.md) detailing ADRs for multi-tenancy, ML scoring, formula centralization, and security.
  4. Create [docs/MANUAL_STEPS.md](file:///c:/Users/dhruv/.gemini/antigravity-ide/scratch/DebtScope/docs/MANUAL_STEPS.md) listing all required external console registrations and credentials.
  5. Formulate open questions requiring user decisions before code modifications begin.
* **Definition of Done**:
  - All 5 problem areas documented with exact code citations.
  - Three master documentation files authored in `docs/`.
  - Zero application code modified in Phase 0.
  - User sign-off obtained on open architectural decisions.

---

### Phase 1: Core Foundation, Multi-Tenancy & Authentication
* **Branch**: `feat/p1-foundation`
* **Goal**: Introduce PostgreSQL, Alembic migrations, tenant isolation, and Google OAuth 2.0 authentication while preserving the original seeded data within a sandboxed "Demo Workspace".
* **Tasks**:
  1. **Database & Migrations**:
     - Configure PostgreSQL engine support in `backend/database/connection.py` while retaining SQLite compatibility for rapid unit test suites.
     - Initialize Alembic (`backend/alembic/`) with automated revision generation.
     - Create initial baseline migration for existing tables.
  2. **Multi-Tenant Schema**:
     - Create `users`, `workspaces`, and `workspace_memberships` tables.
     - Add `workspace_id` foreign key column across all tenant data tables (`repositories`, `source_files`, `engineering_metrics`, `ml_predictions`, `business_contexts`, `priority_scores`, `technical_debt_items`, `recommendations`, `integration_connections`).
     - Build a centralized tenant-scoping query utility (`TenantQueryHelper` / scoped repository pattern) that enforces workspace tenancy boundaries.
  3. **Google Authentication & Secure Session**:
     - Implement verified Google ID Token exchange (`google-auth`) via authorization code flow.
     - Store session tokens in encrypted, `httpOnly`, `Secure`, `SameSite=Lax` cookies (no local storage token leakage).
     - Implement RBAC roles (`owner`, `admin`, `engineer`, `viewer`).
  4. **Demo Workspace Sandbox**:
     - Migrate `seed_service.py` to populate a dedicated system workspace (`workspace_slug="demo"`).
     - Seed data is read-only for demo users; newly registered users land in their own isolated personal/team workspace.
  5. **Automated Tenant Boundary Tests**:
     - Add tests verifying that User A (Workspace 1) cannot read, update, or delete repositories belonging to User B (Workspace 2).
* **Definition of Done**:
  - PostgreSQL container runs and passes all Alembic migrations (`alembic upgrade head`).
  - Google login creates user and workspace records; returns secure session cookie.
  - Test suite passes with 100% tenant boundary isolation tests.
  - Demo workspace accessible as an explicit mode, not default state.
* **Verification & Demo Script**:
  ```bash
  # 1. Run migrations
  alembic upgrade head
  # 2. Run multi-tenancy isolation test suite
  pytest backend/tests/test_multi_tenancy.py backend/tests/test_auth_security.py -v
  # 3. Verify server startup
  uvicorn backend.main:app --reload --port 8000
  ```

---

### Phase 2: Real Repository Ingestion & Mining Worker
* **Branch**: `feat/p2-real-analysis`
* **Goal**: Replace superficial REST tree parsing and fabricated metrics with a sandboxed background analysis worker that performs partial git cloning, commit history mining, and multi-language AST complexity analysis.
* **Tasks**:
  1. **Background Job Orchestration**:
     - Add `analysis_jobs` table (`id`, `workspace_id`, `repository_id`, `status` [QUEUED, CLONING, ANALYZING, MINING, COMPLETED, FAILED], `progress_pct`, `stage`, `error_message`, `created_at`, `completed_at`).
     - Implement an asynchronous, DB-backed worker loop (in-process `asyncio` worker for dev/tests, standalone process for prod).
     - Add job status endpoint (`GET /api/v1/jobs/{job_id}`) and cancellation support.
  2. **Sandboxed Cloning & Security**:
     - Implement shallow/blobless git clone (`git clone --filter=blob:none --no-checkout`) in secure OS temporary directories.
     - Enforce security controls: SSRF URL validation (block `127.0.0.1`, RFC1918 private IPs, AWS metadata `169.254.169.254`), maximum repository size cap (e.g. 500 MB), and hard execution timeout (e.g. 5 minutes).
     - Enforce zero code execution: absolute ban on running `eval()`, build scripts, or test runners on analyzed targets.
     - Clean up temporary clone directories in `finally` blocks.
  3. **Git History Mining**:
     - Extract real per-file commit churn, additions, deletions, and total revisions.
     - Compute author commit entropy to evaluate developer concentration (**Bus Factor**).
     - Calculate debt age from commit timestamps rather than hardcoded 60/90-day defaults.
  4. **Multi-Language AST Analysis**:
     - Integrate `lizard` or `tree-sitter` for robust cyclomatic complexity, cognitive complexity, and LOC across Python, JavaScript, TypeScript, Java, Go, C++, and C#.
     - Retain lexical Python AST parsing for specific code smell detection.
  5. **Test Coverage & Dependency Risk Ingestion**:
     - Inspect repository root for coverage artifacts (`coverage.xml`, `lcov.info`, `.coverage`, `jacoco.xml`).
     - If coverage artifacts exist, extract exact measured coverage.
     - If missing, calculate test file ratio (`test_files_count / total_files_count`), tag metric provenance as `ESTIMATED`, and penalize confidence score.
  6. **Metric Provenance & Confidence Calculation**:
     - Add `provenance` metadata to each metric record: `MEASURED`, `ESTIMATED`, `USER_RULE`, `DEFAULT`.
     - Compute composite confidence score ($0.0 - 1.0$) reflecting input completeness.
* **Definition of Done**:
  - Scanning a public repository (e.g., `pallets/flask`) executes via background worker without blocking HTTP requests.
  - Git history mining produces verified non-zero churn and author distribution.
  - Provenance flags and confidence ratings attached to all records.
  - Zero temporary clone directories left on disk after completion or failure.
* **Verification & Demo Script**:
  ```bash
  # 1. Trigger background scan of public repo
  curl -X POST http://localhost:8000/api/v1/repositories/scan -H "Content-Type: application/json" -d '{"url":"https://github.com/pallets/flask"}'
  # 2. Poll job status
  curl http://localhost:8000/api/v1/jobs/<job_id>
  # 3. Verify extracted metrics and provenance
  pytest backend/tests/test_worker_mining.py -v
  ```

---

### Phase 3: Real-Data Scoring & Single Source of Truth
* **Branch**: `feat/p3-scoring-real-data`
* **Goal**: Retire the synthetic data-leaked regressor, deploy the real SZZ-trained defect model behind a versioned interface, centralize formula weights and quadrant thresholds into a single configuration source of truth, and overhaul the UI to show honest metrics without silent mock fallbacks.
* **Tasks**:
  1. **ML Model Alignment & Versioned Inference**:
     - Relabel `rf_defect_model.pkl` in UI and documentation as `Synthetic Heuristic Risk Index (v1.0-legacy)`.
     - Standardize primary defect forecasting on `real_defect_predictor.pkl` (trained on 291k real SZZ Apache records).
     - Map mined git features (`lines_added`, `lines_removed`, `churn`, `loc`, `is_test`, `author_experience_commits`) into the 14-feature vector.
     - Wrap models in an abstract `DefectPredictorInterface` with graceful fallback when optional features are missing.
  2. **Single Source of Truth Formula Engine**:
     - Consolidate all mathematical formulas, weights, and quadrant thresholds into `backend/config.py` and `backend/services/priority_service.py`.
     - Standardize quadrant thresholds:
       * **QUICK WIN**: $PS_{base} \ge 60.0$ and $Effort \le 40.0$
       * **STRATEGIC REFACTOR**: $PS_{base} \ge 60.0$ and $Effort > 40.0$
       * **OPPORTUNISTIC**: $PS_{base} < 60.0$ and $Effort \le 40.0$
       * **DEPRIORITIZED**: $PS_{base} < 60.0$ and $Effort > 40.0$
     - Provide dynamic weight renormalization for $TR_{static}$ when specific inputs (e.g., test coverage) are absent.
  3. **User-Configurable Business Rules Engine**:
     - Build path-pattern rule evaluator (e.g., `services/payment/**` $\rightarrow BusinessCriticality=95$, `scripts/**` $\rightarrow BusinessCriticality=20$).
     - Allow engineers to define and tune domain rules per workspace.
  4. **Frontend Overhaul & Fallback Removal**:
     - Remove silent `try...catch` fallback to `mockApi.js` in `frontend/src/services/api.js`.
     - Implement explicit error boundaries and banner notifications when backend communication fails.
     - Update `PriorityMatrix.jsx` to render $0-100$ scale for both axes ($PS_{base}$ Y-axis, $Effort$ X-axis) and display confidence badges per data point.
     - Implement route-level code splitting (`React.lazy` + `Suspense`) to eliminate Vite chunk size warnings.
* **Definition of Done**:
  - Formulas, weights, and quadrant boundaries identical across backend, frontend tooltips, and documentation.
  - Real defect predictor executes against real mined git vectors with zero synthetic feature injection.
  - Frontend fails loudly and clearly when backend is offline, reserving mock data exclusively for the "Demo Workspace".
  - Frontend bundle split into lazy-loaded route chunks under 400 kB each.
* **Verification & Demo Script**:
  ```bash
  # 1. Run scoring formula and ML integration tests
  pytest backend/tests/test_priority_engine.py ml_engine/tests/test_ml_pipeline.py -v
  # 2. Run frontend build and verify chunk optimization
  npm --prefix frontend run build
  ```

---

### Phase 4: Atlassian Jira Cloud Integration (OAuth 2.0 3LO)
* **Branch**: `feat/p4-jira-integration`
* **Goal**: Implement authentic Atlassian 3LO OAuth, link Jira issues to codebase files via commit message parsing (`KEY-123`), compute business signals from live ticket telemetry, and enable two-way ticket creation.
* **Tasks**:
  1. **Atlassian OAuth 2.0 (3LO)**:
     - Implement Authorization Code Flow with PKCE against `auth.atlassian.com`.
     - Store encrypted `access_token` and `refresh_token` with automated token refresh.
     - Scopes: `read:jira-work`, `read:jira-user`, `write:jira-work`, `offline_access`.
  2. **Commit-to-Issue Linking Engine**:
     - Parse git commit logs for regex matches against Jira project keys (e.g. `[A-Z][A-Z0-9]+-\d+`).
     - Query Jira REST API v3 for linked issue statuses, priority levels, bug flags, and sprint associations.
  3. **Dynamic Business Signal Derivation**:
     - **Customer Impact**: Derived from linked open bug counts and ticket priorities (`Highest` $\rightarrow 90$, `High` $\rightarrow 75$, `Medium` $\rightarrow 50$).
     - **Sprint Urgency**: Derived from active sprint assignment (`customfield` sprint state == `ACTIVE` $\rightarrow 90$).
     - **Release Proximity**: Calculated from `fixVersions` release milestone target dates.
  4. **Write-Back Ticket Creation**:
     - Allow engineers to select high-priority Quick Wins or Strategic Refactors in the UI and click "Export to Jira".
     - Generate structured Jira tasks/bugs with automated description containing cyclomatic complexity, risk score, and refactoring recommendations.
* **Definition of Done**:
  - Authenticated Atlassian connection successfully exchanges tokens and handles refresh expiry.
  - Real Jira issues associated with files based on repository commit history.
  - Successfully creates a real Jira issue in an active sprint from the DebtScope UI.
* **Verification & Demo Script**:
  ```bash
  # 1. Run Jira provider tests
  pytest backend/tests/test_jira_provider.py -v
  # 2. Test OAuth flow and issue creation in mock/sandbox & live environments
  ```

---

### Phase 5: Notion Integration & Executive Reporting
* **Branch**: `feat/p5-notion-integration`
* **Goal**: Connect Notion via OAuth 2.0, ingest organizational service criticality definitions, and export comprehensive executive technical debt reports into a team's Notion workspace.
* **Tasks**:
  1. **Notion OAuth 2.0 & Token Storage**:
     - Implement public OAuth integration against Notion API v1 (`https://api.notion.com/v1/oauth/token`).
     - Store workspace credentials and bot access tokens securely.
  2. **Service Criticality Database Ingestion**:
     - Allow workspace admins to connect a Notion database defining service tiers (e.g., Service Name, SLA Tier, Revenue Dependency).
     - Automatically map Notion database entries to DebtScope repository business rules.
  3. **Bi-Directional Report Export**:
     - Build structured Markdown/Block converter for Notion API.
     - Export sprint technical debt summaries, top 10 debt items, ROI quadrants, and estimated maintenance savings directly into a designated Notion page.
* **Definition of Done**:
  - Live Notion OAuth connects and discovers user pages/databases.
  - Ingests service metadata into DebtScope business context table.
  - Exports formatted executive report into Notion with charts/table blocks.
* **Verification & Demo Script**:
  ```bash
  # 1. Run Notion integration test suite
  pytest backend/tests/test_notion_provider.py -v
  ```

---

### Phase 6: Production Hardening, Verification & Final Deployment
* **Branch**: `feat/p6-hardening`
* **Goal**: Deliver a production-ready system with Docker Compose, automated CI/CD checks, comprehensive end-to-end test verification on 3 real repositories, and updated documentation.
* **Tasks**:
  1. **Containerization & Orchestration**:
     - Write optimized multi-stage `Dockerfile` for backend API and worker.
     - Write optimized `Dockerfile` for frontend with Nginx/static serving.
     - Author `docker-compose.yml` linking `postgres`, `api`, `worker`, and `frontend`.
     - Verify environment variable propagation and secret injection.
  2. **Continuous Integration**:
     - Create GitHub Actions workflow (`.github/workflows/ci.yml`) running backend linters (`ruff`), security scanners (`pip-audit`), test suites (`pytest`), and frontend builds (`npm run build`).
  3. **End-to-End Validation on 3 Real Repositories**:
     - **Repo 1 (Public Python)**: `pallets/flask` (verifies Python AST, git history mining, SZZ model scoring).
     - **Repo 2 (Public JS/TS)**: `facebook/react` or `expressjs/express` (verifies multi-language lizard parser, dependency analysis).
     - **Repo 3 (Private Repository)**: User-provided private GitHub repo via GitHub App token (verifies authenticated clone, private permissions, business rule matching).
  4. **Documentation & Viva Readiness**:
     - Update all root and member documentation to reflect the production platform.
     - Ensure academic formulas in `docs/MATHEMATICAL_FORMULA.md` and `members/` remain fully explainable for technical vivas.
* **Definition of Done**:
  - `docker compose up` spins up entire multi-tenant stack with zero manual steps.
  - CI pipeline green across all unit, integration, and lint checks.
  - 3 real-world repositories successfully scanned, analyzed, and prioritized with honest confidence ratings.
  - Final documentation and user guide completed.
* **Verification & Demo Script**:
  ```bash
  # 1. Spin up complete production environment
  docker compose up -d --build
  # 2. Run full regression test suite
  docker compose exec api pytest backend/tests/ -v
  # 3. Verify healthy system status
  curl http://localhost:8000/health
  ```
