# DebtScope — Product Requirements Document

**Live app:** https://debtscope.onrender.com · **Repo:** `lazyasz/DebtScope`, branch `workstream/ws1-evidence-closeout`
**Status date:** 17 Nov 2026 · **Project:** PBL 5th Semester (academic)

---

## 1. Problem

Every software team accumulates technical debt — risky, hard-to-change code that slows delivery and causes bugs. Teams know it exists but cannot agree on **what to fix first**: engineers argue code quality, managers argue features, and the choice ends up a gut call.

## 2. Product in one line

**DebtScope scans a team's code, predicts which files are likely to cause bugs, weighs that against business importance, and gives a ranked, explained list of what to fix first.**

What makes it different from code-quality tools (e.g. SonarQube): it combines **code risk** with **business importance** (Notion service tiers, Jira bug history) into one priority score.

## 3. Users

| User | Needs | Main pages |
|---|---|---|
| Engineering lead / architect | Decide what to refactor this sprint | Dashboard, Priorities, File details |
| Engineering manager | See debt in plain terms; push work to Jira/Notion | Dashboard, Priorities, Integrations |
| Developer | Understand why a file is risky and how to fix it | File details, Hotspots, AI Copilot |
| Evaluator / guide | Try it with no setup | "Explore sample data" |

## 4. Goals and non-goals

**Goals**
1. A new user can sign in with Google and see ranked results for their own repo in under 2 minutes.
2. Every number on screen comes from the user's data or the real model — nothing invented.
3. Each user's data is private to their workspace.
4. Plain language: someone non-technical can read the Dashboard and know what to do.

**Non-goals (this release)**
- Paid plans, teams/invites, multiple workspaces per user
- Private-repo scanning via GitHub App
- Calibrated bug counts (scores are relative)

---

## 5. Core user flows

### Flow A — First visit
1. Open the site → **Sign in** page → **Continue with Google** (any Google account).
2. First sign-in creates the user's own empty workspace.
3. **Get started** screen shows 3 steps: *Scan a GitHub repository* · *Connect your tools* · *Explore sample data*.

### Flow B — Scan a repository
1. **Scan a repository** → paste a public GitHub URL → **Scan** (≈10–30 s).
2. Results summary (files, lines, risk, riskiest files) → **View Hotspots** or **Open Priorities**.
3. Dashboard switches from *Get started* to real numbers.

### Flow C — Decide what to fix
1. **Dashboard**: health score, quick wins, average defect risk, complex files, top 5 files.
2. **Priorities**: every file ranked by priority score, filter by quadrant (Quick Win / Strategic / Opportunistic / Deprioritised).
3. Click a file → **File details**: why it ranks there, metrics, recommended fix.

### Flow D — Act on it
- **Export to Jira** (one file or bulk) — creates real tickets in the user's own connected Jira project (picked from their projects; verified live: KAN-4); without a connection it clearly says *Simulated*.
- **Send to Notion** — adds one page per file to a database the user picks from their own connected Notion; without a connection it says *Simulated*.
- **File search** (header) — type part of a file name to jump to that file.
- **Ask AI** (Dashboard, Hotspots, File details) — opens the Copilot already asking how to fix that file.
- **AI Copilot** — ask "why is X ranked #1?" or "how do I fix X?" (Gemini).

### Flow E — Explore without a repo
**Explore sample data** → app shows the demo codebase with a purple bar *"You're viewing sample data · Back to my workspace"*.

---

## 6. Page map (simple navigation)

Sidebar, grouped by journey:

| Group | Page | Purpose (plain words) | Status |
|---|---|---|---|
| — | Sign in | Google sign-in | ✅ Done |
| Overview | **Dashboard** | "How healthy is my code and what's most urgent?" (or *Get started* when empty) | ✅ Real data |
| Analyze | **Priorities** | "What should I fix first?" ranked list + quadrant chart | ✅ Real data |
| Analyze | **Hotspots** | "Which files are both risky and important?" | ✅ Real data |
| Analyze | **Risk Predictions** | "Which files will likely break?" + honest model facts | ✅ Real data |
| Analyze | File details | One file: why it ranks here, metrics, debt items, fix recipe | ✅ Real data |
| Act | **AI Copilot** | Ask questions about the code | ✅ Live (answers from workspace data; falls back to gemini-flash-lite-latest when busy) |
| Act | What-If Simulator | "What if we clean up this file?" — real file metrics into the trained model | ✅ Done (fake TCO/PDF/treemap/PR-gate screens removed) |
| Workspace | **Integrations** | Real status of GitHub / Notion / Jira, one real action each, setup steps when not connected | ✅ Done |
| Workspace | Data Quality | Pipeline/data audit (labelled stored snapshot) | ✅ Fixed |
| Public | Privacy, Terms | Required by Google | ✅ Done |

### UI principles (apply to every page)
1. **Plain words first.** Titles say what the page answers ("What to fix first"), not jargon ("5D Payoff Matrix", "AST telemetry", "SZZ").
2. **No invented numbers.** If data is missing show "—" or an empty state that says what to do.
3. **No fake success.** Buttons that call an unconnected service must say *Simulated* / *Not connected*, never "Created!".
4. **One primary action per page**, at most 3 secondary.
5. **Empty states guide** the next step ("Scan a repository to fill this list").
6. Badges/labels only if they carry real information (remove "v4.18.2 · Active Mesh", "Sprint 48", etc.).

---

## 7. Page → API mapping

All APIs are under `/api/v1` (also `/api`) and need a signed-in session cookie unless noted.

| Page | API calls |
|---|---|
| Sign in | `GET /auth/google/login` → Google → `GET /auth/google/callback`; `GET /auth/me`; `POST /auth/logout` |
| Get started / Dashboard | `GET /repositories`, `GET /metrics/dashboard` (kpis, debt_categories, recent_high_priority) |
| Scan | `POST /repositories/scan {url}` (sync) · `POST /jobs/scan` (background) |
| Priorities | `GET /priorities?category=source\|test\|docs\|build\|all`, `GET /recommendations/sprint-plan` |
| Hotspots | `GET /hotspots` (now includes LOC, complexity, smells, duplication, churn) |
| Risk Predictions | `GET /predictions`, `GET /predictions/model-info`, `GET /priorities` |
| File details | `GET /files/{file_id}`, `POST /recommendations/ai-recipe` |
| Simulator | `POST /simulator/what-if` (real defect model on a chosen file) |
| Copilot | `/copilot/*` (conversations, chat) |
| Integrations | `GET /integrations/status`, `/integrations/{provider}/auth-url\|callback\|resources\|sync\|disconnect`, `POST /integrations/jira/create-issue`, `POST /integrations/jira/bulk-export`, `POST /integrations/notion/sync`, `POST /integrations/notion/ingest-criticality` |
| Public | `GET /health`, `/privacy`, `/terms` |

### Priority score (shown on Priorities)
`Priority = 35% Technical risk + 30% Business impact + 15% Release urgency + 10% Maintenance cost + 10% Debt age`, then a 15% effort blend. Quadrants: Quick Win (priority ≥ 60, effort ≤ 40), Strategic (≥ 60, > 40), Opportunistic (< 60, ≤ 40), Deprioritised (< 60, > 40).

### Defect model (shown on Risk Predictions — real values)
Random Forest regressor, 100 trees, 14 features, target = fault count, trained 15 Sep 2026. Test R² 0.41, cross-validated R² 0.40, MAE 4.74 (35% better than baseline), RMSE 15.7. Top features: author experience (42%), refactoring count (20%), file size (11%). Scores are **relative, uncalibrated**.

---

## 8. Integrations and keys

| Service | Used for | Status | Where the key lives |
|---|---|---|---|
| Google OAuth | Sign-in | ✅ Live, published (any Google account) | Render env + local `.env` |
| GitHub token | Repo scanning (5,000 req/h) | ✅ Live | Render env + `.env` |
| Notion API key + DB ID | Optional shared service-tier import (admin table) | ✅ Live | Render env + `.env` |
| Gemini API key | AI Copilot | ✅ Live (new key "DebtScope Copilot", Nov 17) | Render env + `.env` |
| GitHub OAuth app | Each user connects their own GitHub (GitHub shows its account chooser), lists their repos; private repos only with the user's own connection | ✅ Live (tested) | Render env `GITHUB_CLIENT_ID/SECRET` |
| Notion OAuth app | Each user connects their own Notion, lists their databases | ✅ Live (tested) | Render env `NOTION_CLIENT_ID/SECRET` |
| Jira OAuth app (Atlassian 3LO) | Each user connects their own Jira site, lists their projects | ✅ Live for any user (Atlassian app distribution: Sharing with anyone, Nov 18; tested on dhruvsakhare2006.atlassian.net, project KAN) | Render env `JIRA_CLIENT_ID/SECRET` |
| Render | Hosting + Postgres | ✅ Live (free tier: sleeps after ~15 min idle) | — |

---

## 9. Remaining work (priority order)

**Must (before demo)**
1. Keys pasted in chat were left as-is by the owner's decision (rotate them if the project is ever made public).
2. (Done) Integrations and Data Quality pages; in-app keys drawer removed (it overwrote server keys).
3. (Done) AI Copilot answers live; busy/invalid-key cases show a plain message.
4. (Done) Sidebar/scan-dialog jargon and fake "System Health 94.2%" removed; Executive PDF with invented dollar figures removed.

**Should**
5. (Done) GitHub, Notion and Jira connect per user; scans use the user's own GitHub (private repos); Jira export creates real tickets; Notion export adds real pages.
6. (Done) Full audit (Nov 17): removed fake badges, persona sign-in dialog, template recipes, illustrative formula and orphan Technical debt page; fixed a login redirect loop.
7. (Done) Simulator rebuilt on real data. Scans use the user's own GitHub connection (private repos), not yet tested on a private repo.
8. Store scan history so the Dashboard risk trend can show real data.

**Could**
9. Delete old test scans left in the demo workspace.
10. Background scans with progress for large repos.

---

## 10. Acceptance criteria

- [x] Any Google account can sign in on the live URL.
- [x] A new user sees *Get started*; after scanning, Dashboard shows that repo's numbers.
- [x] Two users never see each other's repositories.
- [x] Dashboard, Priorities, Hotspots, Risk Predictions show no hard-coded numbers.
- [x] Jira/Notion actions never claim success when not connected.
- [x] Dialogs open on screen; notifications don't crash the page.
- [x] In production, data APIs require sign-in (no anonymous demo access).
- [x] File details shows only real data, with a plain "why it ranks here" breakdown.
- [x] Integrations and Data Quality pass the audit; the in-app keys drawer is removed.
- [x] What-If Simulator passes the same audit.
- [x] AI Copilot answers on the live site.
- [ ] All pasted keys rotated.

## 11. Non-functional

- **Security:** data APIs return 401 without a session in production; CORS limited to the app origin; secrets only in env; production refuses to start with default secrets; OAuth state check; session in httpOnly cookie.
- **Privacy:** only Google name/email/picture; see `/privacy`.
- **Tests:** 189 backend tests (`.venv/bin/python -m pytest -q`).
- **Deploy:** push to the branch → Render auto-deploys (Docker; UI + API on one origin).

---

## 12. Viva demo script (5 minutes)

1. Open https://debtscope.onrender.com (open it 1 minute early — free tier wakes slowly).
2. **Continue with Google** → *Get started* screen → explain the 3 steps.
3. **Scan a repository** → `https://github.com/psf/requests` → show the result summary.
4. **Dashboard**: health 50/100, quick wins, average defect risk, complex files, top files.
5. **Priorities**: explain the 5-factor formula and quadrants; click a Quick Win.
6. **Hotspots**: highest-complexity file; churn honestly labelled *estimated*.
7. **Risk Predictions**: the real model facts (R² 0.41, top feature author experience) — say plainly the scores are relative.
8. **Export to Jira** → pick the KAN project → **Create ticket** → opens the real ticket in Jira.
9. Close with: what's unique (code risk × business impact) and what's next (§9).
