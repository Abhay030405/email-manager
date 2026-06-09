# Autonomail — Autonomous Campaign Engine

An autonomous AI multi-agent system that plans, executes, and optimizes email marketing campaigns. Eight specialized AI agents collaborate through a directed LangGraph execution graph to parse campaign briefs, segment customers via real RFM clustering, generate strategy, create personalized email content via parallel fan-out, and execute campaigns — with a human-in-the-loop approval gate before any emails are sent.

**Live:** [https://autonomail.dev](https://autonomail.dev)

---

**Built by Abhay Agarwal**  
MNNIT Allahabad · Jhansi, Uttar Pradesh, India

| | |
|---|---|
| Email | [officialabhay030405@gmail.com](mailto:officialabhay030405@gmail.com) |
| Phone | [+91-8887752006](tel:+918887752006) |
| Portfolio | [itsabhay.me](https://itsabhay.me) |
| GitHub | [github.com/Abhay030405](https://github.com/Abhay030405) |

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [AI Agent Pipeline](#ai-agent-pipeline)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started (Local)](#getting-started-local)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)

---

## Architecture Overview

```
Next.js 14 Frontend (App Router + Shadcn/ui)
            ↓  REST API
FastAPI Backend (/api/v1/*)
            ↓  LangGraph orchestration
AI Agent Pipeline (LangChain + OpenRouter LLM)
            ↓  async Motor driver
MongoDB Atlas
            ↓  HTTP
Mock Campaign API (email execution)
```

### How it works

1. User fills a multi-step form describing their product, audience, and goals
2. Frontend POSTs to `POST /api/v1/campaigns` to persist the brief, then calls `POST /api/v1/campaigns/{id}/start`
3. The backend fires an `asyncio.create_task` — the LangGraph pipeline runs in the background
4. Frontend polls `GET /api/v1/campaigns/{id}/status` every 4 seconds, showing a live progress tracker
5. Pipeline pauses at the approval node (`PENDING_APPROVAL`) — a human reviews and approves/rejects
6. On approval, execution resumes and emails are sent via the Mock Campaign API

---

## AI Agent Pipeline

LangGraph `StateGraph` with 6 nodes:

```
parse_brief → segmentation → strategy → content_generation → approval → execution
                                                                  ↑
                                                        wait_approval (loop)
```

| Node | Agent | What it does |
|------|-------|-------------|
| `parse_brief` | Brief Parser | Extracts product details, target audience, objective, and preferences from the natural language brief |
| `segmentation` | Segmentation Agent | Fetches customer cohort, groups into micro-segments with priority scores and recommended messaging approaches |
| `strategy` | Strategy Agent | Produces targeting strategy, send-time plan, and A/B variant structure for each segment |
| `content_generation` | Content Gen Agent | Generates personalized email subject lines and bodies per segment variant |
| `approval` | Approval Coordinator | Sets status to `PENDING_APPROVAL` and pauses the graph — waits for human review |
| `execution` | Execution Agent | Schedules and sends campaigns via the Mock Campaign API, records variant IDs |

All nodes run through `_execute_node_with_retries` which writes `current_step` to MongoDB on entry and retries on failure (up to 3 attempts with exponential backoff).

---

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| Python 3.11 | Language |
| FastAPI | REST API |
| Pydantic v2 + pydantic-settings | Validation & config |
| LangChain + LangGraph | Agent framework & orchestration |
| OpenRouter → Google Gemini 2.5 Flash Lite | LLM |
| Motor (async) | MongoDB async driver |
| uvicorn | ASGI server |

### Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 14 (App Router) | React framework |
| Shadcn/ui | Component library |
| Tailwind CSS | Styling |
| Lucide React | Icons |
| Recharts | Data visualization |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| MongoDB Atlas | Primary database |
| Digital Ocean App Platform | Hosting (backend + frontend) |
| OpenRouter | LLM API gateway |
| Mock Campaign API (Render) | Email execution sandbox |

---

## Project Structure

```
├── .do/
│   └── app.yaml                  # Digital Ocean App Platform spec
├── backend/
│   ├── Procfile                  # Tells DO buildpack how to start uvicorn
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app factory + lifespan
│   │   ├── agents/               # LangChain agent implementations
│   │   │   ├── brief_parser.py
│   │   │   ├── segmentation.py
│   │   │   ├── strategy.py
│   │   │   ├── content_gen.py
│   │   │   ├── approval.py
│   │   │   └── execution.py
│   │   ├── api/v1/               # REST endpoints
│   │   │   ├── campaigns.py      #   /campaigns + /start + /status
│   │   │   ├── segments.py
│   │   │   ├── approval.py
│   │   │   ├── agents.py         #   Individual agent test endpoints
│   │   │   └── health.py
│   │   ├── orchestration/
│   │   │   ├── campaign_graph.py # LangGraph StateGraph definition
│   │   │   └── state.py          # CampaignState TypedDict
│   │   ├── models/               # MongoDB document models
│   │   ├── db/
│   │   │   ├── mongodb.py        # Atlas connection manager
│   │   │   └── repositories/     # BaseRepository + CampaignRepository etc.
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   └── core/                 # Config, logging, security
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   │   ├── campaigns/
│   │   │   │   ├── create/       # Campaign creation form
│   │   │   │   ├── [id]/         # Campaign detail & approval
│   │   │   │   └── page.tsx      # Campaign list
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── CampaignForm.tsx  # Multi-step campaign brief form
│   │   │   ├── campaign/
│   │   │   │   └── CampaignProgressTracker.tsx  # Live pipeline UI
│   │   │   └── ui/               # Shadcn components
│   │   ├── hooks/
│   │   │   └── useCampaignPolling.ts  # Polls /status every 4s
│   │   └── lib/
│   │       ├── campaignSteps.ts  # Pipeline step definitions
│   │       └── api.ts            # Fetch utilities
└── README.md
```

---

## Getting Started (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account (or local MongoDB)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env` (see [Environment Variables](#environment-variables) below), then:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend

```bash
cd frontend
npm install
npm run dev        # runs on http://localhost:8080
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Environment Variables

### Backend (`backend/.env`)

```env
# App
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# LLM — OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemini-2.5-flash-lite

# MongoDB Atlas
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DATABASE_NAME=autonomail

# Mock Campaign API
MOCK_CAMPAIGN_API_URL=https://mock-campaign-api.onrender.com
MOCK_API_TIMEOUT=60

# CORS
ALLOWED_ORIGINS=["https://autonomail.dev","http://localhost:8080"]

# Security
SECRET_KEY=<openssl rand -hex 32>
ALGORITHM=HS256
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000   # or https://autonomail.dev for prod
```

---

## Deployment

Deployed on **Digital Ocean App Platform** using `.do/app.yaml`.

Both services share a single domain via DO ingress rules:
- `https://autonomail.dev/api/*` → FastAPI backend
- `https://autonomail.dev/*` → Next.js frontend

### Redeploy

Any push to `master` triggers an automatic redeploy (`deploy_on_push: true`).

To deploy manually:
```bash
doctl auth init
doctl apps create --spec .do/app.yaml
# or update existing:
doctl apps update <APP_ID> --spec .do/app.yaml
```

---

## Author

**Abhay Agarwal** · MNNIT Allahabad · Jhansi, Uttar Pradesh, India  
[itsabhay.me](https://itsabhay.me) · [github.com/Abhay030405](https://github.com/Abhay030405) · [officialabhay030405@gmail.com](mailto:officialabhay030405@gmail.com)
