# AI-Driven Multi-Agent Platform for Campaign Planning & Optimization

An autonomous AI multi-agent system that plans, executes, monitors, and optimizes digital marketing email campaigns.

The platform operates like an autonomous marketing team: specialized AI agents collaborate through a directed execution graph to understand campaign briefs, segment customers, generate strategies, create email content, execute campaigns, collect metrics, and continuously optimize performance through feedback loops.

**Author:** Abhay Agarwal

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core AI Agents](#core-ai-agents)
- [System Workflow](#system-workflow)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Structures & Optimization](#data-structures--optimization)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Development Phases](#development-phases)

---

## Architecture Overview

```
Frontend Layer (React + Tailwind CSS)
         ↓
API Gateway Layer (FastAPI REST)
         ↓
Campaign Orchestration Layer (LangGraph Workflows)
         ↓
AI Agent Layer (LangChain + OpenAI GPT-4)
         ↓
External Campaign APIs (Customer Data · Email Sending · Analytics)
         ↓
Data Storage & Analytics Layer (MongoDB + Motor)
```

### Design Principles

1. **Agentic AI Architecture** — Specialized agents with distinct responsibilities
2. **Feedback-Driven Optimization** — Continuous improvement via metrics loops
3. **Modular System Design** — Clean separation of concerns across layers
4. **Data-Structure Driven Intelligence** — Priority queues, hashmaps, and graphs for efficient processing
5. **Human-in-the-Loop Safety** — Approval gates before campaign execution

---

## Core AI Agents

| Agent | Responsibility |
|-------|---------------|
| **Campaign Brief Parser** | Extracts structured data (product, audience, CTA, budget) from natural language briefs |
| **Customer Segmentation** | Groups customers into micro-segments based on demographics and behavior |
| **Campaign Strategy** | Determines targeting strategy, send-time optimization, and A/B test plans |
| **Content Generation** | Generates email subject lines and bodies with personalization variants |
| **Approval Coordinator** | Manages human-in-the-loop approval workflow |
| **Campaign Execution** | Interfaces with external email APIs to schedule and send campaigns |
| **Performance Monitoring** | Collects open rates, click rates, and conversion metrics |
| **Optimization** | Identifies underperformers, generates improved variants, and triggers re-optimization |

### Agent Orchestration Graph

```
BriefParser → Segmenter → StrategyPlanner → ContentGenerator → ApprovalNode
                                                                     ↓
                          OptimizationAgent ← MetricsCollector ← ExecutionAgent
                                ↓
                          StrategyPlanner (feedback loop)
```

Agents are orchestrated as a **directed execution graph** using LangGraph, with conditional routing and a feedback loop from the Optimization Agent back to Strategy for continuous improvement.

---

## System Workflow

1. **Campaign Brief Input** — Marketer enters a natural language campaign brief
2. **Brief Parsing** — AI extracts product details, target audience, CTA link, and goals
3. **Customer Retrieval** — System fetches customer cohort via external APIs
4. **Segmentation** — Customers grouped into meaningful micro-segments
5. **Strategy Generation** — AI determines segments, send times, and A/B variants
6. **Content Generation** — AI generates email subjects, bodies, and style variants
7. **Human Approval** — Campaign plan displayed for review and approval
8. **Execution** — Approved campaigns scheduled and sent via email API
9. **Metrics Collection** — Open rates and click rates collected in real-time
10. **Optimization Loop** — AI adjusts strategy and relaunches underperforming variants

---

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Programming language |
| FastAPI | REST API framework |
| Pydantic v2 | Data validation & serialization |
| LangChain | AI agent framework |
| LangGraph | Agent orchestration workflows |
| OpenAI GPT-4 | Primary LLM |
| Motor (async) | MongoDB async driver |
| PyMongo | MongoDB driver |

### Frontend
| Technology | Purpose |
|------------|---------|
| React 18 | UI framework |
| Tailwind CSS | Styling |
| Recharts | Data visualization |
| React Router 6 | Routing |
| Axios | HTTP client |
| Vite | Build tool |

### Database & Infrastructure
| Technology | Purpose |
|------------|---------|
| MongoDB | Primary database |
| Faker | Mock data generation |
| pytest + pytest-asyncio | Testing framework |
| mongomock-motor | In-memory test database |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/              # 8 AI agent implementations
│   │   │   ├── base_agent.py    #   Base agent class (LangChain)
│   │   │   ├── brief_parser.py  #   Campaign brief parser
│   │   │   ├── segmentation.py  #   Customer segmentation
│   │   │   ├── strategy.py      #   Campaign strategy planner
│   │   │   ├── content_gen.py   #   Email content generator
│   │   │   ├── approval.py      #   Approval coordinator
│   │   │   ├── execution.py     #   Campaign execution
│   │   │   ├── monitoring.py    #   Performance monitoring
│   │   │   └── optimization.py  #   Optimization engine
│   │   ├── api/v1/              # REST API endpoints
│   │   ├── core/                # Config, security, logging
│   │   ├── db/                  # MongoDB connection & repositories
│   │   │   ├── mongodb.py       #   Async connection manager (pooling)
│   │   │   ├── repositories/    #   Generic BaseRepository + 4 repos
│   │   │   └── migrations/      #   Seed data (Faker, 500+ records)
│   │   ├── models/              # Pydantic models & schemas
│   │   ├── orchestration/       # LangGraph campaign & optimization graphs
│   │   ├── services/            # Business logic layer
│   │   ├── external/            # External API integrations
│   │   └── utils/               # Data structures, validators, helpers
│   ├── tests/                   # 97 async tests (pytest)
│   │   ├── conftest.py          #   Shared fixtures & mock DB
│   │   └── test_repositories/   #   Repository CRUD & query tests
│   └── scripts/                 # DB seeding & migration scripts
├── frontend/                    # React application
├── docs/                        # Architecture & build plan docs
└── README.md
```

---

## Data Structures & Optimization

### Customer Storage
```
HashMap<CustomerID, CustomerProfile>
```
Indexed by `customer_id`, `age`, `gender`, `location`, `activity_status`.

### Segment Storage
```
HashMap<SegmentName, List<CustomerID>>
```
Segments auto-sync size with customer ID lists via Pydantic validators.

### Campaign Variant Storage
```
List<CampaignVariant>   # subject, body, send_time, metrics per variant
```
3–5 A/B variants per campaign, tracked by segment.

### Optimization Priority Queue
```
PriorityQueue<CampaignVariant>
score = 0.7 × click_rate + 0.3 × open_rate
```
Lowest-scoring variants are prioritized for AI-driven replacement. Performance score is auto-calculated via `model_validator`.

### MongoDB Collections

| Collection | Key Indexes |
|------------|-------------|
| `customers` | customer_id (unique), age, gender, location, activity_status |
| `campaigns` | campaign_id (unique), status, created_at (desc) |
| `campaign_variants` | variant_id (unique), campaign_id, segment_name, status |
| `metrics` | metric_id (unique), variant_id, campaign_id, performance_score (desc) |
| `segments` | segment_id (unique), campaign_id, segment_name |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB (local or Atlas)

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### Seed the Database

```bash
cd backend
python scripts/seed_database.py
```

Generates 500 customers, 10 campaigns, 37 variants, metrics, and 26 segments using Faker with deterministic seeds.

### Run the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

### Backend (`backend/.env`)
```env
OPENAI_API_KEY=sk-...
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=campaignx
EXTERNAL_CAMPAIGN_API_URL=https://...
EXTERNAL_EMAIL_API_URL=https://...
EXTERNAL_METRICS_API_URL=https://...
LOG_LEVEL=INFO
```

### Frontend (`frontend/.env`)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

**Current status:** 97 tests passing — covering all 4 repository classes with CRUD, specialised queries, Pydantic model validation, and error handling. Tests use `mongomock-motor` for in-memory async MongoDB.

| Test Area | Tests |
|-----------|-------|
| Campaign Repository | 25 |
| Customer Repository | 27 |
| Variant Repository | 22 |
| Metrics Repository | 23 |

---

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project Setup & Infrastructure | ✅ Complete |
| 2 | Database Design & Data Models | ✅ Complete |
| 3 | Core AI Agent Development | Upcoming |
| 4 | LangGraph Orchestration System | Upcoming |
| 5 | Backend API Development | Upcoming |
| 6 | Frontend Foundation & UI Components | Upcoming |
| 7 | Campaign Execution & External Integration | Upcoming |
| 8 | Metrics Collection & Monitoring | Upcoming |
| 9 | Optimization Engine & Feedback Loop | Upcoming |
| 10 | Testing, Polish & Deployment | Upcoming |

---

## License

Built by Abhay Agarwal.