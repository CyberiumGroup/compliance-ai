# Compliance AI

An AI-driven multi-framework compliance assessment platform. Upload your controls and policies, run guided interviews, and receive explainable compliance scores with deviation tracking and risk-ranked remediation — all powered by Claude and OpenAI embeddings.

## Supported Frameworks

- **NIST CSF 2.0**
- **ISO/IEC 27001:2022**
- **SOC 2 Trust Services Criteria**
- **Custom frameworks** (upload your own)

## Key Capabilities

- **Cross-framework mappings** — AI generates and validates equivalence/partial/related mappings between frameworks, with a human approval workflow
- **Requirement clustering** — Semantically similar requirements are grouped to reduce interview burden (~65% reduction)
- **Guided interviews** — Deterministic question sequencing with branching logic and save/resume
- **Explainable scoring** — 0–4 scale with full explanation payloads for every score
- **Deviation detection** — Identifies gaps, classifies severity, and ranks by risk
- **Report generation** — JSON and PDF output
- **Audit logging** — Every state change and approval is recorded

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| Database | PostgreSQL 16 |
| AI | OpenAI GPT-4o (analysis & mapping), OpenAI text-embedding-3-small (embeddings) |
| PDF | WeasyPrint + Jinja2 |
| Auth | JWT (python-jose), bcrypt |

## Project Structure

```
compliance-ai/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/v1/          # REST endpoints
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (scoring, clustering, interviews, etc.)
│   │   ├── core/            # Config, AI client, permissions
│   │   └── data/            # Built-in framework data and question bank
│   ├── alembic/             # Database migrations
│   └── tests/
├── frontend/                # Next.js application
│   ├── app/                 # Pages (dashboard, assessments, frameworks, settings)
│   ├── components/          # React components organized by feature
│   └── lib/                 # API client, auth context, types
└── docker-compose.yml       # PostgreSQL database
```

## Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **Docker** (for PostgreSQL)

### 1. Start the database

```bash
docker-compose up -d
```

This starts PostgreSQL 16 on `localhost:5432` with database `compliance_ai`.

### 2. Backend setup

```bash
cd backend

# Create and configure environment variables
cp .env.example .env
# Edit .env and set your API key:
#   OPENAI_API_KEY  — required for AI features (chat completions and embeddings)

# Create a virtual environment and install
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload
```

The API will be available at **http://localhost:8000**.
Interactive API docs are at **http://localhost:8000/docs**.

### 3. Frontend setup

```bash
cd frontend

npm install
npm run dev
```

The frontend will be available at **http://localhost:3000**.

### Running Tests

```bash
cd backend
pytest
```

Tests use an in-memory SQLite database for isolation.

## Assessment Workflow

1. **Create an assessment** and select which frameworks are in scope
2. **Upload controls** (CSV/XLSX) and **policies** (PDF/DOCX/TXT/MD)
3. **Generate mappings** — AI maps your controls to framework requirements with confidence scores; reviewers approve or reject
4. **Run interviews** — guided question sessions with deterministic sequencing and branching logic
5. **Review scores** — each requirement receives a 0–4 score with an explanation payload
6. **Track deviations** — gaps are identified, classified by severity, and ranked by risk
7. **Generate reports** — export as JSON or PDF

## Notes

- **WeasyPrint** (PDF generation) requires system-level dependencies. On Windows you may need GTK3. See the [WeasyPrint installation docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).
- The database credentials default to `compliance`/`compliance` as configured in `docker-compose.yml` — change these for any non-local deployment.
- AI-generated crosswalk mappings with confidence > 0.9 are auto-approved; all others require human review.
