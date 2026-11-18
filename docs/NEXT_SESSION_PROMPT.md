# Continue DebtScope on another device (or with another AI)

## 1. Get the code

The code lives on GitHub at **`lazyasz/DebtScope`** (owner: lazyasz / Dhruv), branch
**`workstream/ws1-evidence-closeout`**. Adesh's account (`Adesh0512`) has write access.

```bash
git clone https://github.com/lazyasz/DebtScope.git
cd DebtScope
git checkout workstream/ws1-evidence-closeout
```

Pushing: sign in to GitHub as Adesh0512 on the new device (`gh auth login`), or ask lazyasz to add
the new account as a collaborator.

## 2. Set up locally

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && VITE_API_BASE_URL= npm run build && cd ..
cp .env.example .env      # then fill in values (see below)
.venv/bin/python -m uvicorn backend.main:app --port 8000     # open http://localhost:8000
```

- `.env` is **not** in git (it holds secrets). Copy the values from **Render → debtscope →
  Environment** (dashboard.render.com) or from the old laptop's `.env`. Never commit it or paste it in chat.
- Without a Google sign-in set up locally, start with `DEV_SANDBOX_AUTH=True` to log in as a demo user.
- Tests: `DEV_SANDBOX_AUTH=True .venv/bin/python -m pytest -q` (188 passing).
- Build the frontend with `VITE_API_BASE_URL=` (empty) so it calls the same server it is served from.

## 3. Where things stand (Nov 18, 2026)

- **Live:** https://debtscope.onrender.com (Render free tier, Docker, Postgres). Every push to the
  branch auto-deploys in ~5 min. The free server sleeps after ~15 min idle (first load ~1 min).
- **Works live, checked as a brand-new user:** Google sign-in for any account, own workspace,
  Get started screen, sample data, Dashboard, Priorities, Hotspots, Risk Predictions, File details,
  What-If Simulator (real model), AI Copilot (Gemini), About the model, file search, phone layout.
- **Integrations (each user connects their own accounts):**
  - GitHub: GitHub asks which account to use; lists the user's repos; scans with their token
    (private repos need their own connection; the server token is refused for private repos).
  - Jira: lists the user's projects; Export to Jira creates real tickets (tested: KAN-4…KAN-10).
  - Notion: lists the user's databases; Send to Notion adds pages. Needs a normal database shared
    with the DebtScope connection (Notion's special "People" database refuses new rows).
- Docs: `docs/PRD.md` is the source of truth for users, flows, pages, APIs and status.

## 4. Rules (keep these)

1. No invented numbers anywhere. Missing data → "—" or a helpful empty state.
2. No fake success. Unconnected services must say "Simulated" / "Not connected".
3. Plain language, simple UI, readable by a non-engineer.
4. Verify every change in a browser before committing; run the tests.
5. Never put API keys or passwords into git, web forms or chat.

## 5. Open items

1. Show Send to Notion working with a normal Notion database.
2. Test scanning a private repo with a connected GitHub account.
3. Optional: keys pasted in chat earlier were never rotated (owner's decision).

## Prompt to paste into the new AI session

```
You are continuing DebtScope, a PBL 5th-semester project (FastAPI + React, live on Render).
Read docs/NEXT_SESSION_PROMPT.md and docs/PRD.md first, follow the rules in section 4,
then work on the open items in section 5. Commit and push to branch
workstream/ws1-evidence-closeout when each step is done and verified.
```
