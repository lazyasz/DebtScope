# 🎯 DebtScope - Predictive Engineering Intelligence Platform

**DebtScope** is an enterprise-grade AI-powered codebase health and technical debt intelligence platform. It analyzes static code metrics, repository churn, test coverage, and architectural coupling to forecast refactoring debt, predict defect density, and optimize engineering velocity through machine learning.

---

## 🏗️ Architecture & Modules

The platform is organized into modular services:

- **`backend/`**: High-performance FastAPI server providing REST APIs for metric calculation, debt prioritization, risk quadrant mapping, and Google OAuth integration.
- **`frontend/`**: Interactive modern UI with real-time health dashboards, priority matrices, file intelligence breakdown, and trend analysis.
- **`ml_engine/`**: Machine learning models and training pipelines for technical debt regression, classification of high-risk components, and SHAP explainability.
- **`data_pipeline/`**: Extraction and processing pipelines for static analysis logs, AST parsing, and PySpark transformations.
- **`members/`**: Individual contributor modules, viva speaking notes, and specialized analysis logic.
- **`docs/`**: Comprehensive system specifications including API Contracts, Architecture Diagrams, Mathematical Formulas, ML Model Specifications, and Technical Viva Q&A.

---

## 🚀 Quick Start & Deployment Options

### Option A: 1-Click Production Stack (Docker Compose)
Spins up PostgreSQL 16, FastAPI backend with Alembic migrations, and React 19 / Nginx frontend in unified isolated containers:
```bash
docker compose up --build -d
```
* **Frontend Dashboard**: `http://localhost:5173`
* **FastAPI Swagger Docs**: `http://localhost:8000/docs`
* **Health Check**: `http://localhost:8000/health`

### Option B: Local Development

#### Backend (FastAPI & Background Worker)
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Run database migrations
python -m alembic upgrade head

# 3. Start server
uvicorn backend.main:app --reload --port 8000
```

#### Frontend (React 19 / Vite / Tailwind)
```bash
cd frontend
npm install
npm run dev
```

---

## 🌿 Branching Architecture & Safety Model

- **`main`**: Protected baseline branch containing the original demo version. This branch remains untouched and provides a guaranteed fallback for live demonstrations.
- **`advancements`**: Full-scale multi-tenant enterprise intelligence platform featuring:
  - **Phase 1**: PostgreSQL + Alembic multi-tenancy, workspace isolation, Google OAuth & secure httpOnly session cookies.
  - **Phase 2**: Sandboxed blobless git cloner, SSRF prevention, multi-language `lizard` AST analysis, commit churn mining, and developer concentration entropy (Bus Factor).
  - **Phase 3**: Real SZZ Apache 291k defect predictor model (`real_defect_predictor.pkl`), centralized 5D formula engine ($TR, BI, U, MC, DA$), and dynamic missing-dimension weight renormalization.
  - **Phase 3.5**: Grounded AI Copilot with tenant-scoped tool calling, AST-verified refactoring diffs, and 42-scenario automated benchmark suite (100% pass rate).
  - **Phase 4**: Atlassian Jira Cloud (OAuth 2.0 3LO) integration with commit regex parsing (`KEY-123`), customer impact/sprint urgency signal derivation, and sprint write-back ticket creation.
  - **Phase 5**: Notion Workspace integration with Service Criticality Tier ingestion into business rules and executive technical debt audit reporting.
  - **Phase 6**: Production containerization (Docker Compose), GitHub Actions CI/CD pipeline, and complete regression verification.

---

## 📑 Detailed Documentation
- [Roadmap & Implementation Plan](docs/ROADMAP.md)
- [Architecture Decisions (ADRs)](docs/DECISIONS.md)
- [External Credentials Setup Guide](docs/MANUAL_STEPS.md)
- [Copilot Evaluation Benchmark Report](docs/COPILOT_EVAL.md)
- [Architecture Master](docs/ARCHITECTURE_MASTER.md)
- [API Contract](docs/API_CONTRACT.md)
- [ML Model Specification](docs/ML_MODEL_SPECIFICATION.md)
- [Mathematical Formulas](docs/MATHEMATICAL_FORMULA.md)
- [Technical Viva Q&A Master](docs/TECHNICAL_VIVA_QA_MASTER.md)

