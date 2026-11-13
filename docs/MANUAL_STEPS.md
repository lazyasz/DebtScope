# DebtScope Manual Steps & External Credentials Guide

> [!IMPORTANT] Active Status: External Credentials Still Missing Prior to Live Production Launch
> As planned, the platform is currently operating in verified sandbox/simulation modes (`DEV_SANDBOX_AUTH=True`, `JIRA_SIMULATION_MODE=True`, `NOTION_SIMULATION_MODE=True`, `DeterministicMockCopilotAdapter`). The following credentials must be populated before enabling live production operations:
>
> | Integration | Required Environment Variables | Status | Pending Owner Action |
> | :--- | :--- | :---: | :--- |
> | **GitHub Access** | `GITHUB_TOKEN` (Personal Token) OR `GITHUB_APP_ID`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_PRIVATE_KEY_PATH` | ⏳ PENDING | Teammate manual generation (needed for private repository scanning and higher rate limits) |
> | **Google OAuth 2.0** | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | ⏳ PENDING | Google Cloud Console project OAuth Client ID creation |
> | **Atlassian Jira Cloud** | `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`, `JIRA_REDIRECT_URI` | ⏳ PENDING | Atlassian Developer Console 3LO app creation |
> | **Notion Integration** | `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET` (or `NOTION_API_KEY`) | ⏳ PENDING | Notion Developer Portal integration creation |
> | **AI Copilot LLM** | `GEMINI_API_KEY` (or `ANTHROPIC_API_KEY`), `COPILOT_LLM_PROVIDER` | ⏳ PENDING | Google AI Studio or Anthropic Console API key generation |

---

## 🛠️ Prerequisites, Environment Modes & Local HTTPS Tunnel

> [!WARNING] Fail-Closed Environment Configuration: Local Development Requires `ENVIRONMENT=development`
> DebtScope operates under a strict **fail-closed** architecture:
> - By default, the application runs in `ENVIRONMENT=production`.
> - In `production`, startup **refuses to run** (`RuntimeError`) if `SECRET_KEY`, `JWT_SECRET`, or `TOKEN_ENCRYPTION_KEY` are unset, empty, or left as default placeholders, or if any sandbox/simulation flags are enabled.
> - **For local engineering and testing**, you MUST explicitly specify `ENVIRONMENT=development` in your local `.env` file. This permits local sandbox auth, mock services, and dev convenience defaults.

OAuth providers (especially Google and Atlassian) require public HTTPS endpoints or strict localhost URIs for OAuth callbacks. For local development on Windows, we use the pre-staged `cloudflared.exe` located in the repository root.

### Starting the Cloudflare Tunnel:
Run the following in PowerShell from the repository root:
```powershell
.\cloudflared.exe tunnel --url http://localhost:8000
```
`cloudflared` will print a public HTTPS URL (e.g. `https://your-random-subdomain.trycloudflare.com`).  
Use this base URL wherever **`{TUNNEL_HTTPS_BASE}`** appears below.

---

## 1. Google OAuth 2.0 & OIDC Setup

### Purpose
Enables users to sign in with their Google corporate or personal accounts, automatically provisioning user and workspace accounts.

### Step-by-Step Instructions:
1. Navigate to the **[Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials)**.
2. Select your Google Cloud Project (or create a new project named `DebtScope`).
3. Click **Configure Consent Screen** (if not already done):
   - User Type: **External**
   - App Name: `DebtScope Intelligence`
   - User support email: Select your email
   - Developer contact email: Enter your email
   - Scopes: Click **Add or Remove Scopes** and select:
     - `.../auth/userinfo.email`
     - `.../auth/userinfo.profile`
     - `openid`
   - Save and continue to Summary.
4. Return to **Credentials** -> Click **+ CREATE CREDENTIALS** -> Select **OAuth client ID**.
5. Fill in the form:
   - **Application type**: `Web application`
   - **Name**: `DebtScope Web Client`
   - **Authorized JavaScript origins**:
     - `http://localhost:5173`
     - `http://localhost:8000`
     - `{TUNNEL_HTTPS_BASE}`
   - **Authorized redirect URIs**:
     - `http://localhost:8000/api/v1/auth/google/callback`
     - `http://localhost:5173/auth/callback`
     - `{TUNNEL_HTTPS_BASE}/api/v1/auth/google/callback`
6. Click **CREATE**. A modal will display your **Client ID** and **Client Secret**.

### `.env` Variables:
```env
GOOGLE_CLIENT_ID="<your-google-client-id>.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="<your-google-client-secret>"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"
```

---

## 2. GitHub App / Server Token Setup

### Purpose
Allows DebtScope to clone and analyze public repositories without aggressive rate limits (raising limits from 60 to 5,000 req/hr) and access private repositories with read-only permissions.

### Option A: Personal Access Token (Fastest for initial dev & public repos)
1. Go to **[GitHub Personal Access Tokens (Classic)](https://github.com/settings/tokens)**.
2. Click **Generate new token (classic)**.
3. Note: `DebtScope Scanner`
4. Expiration: 90 days.
5. Scopes: `repo` (for private repos) or `public_repo` (for public repos only).
6. Click **Generate token** and copy the token.

### Option B: GitHub App (Target Architecture for Multi-Tenant Organizations)
1. Navigate to **[GitHub Developer Settings — GitHub Apps](https://github.com/settings/apps)**.
2. Click **New GitHub App**.
3. Fill in:
   - **GitHub App name**: `DebtScope Intelligence Platform`
   - **Homepage URL**: `http://localhost:5173`
   - **Callback URL**: `http://localhost:8000/api/v1/integrations/github/callback`
   - **Webhook**: Uncheck "Active" for local dev, or provide `{TUNNEL_HTTPS_BASE}/api/v1/integrations/github/webhook`.
4. **Permissions** (Strict Least-Privilege):
   - **Repository permissions**:
     - **Contents**: `Read-only` (to inspect files and git trees)
     - **Metadata**: `Read-only` (mandatory for repo info)
     - **Pull requests**: `Read-only` (for PR risk gating)
     - **Issues**: `Read-only` (for defect correlation)
5. Under "Where can this GitHub App be installed?", select: **Any account**.
6. Click **Create GitHub App**.
7. Note the **App ID** and **Client ID**.
8. Generate a **Client Secret** and copy it.
9. Scroll down to **Private keys** -> Click **Generate a private key** (saves a `.pem` file).

### `.env` Variables:
```env
GITHUB_TOKEN="<paste-your-github-personal-access-token-here>" # For Option A
GITHUB_APP_ID="123456"                                        # For Option B
GITHUB_CLIENT_ID="<paste-your-github-app-client-id>"
GITHUB_CLIENT_SECRET="<paste-your-github-app-client-secret>"
GITHUB_PRIVATE_KEY_PATH="backend/secrets/github-app.private-key.pem"
```

---

## 3. Atlassian Developer Console (Jira Cloud 3LO)

### Purpose
Connects to Jira Cloud to link commits to tickets (`KEY-123`), compute business criticality from bug priorities, evaluate sprint urgency, and write back technical debt tasks.

### Step-by-Step Instructions:
1. Navigate to the **[Atlassian Developer Console](https://developer.atlassian.com/console/myapps/)**.
2. Click **Create** -> Select **OAuth 2.0 (3LO) integration**.
3. Name: `DebtScope Platform` -> Click **Create**.
4. In the left sidebar, click **Permissions**:
   - Under **Jira API**, click **Add**.
   - Click **Configure** next to Jira API.
   - Add the following scopes:
     - `read:jira-work` (read issues, projects, fixVersions)
     - `read:jira-user` (read author details)
     - `write:jira-work` (create refactoring tasks in active sprints)
     - `offline_access` (obtain refresh tokens for background sync)
5. In the left sidebar, click **Authorization**:
   - Click **Add** next to OAuth 2.0 (3LO).
   - Enter Callback URL:
     - `http://localhost:8000/api/v1/integrations/jira/callback`
     - `http://localhost:5173/auth/callback`
     - `{TUNNEL_HTTPS_BASE}/api/v1/integrations/jira/callback`
   - Click **Save changes**.
6. In the left sidebar, click **Settings**:
   - Copy **Client ID** and **Secret**.

### `.env` Variables:
```env
JIRA_CLIENT_ID="<your-atlassian-client-id>"
JIRA_CLIENT_SECRET="<your-atlassian-client-secret>"
JIRA_REDIRECT_URI="http://localhost:8000/api/v1/integrations/jira/callback"
```

---

## 4. Notion Integration Setup

### Purpose
Allows DebtScope to ingest team service criticality definitions and export prioritization reports directly into the team's Notion workspace.

### Step-by-Step Instructions:
1. Navigate to the **[Notion Developers Portal — My Integrations](https://www.notion.so/profile/integrations)**.
2. Click **+ New integration**.
3. Fill in:
   - **Type**: Public (for multi-tenant OAuth) or Internal (for personal workspace).
   - **Name**: `DebtScope Technical Debt Intelligence`
   - **Associated workspace**: Select your workspace.
4. Under **Capabilities**:
   - Read content: `Checked`
   - Update content: `Checked`
   - Insert content: `Checked`
   - User capabilities: `No user information`
5. If public:
   - Redirect URI:
     - `http://localhost:8000/api/v1/integrations/notion/callback`
     - `http://localhost:5173/auth/callback`
6. Click **Submit**.
7. Copy the **Internal Integration Secret** (or OAuth Client ID & Secret).

### Notion "Service Criticality" Database Template Schema:
When testing the Notion ingestion feature, create a database in your Notion workspace with the following columns:
| Property Name | Property Type | Expected Values |
| :--- | :--- | :--- |
| **Service Name** | Title | e.g., `payment-service`, `auth-service` |
| **Path Pattern** | Text | e.g., `services/payment/**`, `auth/**` |
| **Criticality Tier**| Select | `Tier-1 (Core Revenue)`, `Tier-2`, `Tier-3 (Internal)` |
| **Business Impact** | Number (0–100) | `95`, `70`, `30` |
| **SLA Uptime Target**| Text | `99.99%`, `99.9%` |

### `.env` Variables:
```env
NOTION_CLIENT_ID="<your-notion-client-id>"
NOTION_CLIENT_SECRET="<your-notion-client-secret>"
NOTION_REDIRECT_URI="http://localhost:8000/api/v1/integrations/notion/callback"
NOTION_API_KEY="<paste-your-notion-api-key-here>" # For internal testing
```

---

## 5. Security Encryption & Database Secrets

Generate a cryptographically secure encryption key for token storage and session signing.

In PowerShell:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copy the output into `TOKEN_ENCRYPTION_KEY`.

In PowerShell:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output into `SECRET_KEY`.

### `.env` Variables:
```env
# Encryption & Secrets
SECRET_KEY="<generated-64-character-hex-string>"
TOKEN_ENCRYPTION_KEY="<generated-fernet-key>"

# PostgreSQL Database (Docker Compose default)
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/debtscope_db"
```

---

## 6. AI Copilot LLM Provider Setup (Phase 3.5)

### Purpose
Powers the interactive Grounded AI Engineering Copilot (`POST /api/v1/copilot/chat`) with streaming tool calling against real codebase metrics and AST refactoring diffs. No fine-tuning is required. We use a provider-agnostic interface supporting Google Gemini and Anthropic Claude.

### Option A: Google Gemini (Recommended — Gemini 1.5 Flash / Pro)
1. Navigate to **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Sign in with your Google account.
3. Click **Create API key** -> select or create a Google Cloud project.
4. Copy the generated key.

### Option B: Anthropic Claude (Claude 3.5 Sonnet)
1. Navigate to the **[Anthropic Console](https://console.anthropic.com/)**.
2. Sign in or create an account.
3. Go to **Settings** -> **API Keys**.
4. Click **Create Key**, name it `DebtScope Copilot`, and copy the key (`sk-ant-...`).

### `.env` Variables:
```env
# Provider selector: 'gemini' (default) or 'claude'
COPILOT_LLM_PROVIDER=gemini

# Google Gemini API Key (Option A)
GEMINI_API_KEY="<paste-your-gemini-api-key-here>"

# Anthropic Claude API Key (Option B)
ANTHROPIC_API_KEY="<paste-your-anthropic-api-key-here>"
```

