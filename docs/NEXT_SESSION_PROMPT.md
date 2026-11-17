# Prompt for the next Claude session

Copy everything inside the box below into a new Claude Code session opened on this folder
(`/Users/adeshpatankar/Downloads/PBL 5th Sem`).

---

```
You are continuing DebtScope, my PBL 5th-semester project. Today is my final day, so
prioritise what makes the live demo work and look clean. Read docs/PRD.md first — it is
the source of truth for users, flows, pages, APIs, status and remaining work.

## Where things stand
- Live: https://debtscope.onrender.com (Render, Docker, Postgres; auto-deploys on push)
- Repo: lazyasz/DebtScope, branch workstream/ws1-evidence-closeout. My GitHub (Adesh0512)
  has write access and is logged in via `gh`. Commit and push when a step is done.
- Backend: FastAPI in backend/ (tests: `.venv/bin/python -m pytest -q`, 187 passing).
  Frontend: React/Vite in frontend/ (`npm run build` → served by the backend).
- Local run: `.venv/bin/python -m uvicorn backend.main:app --port 8000`, then
  http://localhost:8000. Rebuild the frontend after UI changes.
- Done: Google sign-in (published, any account), personal workspaces, Get started screen,
  real data on Dashboard / Priorities / Hotspots / Risk Predictions, honest Jira/Notion
  dialogs, production refuses anonymous data access, Privacy/Terms pages.

## Rules (keep these)
1. No invented numbers anywhere. Missing data → "—" or a helpful empty state.
2. No fake success. Unconnected services must say "Simulated" / "Not connected".
3. Plain language. Page titles answer a question ("What to fix first"), no jargon
   (AST telemetry, SZZ, 5D matrix, version badges, "Sprint 48").
4. Simple UI: one primary action per page, clear empty states, readable by a non-engineer.
5. Verify every change in the browser pane (sign in with Google there) before committing.
6. Never type passwords, API keys or tokens into web forms, and don't ask me to paste
   secrets in chat. Open the right page in the browser pane and tell me exactly what
   to click and paste myself. Writing a key I give you into the local .env is fine.

## Tasks, in order
1. File details page (frontend/src/pages/FileIntelligence.jsx): remove fake values, wire to
   GET /files/{id} and POST /recommendations/ai-recipe; plain explanation of why the file
   ranks where it does.
2. Integrations page (frontend/src/pages/IntegrationsHub.jsx): ~10 fake actions. Show real
   connection status from GET /integrations/status; buttons either work or clearly say
   "Not connected — here's how to connect".
3. Dashboard hero: remove "DebtScope Telemetry Engine", "v4.18.2 · Active Mesh", the decorative
   radar; replace with a one-line plain summary and the Scan button.
4. AI Copilot: test a real question on the live site. If Gemini fails, show a clear
   "AI is busy, try again" message instead of an error dump.
5. Audit What-If Simulator and Data Quality pages with the same rules.
6. Jira (only if I want it): open https://www.atlassian.com/software/jira/free and
   https://id.atlassian.com/manage-profile/security/api-tokens in the browser pane, guide me,
   then I add JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN to Render → Environment.
7. Help me rotate keys that were exposed in chat (GitHub token, Notion key, Gemini key,
   Google client secret): open each page in the browser pane, I create the new value,
   I paste it into Render → Environment and local .env.
8. Final check on the live site following the demo script in docs/PRD.md §12, then update
   docs/PRD.md status tables and commit.

Start with task 1. Keep a task list, and after each task tell me in two lines what changed
and what's left.
```

---

## What you (Adesh) need to do yourself
These need your accounts or a decision, so Claude can only guide you:

| # | Task | Where | Time |
|---|---|---|---|
| 1 | Rotate keys pasted in chat: GitHub token, Notion key, Gemini key, Google client secret | GitHub settings · Notion Developer connections · AI Studio · Google Cloud → Clients | 10 min |
| 2 | Paste new keys into **Render → debtscope → Environment** and local `.env` | dashboard.render.com | 5 min |
| 3 | Decide on Jira; if yes, create a free Atlassian site + API token | atlassian.com | 10 min |
| 4 | Ask your guide about the Notion backlog database | — | — |
| 5 | Before the demo, open the live site 1 minute early (free tier wakes slowly) | debtscope.onrender.com | 1 min |
| 6 | Read Privacy/Terms pages; change the contact email if it shouldn't be Dhruv's | /privacy, /terms | 2 min |
