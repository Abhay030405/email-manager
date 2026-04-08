# CampaignX - Project Architecture Document

## Author: Abhay Agarwal
## Project: AI Multi-Agent Marketing Automation Platform
## Target: FrostHack - CampaignX Hackathon

---

# 1. Complete Tech Stack

## Frontend Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI Framework |
| React Router | 6.x | Client-side routing |
| Axios | 1.x | HTTP client for API calls |
| Recharts | 2.x | Data visualization & charts |
| Tailwind CSS | 3.x | Utility-first CSS framework |
| Lucide React | 0.x | Icon library |
| React Hook Form | 7.x | Form management |
| React Query | 4.x | Server state management |
| date-fns | 2.x | Date manipulation |
| Vite | 5.x | Build tool & dev server |

## Backend Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Programming language |
| FastAPI | 0.104+ | Web framework |
| Uvicorn | 0.24+ | ASGI server |
| Pydantic | 2.x | Data validation |
| LangChain | 0.1.x | AI framework |
| LangGraph | 0.0.x | Agent orchestration |
| OpenAI | 1.x | LLM provider |
| Motor | 3.x | Async MongoDB driver |
| PyMongo | 4.x | MongoDB driver |
| python-dotenv | 1.x | Environment management |
| python-multipart | 0.x | File upload support |

## Database & Storage
| Technology | Purpose |
|------------|---------|
| MongoDB | Primary database |
| MongoDB Atlas | Cloud database (optional) |
| Redis | Caching (future consideration) |

## AI & ML Stack
| Technology | Purpose |
|------------|---------|
| OpenAI GPT-4 | Primary LLM |
| LangChain | Agent framework |
| LangGraph | Workflow orchestration |
| FAISS | Vector search (if needed) |

## Development Tools
| Technology | Purpose |
|------------|---------|
| Poetry / pip | Python dependency management |
| npm / yarn | Node.js package management |
| pytest | Backend testing |
| Jest | Frontend testing |
| ESLint | JavaScript linting |
| Black | Python code formatting |
| Ruff | Python linting |
| Git | Version control |

## API Integration Layer
| Integration | Purpose |
|------------|---------|
| External Campaign API | Customer data retrieval |
| External Email API | Campaign execution |
| External Metrics API | Performance tracking |

---

# 2. Project Folder Structure

```
campaignx/
│
├── backend/                           # Backend application
│   ├── app/                          # Main application package
│   │   ├── agents/                   # AI agent implementations
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py        # Base agent class
│   │   │   ├── brief_parser.py      # Campaign Brief Parser Agent
│   │   │   ├── segmentation.py      # Customer Segmentation Agent
│   │   │   ├── strategy.py          # Campaign Strategy Agent
│   │   │   ├── content_gen.py       # Content Generation Agent
│   │   │   ├── approval.py          # Approval Coordinator Agent
│   │   │   ├── execution.py         # Campaign Execution Agent
│   │   │   ├── monitoring.py        # Performance Monitoring Agent
│   │   │   └── optimization.py      # Optimization Agent
│   │   │
│   │   ├── api/                     # API routes
│   │   │   ├── __init__.py
│   │   │   ├── deps.py              # Dependencies
│   │   │   └── v1/                  # API version 1
│   │   │       ├── __init__.py
│   │   │       ├── campaigns.py     # Campaign endpoints
│   │   │       ├── customers.py     # Customer endpoints
│   │   │       ├── segments.py      # Segmentation endpoints
│   │   │       ├── metrics.py       # Metrics endpoints
│   │   │       └── health.py        # Health check endpoints
│   │   │
│   │   ├── core/                    # Core configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Application settings
│   │   │   ├── security.py          # Security utilities
│   │   │   └── logging.py           # Logging configuration
│   │   │
│   │   ├── db/                      # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── mongodb.py           # MongoDB connection
│   │   │   ├── repositories/        # Data access layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── campaign_repo.py
│   │   │   │   ├── customer_repo.py
│   │   │   │   ├── variant_repo.py
│   │   │   │   └── metrics_repo.py
│   │   │   └── migrations/          # Database migrations
│   │   │       └── seed_data.py
│   │   │
│   │   ├── models/                  # Data models
│   │   │   ├── __init__.py
│   │   │   ├── customer.py          # Customer model
│   │   │   ├── campaign.py          # Campaign model
│   │   │   ├── variant.py           # Campaign variant model
│   │   │   ├── metrics.py           # Metrics model
│   │   │   ├── segment.py           # Segment model
│   │   │   └── schemas.py           # Pydantic schemas
│   │   │
│   │   ├── orchestration/           # LangGraph workflows
│   │   │   ├── __init__.py
│   │   │   ├── campaign_graph.py    # Main campaign workflow
│   │   │   ├── optimization_graph.py # Optimization workflow
│   │   │   └── state.py             # Workflow state management
│   │   │
│   │   ├── services/                # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── campaign_service.py  # Campaign business logic
│   │   │   ├── segmentation_service.py
│   │   │   ├── content_service.py
│   │   │   ├── execution_service.py
│   │   │   ├── metrics_service.py
│   │   │   └── optimization_service.py
│   │   │
│   │   ├── external/                # External API integrations
│   │   │   ├── __init__.py
│   │   │   ├── campaign_api.py      # External campaign API client
│   │   │   ├── email_api.py         # Email service provider API
│   │   │   └── analytics_api.py     # Analytics API client
│   │   │
│   │   ├── utils/                   # Utility functions
│   │   │   ├── __init__.py
│   │   │   ├── data_structures.py   # Custom data structures
│   │   │   ├── priority_queue.py    # Priority queue implementation
│   │   │   ├── validators.py        # Input validators
│   │   │   └── helpers.py           # Helper functions
│   │   │
│   │   └── main.py                  # Application entry point
│   │
│   ├── tests/                       # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py              # Pytest configuration
│   │   ├── test_agents/             # Agent tests
│   │   ├── test_api/                # API tests
│   │   ├── test_services/           # Service tests
│   │   └── test_utils/              # Utility tests
│   │
│   ├── scripts/                     # Utility scripts
│   │   ├── seed_database.py         # Database seeding
│   │   └── run_migrations.py        # Migration runner
│   │
│   ├── requirements.txt             # Python dependencies
│   ├── pyproject.toml               # Poetry configuration (optional)
│   ├── .env.example                 # Environment variables template
│   └── README.md                    # Backend documentation
│
├── frontend/                        # Frontend application
│   ├── public/                      # Static files
│   │   ├── index.html
│   │   └── favicon.ico
│   │
│   ├── src/                         # Source code
│   │   ├── assets/                  # Images, fonts, etc.
│   │   │   ├── images/
│   │   │   └── styles/
│   │   │
│   │   ├── components/              # Reusable components
│   │   │   ├── common/              # Common UI components
│   │   │   │   ├── Button.jsx
│   │   │   │   ├── Card.jsx
│   │   │   │   ├── Input.jsx
│   │   │   │   ├── Modal.jsx
│   │   │   │   └── LoadingSpinner.jsx
│   │   │   │
│   │   │   ├── campaign/            # Campaign-specific components
│   │   │   │   ├── CampaignBriefForm.jsx
│   │   │   │   ├── CampaignCard.jsx
│   │   │   │   ├── CampaignList.jsx
│   │   │   │   └── CampaignStatus.jsx
│   │   │   │
│   │   │   ├── segments/            # Segmentation components
│   │   │   │   ├── SegmentCard.jsx
│   │   │   │   ├── SegmentList.jsx
│   │   │   │   └── SegmentVisualizer.jsx
│   │   │   │
│   │   │   ├── approval/            # Approval workflow components
│   │   │   │   ├── ApprovalPanel.jsx
│   │   │   │   ├── VariantComparison.jsx
│   │   │   │   └── ApprovalControls.jsx
│   │   │   │
│   │   │   ├── metrics/             # Metrics & analytics components
│   │   │   │   ├── MetricsDashboard.jsx
│   │   │   │   ├── PerformanceChart.jsx
│   │   │   │   ├── MetricsCard.jsx
│   │   │   │   └── RealtimeMetrics.jsx
│   │   │   │
│   │   │   └── layout/              # Layout components
│   │   │       ├── Header.jsx
│   │   │       ├── Sidebar.jsx
│   │   │       └── Footer.jsx
│   │   │
│   │   ├── pages/                   # Page components
│   │   │   ├── HomePage.jsx         # Landing/dashboard
│   │   │   ├── CampaignCreate.jsx   # Campaign creation
│   │   │   ├── CampaignDetail.jsx   # Campaign details
│   │   │   ├── ApprovalPage.jsx     # Approval interface
│   │   │   ├── MetricsPage.jsx      # Metrics dashboard
│   │   │   └── NotFound.jsx         # 404 page
│   │   │
│   │   ├── services/                # API services
│   │   │   ├── api.js               # Axios instance configuration
│   │   │   ├── campaignService.js   # Campaign API calls
│   │   │   ├── customerService.js   # Customer API calls
│   │   │   ├── metricsService.js    # Metrics API calls
│   │   │   └── segmentService.js    # Segment API calls
│   │   │
│   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── useCampaigns.js
│   │   │   ├── useMetrics.js
│   │   │   └── useWebSocket.js
│   │   │
│   │   ├── context/                 # React Context
│   │   │   ├── AuthContext.jsx
│   │   │   └── CampaignContext.jsx
│   │   │
│   │   ├── utils/                   # Utility functions
│   │   │   ├── formatters.js        # Data formatters
│   │   │   ├── validators.js        # Form validators
│   │   │   └── constants.js         # Constants
│   │   │
│   │   ├── App.jsx                  # Root component
│   │   ├── main.jsx                 # Entry point
│   │   └── index.css                # Global styles
│   │
│   ├── .eslintrc.json               # ESLint configuration
│   ├── tailwind.config.js           # Tailwind configuration
│   ├── vite.config.js               # Vite configuration
│   ├── package.json                 # Node dependencies
│   └── README.md                    # Frontend documentation
│
├── docs/                            # Documentation
│   ├── api/                         # API documentation
│   │   └── endpoints.md
│   ├── agents/                      # Agent documentation
│   │   └── agent_specifications.md
│   ├── architecture/                # Architecture docs
│   │   └── system_design.md
│   └── setup/                       # Setup guides
│       └── installation.md
│
├── .gitignore                       # Git ignore file
├── README.md                        # Project documentation
└── LICENSE                          # License file
```

---

# 3. Development Phases - Complete Breakdown

## Phase 1: Project Setup & Infrastructure Foundation
**Duration:** 3-4 days  
**Goal:** Establish development environment and project scaffolding

### Task 1.1: Initialize Project Repositories
**Description:** Create and configure Git repository with proper branching strategy and folder structure.
- Initialize Git repository with main/develop branches
- Set up .gitignore for Python and Node.js
- Create complete folder structure as per architecture
- Initialize README.md with project overview
- Set up LICENSE file

### Task 1.2: Backend Environment Setup
**Description:** Configure Python environment with all necessary dependencies and tools.
- Install Python 3.11+ and create virtual environment
- Create requirements.txt with all backend dependencies
- Install FastAPI, LangChain, LangGraph, OpenAI, Motor, PyMongo
- Configure .env.example with required environment variables
- Set up code formatting tools (Black, Ruff)

### Task 1.3: Frontend Environment Setup
**Description:** Initialize React application with Vite and install all frontend dependencies.
- Initialize Vite + React project
- Install React Router, Axios, Recharts, Tailwind CSS
- Configure Tailwind CSS with custom theme
- Set up ESLint and Prettier
- Create basic folder structure in src/

### Task 1.4: MongoDB Database Setup
**Description:** Set up MongoDB instance and configure connection.
- Install MongoDB locally or set up MongoDB Atlas account
- Create database and initial collections
- Configure MongoDB connection strings
- Test database connectivity from backend
- Create database configuration file

### Task 1.5: Configuration Management
**Description:** Set up environment variables and configuration management system.
- Create .env files for backend and frontend
- Configure OpenAI API keys
- Set up MongoDB connection strings
- Configure CORS settings for local development
- Create config.py for centralized configuration

---

## Phase 2: Database Design & Data Models
**Duration:** 4-5 days  
**Goal:** Design and implement complete database schema and data access layer

### Task 2.1: Database Schema Design
**Description:** Design MongoDB collections schema with proper relationships and indexes.
- Design Customers collection schema
- Design Campaigns collection schema
- Design Campaign Variants collection schema
- Design Metrics collection schema
- Design Segments collection schema
- Create indexes for performance optimization

### Task 2.2: Pydantic Models Implementation
**Description:** Create Pydantic models for data validation and serialization.
- Create CustomerModel with validation rules
- Create CampaignModel with nested structures
- Create VariantModel with email content fields
- Create MetricsModel with performance tracking
- Create API request/response schemas

### Task 2.3: Repository Pattern Implementation
**Description:** Build data access layer using repository pattern for clean architecture.
- Create base repository class with CRUD operations
- Implement CampaignRepository with specialized queries
- Implement CustomerRepository with segmentation queries
- Implement VariantRepository with filtering
- Implement MetricsRepository with aggregation queries

### Task 2.4: Database Seeding & Mock Data
**Description:** Create seed data for development and testing.
- Generate mock customer data (100-500 customers)
- Create sample campaign templates
- Generate historical metrics data
- Create seed script for database initialization
- Test data integrity and relationships

### Task 2.5: Database Testing & Validation
**Description:** Validate database operations and ensure data integrity.
- Write unit tests for repository methods
- Test CRUD operations for all collections
- Validate data relationships and constraints
- Test indexing performance
- Create database migration scripts

---

## Phase 3: Core AI Agent Development
**Duration:** 7-10 days  
**Goal:** Build individual AI agents with proper LangChain integration

### Task 3.1: Base Agent Architecture
**Description:** Create foundational agent class with common functionality.
- Design BaseAgent class with LangChain integration
- Implement OpenAI LLM configuration
- Create agent memory management
- Build prompt template system
- Implement error handling and retry logic

### Task 3.2: Campaign Brief Parser Agent
**Description:** Build agent to extract structured data from natural language briefs.
- Design prompt templates for brief parsing
- Implement structured output parsing
- Extract: product, audience, goals, CTA, budget
- Validate extracted data with Pydantic
- Test with various brief formats
- Handle edge cases and malformed inputs

### Task 3.3: Customer Segmentation Agent
**Description:** Create intelligent customer segmentation using AI.
- Design segmentation prompt templates
- Implement clustering logic based on demographics
- Create segment naming algorithm
- Generate segment descriptions
- Validate segment quality and distribution
- Test with different customer datasets

### Task 3.4: Campaign Strategy Agent
**Description:** Build agent to generate campaign targeting and timing strategies.
- Design strategy generation prompts
- Determine optimal segment targeting
- Calculate send time optimization
- Generate A/B testing strategies
- Create variant distribution logic
- Validate strategy feasibility

### Task 3.5: Content Generation Agent
**Description:** Create agent for generating email subject lines and bodies.
- Design content generation prompts
- Implement subject line generation (5-10 variants)
- Generate email body with personalization
- Create tone and style adaptation
- Implement A/B variant creation
- Validate content quality and appropriateness

---

## Phase 4: LangGraph Orchestration System
**Duration:** 6-8 days  
**Goal:** Build agent orchestration workflow using LangGraph

### Task 4.1: Workflow State Management
**Description:** Design state management system for multi-agent workflows.
- Create CampaignState class for workflow
- Define state transitions and data flow
- Implement state persistence to MongoDB
- Build state validation logic
- Create state recovery mechanisms

### Task 4.2: Campaign Creation Graph
**Description:** Build LangGraph workflow for campaign creation pipeline.
- Create graph nodes for each agent
- Define edges between agents (Parser → Segmenter → Strategy → Content)
- Implement conditional routing logic
- Add human-in-loop approval node
- Test full workflow execution

### Task 4.3: Optimization Loop Graph
**Description:** Create feedback loop for continuous campaign optimization.
- Build optimization workflow graph
- Create edge from Optimization → Strategy (feedback loop)
- Implement convergence criteria
- Add performance threshold checks
- Test iterative optimization

### Task 4.4: Error Handling & Recovery
**Description:** Implement robust error handling in workflow execution.
- Add try-catch blocks at each node
- Implement agent failure recovery
- Create fallback strategies
- Add workflow checkpointing
- Log agent decisions and errors

### Task 4.5: Graph Testing & Validation
**Description:** Thoroughly test workflow orchestration.
- Test individual node execution
- Test complete workflow end-to-end
- Validate state transitions
- Test error scenarios
- Measure workflow execution time

---

## Phase 5: Backend API Development
**Duration:** 6-8 days  
**Goal:** Build comprehensive REST API with FastAPI

### Task 5.1: API Architecture & Middleware
**Description:** Set up FastAPI application structure with middleware.
- Create FastAPI application instance
- Configure CORS middleware
- Implement request logging middleware
- Add authentication middleware (if needed)
- Set up error handling middleware
- Configure OpenAPI documentation

### Task 5.2: Campaign Management Endpoints
**Description:** Build API endpoints for campaign CRUD operations.
- POST /api/v1/campaigns/create - Create new campaign
- GET /api/v1/campaigns - List all campaigns
- GET /api/v1/campaigns/{id} - Get campaign details
- PUT /api/v1/campaigns/{id} - Update campaign
- DELETE /api/v1/campaigns/{id} - Delete campaign
- Implement request validation with Pydantic

### Task 5.3: Approval & Execution Endpoints
**Description:** Create endpoints for campaign approval and execution workflow.
- POST /api/v1/campaigns/{id}/approve - Approve campaign
- POST /api/v1/campaigns/{id}/reject - Reject campaign
- POST /api/v1/campaigns/{id}/execute - Execute campaign
- GET /api/v1/campaigns/{id}/status - Get execution status
- Implement approval workflow logic

### Task 5.4: Customer & Segmentation Endpoints
**Description:** Build APIs for customer data and segmentation.
- GET /api/v1/customers - Fetch customer cohort
- GET /api/v1/customers/{id} - Get customer details
- POST /api/v1/segments/generate - Generate segments
- GET /api/v1/segments - List segments
- GET /api/v1/segments/{name} - Get segment details

### Task 5.5: Metrics & Analytics Endpoints
**Description:** Create endpoints for performance metrics.
- GET /api/v1/campaigns/{id}/metrics - Get campaign metrics
- GET /api/v1/campaigns/{id}/variants/metrics - Get variant-wise metrics
- POST /api/v1/campaigns/{id}/optimize - Trigger optimization
- GET /api/v1/analytics/dashboard - Get dashboard data
- Implement real-time metrics updates

---

## Phase 6: Frontend Foundation & UI Components
**Duration:** 7-9 days  
**Goal:** Build React frontend with all core components

### Task 6.1: UI Component Library
**Description:** Create reusable UI components with Tailwind CSS.
- Build Button component with variants
- Create Card component for data display
- Build Input/Textarea components
- Create Modal component for dialogs
- Build LoadingSpinner and progress indicators
- Create Alert/Notification components

### Task 6.2: Campaign Brief Input Interface
**Description:** Build campaign creation form with validation.
- Create CampaignBriefForm component
- Implement form validation with React Hook Form
- Add rich text editor for campaign brief
- Build product details input section
- Create target audience selector
- Add campaign goals dropdown

### Task 6.3: Strategy Dashboard
**Description:** Display generated campaign strategy and segments.
- Create StrategyDashboard component
- Build SegmentCard to display each segment
- Create VariantPreview component
- Implement segment visualization with charts
- Add scheduling calendar view
- Display A/B test plan

### Task 6.4: Approval Interface
**Description:** Build interactive approval workflow UI.
- Create ApprovalPanel component
- Build side-by-side variant comparison
- Add edit capabilities for email content
- Implement approve/reject buttons
- Create comment/feedback section
- Add revision request functionality

### Task 6.5: Routing & Navigation
**Description:** Set up React Router and navigation system.
- Configure React Router v6
- Create route definitions for all pages
- Build Header with navigation menu
- Implement Sidebar navigation
- Add breadcrumb navigation
- Create 404 Not Found page

---

## Phase 7: Campaign Execution & External Integration
**Duration:** 6-7 days  
**Goal:** Integrate with external APIs for campaign execution

### Task 7.1: External API Client Setup
**Description:** Build abstraction layer for external API calls.
- Create base HTTP client with Axios
- Implement authentication handling
- Add retry logic for failed requests
- Build rate limiting
- Create error handling wrappers

### Task 7.2: Customer Data API Integration
**Description:** Integrate with external customer cohort API.
- Implement customer data fetching
- Parse and validate customer data
- Map external data to internal models
- Handle pagination for large datasets
- Add data caching mechanism

### Task 7.3: Email Campaign API Integration
**Description:** Connect to email service provider API.
- Implement email sending API calls
- Build batch email scheduling
- Handle API rate limits
- Implement send time optimization
- Add delivery status tracking

### Task 7.4: Campaign Execution Agent Implementation
**Description:** Build execution agent that triggers email campaigns.
- Create ExecutionAgent with API integration
- Implement campaign scheduling logic
- Build batch processing for segments
- Add execution error handling
- Create execution status tracking

### Task 7.5: Integration Testing
**Description:** Test all external API integrations.
- Test customer data retrieval
- Test email sending functionality
- Validate API error handling
- Test rate limiting behavior
- Mock external APIs for testing

---

## Phase 8: Metrics Collection & Monitoring System
**Duration:** 5-6 days  
**Goal:** Build performance tracking and metrics collection

### Task 8.1: Performance Monitoring Agent
**Description:** Create agent to collect campaign performance metrics.
- Build MonitoringAgent for metrics collection
- Implement open rate tracking
- Implement click rate tracking
- Add conversion tracking
- Create metrics polling system

### Task 8.2: Metrics API Integration
**Description:** Integrate with external analytics API.
- Connect to campaign metrics API
- Implement metric data parsing
- Handle real-time metric updates
- Add historical metrics retrieval
- Build metrics caching

### Task 8.3: Metrics Dashboard Frontend
**Description:** Build interactive metrics visualization.
- Create MetricsDashboard component
- Implement real-time metrics display
- Build PerformanceChart with Recharts
- Add segment-wise metric breakdown
- Create campaign comparison view

### Task 8.4: Real-time Metrics Updates
**Description:** Implement live metrics updates using polling/WebSocket.
- Set up metrics polling system
- Implement WebSocket connection (optional)
- Build real-time chart updates
- Add notification for performance alerts
- Create refresh mechanism

### Task 8.5: Metrics Storage & Analytics
**Description:** Store and analyze performance data.
- Save metrics to MongoDB
- Implement time-series storage
- Build aggregation queries
- Create historical analysis
- Generate performance reports

---

## Phase 9: Optimization Engine & Feedback Loop
**Duration:** 7-8 days  
**Goal:** Build AI-powered continuous optimization system

### Task 9.1: Performance Scoring Algorithm
**Description:** Implement campaign performance scoring system.
- Create scoring formula (70% click, 30% open)
- Build variant ranking algorithm
- Implement priority queue for optimization
- Add percentile calculations
- Create performance threshold logic

### Task 9.2: Optimization Agent Development
**Description:** Build AI agent for campaign optimization.
- Create OptimizationAgent with LangChain
- Implement poor performer identification
- Build optimization prompt templates
- Generate improved variant suggestions
- Add A/B test recommendations

### Task 9.3: Variant Replacement Logic
**Description:** Implement automatic variant replacement system.
- Identify bottom 25% performers
- Generate new optimized variants
- Replace poor variants in database
- Update campaign strategy
- Trigger re-execution

### Task 9.4: Optimization Workflow Integration
**Description:** Connect optimization to LangGraph workflow.
- Add optimization node to graph
- Create feedback edge to strategy agent
- Implement optimization trigger conditions
- Add convergence detection
- Test full optimization loop

### Task 9.5: Optimization Dashboard
**Description:** Build UI for optimization insights.
- Create OptimizationDashboard component
- Display optimization suggestions
- Show before/after comparisons
- Add manual optimization controls
- Create optimization history view

---

## Phase 10: Testing, Polish & Deployment
**Duration:** 6-8 days  
**Goal:** Comprehensive testing, debugging, and production readiness

### Task 10.1: Backend Unit & Integration Testing
**Description:** Write comprehensive test suite for backend.
- Write pytest tests for all agents
- Test API endpoints with TestClient
- Test database repositories
- Test LangGraph workflows
- Achieve 80%+ code coverage

### Task 10.2: Frontend Testing
**Description:** Test React components and user flows.
- Write Jest tests for components
- Test React hooks
- Test API service layer
- Add end-to-end testing with Cypress (optional)
- Test responsive design

### Task 10.3: System Integration Testing
**Description:** Test complete system end-to-end.
- Test full campaign creation workflow
- Test approval and execution flow
- Test metrics collection pipeline
- Test optimization loop
- Validate all agent interactions

### Task 10.4: Performance Optimization & Polish
**Description:** Optimize performance and improve UX.
- Optimize database queries with indexes
- Add frontend loading states
- Implement error boundaries
- Optimize API response times
- Improve UI/UX based on testing

### Task 10.5: Documentation & Deployment Preparation
**Description:** Complete documentation and prepare for deployment.
- Write comprehensive README
- Document API endpoints
- Create setup/installation guide
- Write agent specifications document
- Create demo video/screenshots
- Prepare presentation for hackathon

---

# 4. Running the Application

## Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Frontend
```bash
cd frontend
npm install
npm run dev  # Runs on port 5173 by default
```

## MongoDB
```bash
# Local MongoDB
mongod --dbpath /path/to/data

# Or use MongoDB Atlas (cloud)
```

---

# 5. Environment Variables

## Backend (.env)
```
OPENAI_API_KEY=sk-...
MONGODB_URI=mongodb://localhost:27017/campaignx
DATABASE_NAME=campaignx
EXTERNAL_CAMPAIGN_API_URL=https://...
EXTERNAL_EMAIL_API_URL=https://...
EXTERNAL_METRICS_API_URL=https://...
LOG_LEVEL=INFO
```

## Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

# 6. Development Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 3-4 days | None |
| Phase 2 | 4-5 days | Phase 1 |
| Phase 3 | 7-10 days | Phase 1, 2 |
| Phase 4 | 6-8 days | Phase 3 |
| Phase 5 | 6-8 days | Phase 2, 4 |
| Phase 6 | 7-9 days | Phase 5 |
| Phase 7 | 6-7 days | Phase 3, 5 |
| Phase 8 | 5-6 days | Phase 5, 7 |
| Phase 9 | 7-8 days | Phase 4, 8 |
| Phase 10 | 6-8 days | All phases |

**Total Estimated Duration:** 8-10 weeks for complete production-ready system  
**Hackathon MVP:** Can be completed in 3-4 weeks by focusing on core functionality

---

# 7. Success Metrics

- ✅ All 8 AI agents functioning correctly
- ✅ Complete workflow orchestration with LangGraph
- ✅ Full CRUD API for campaigns
- ✅ Interactive React frontend
- ✅ Real-time metrics collection
- ✅ Working optimization loop
- ✅ 80%+ test coverage
- ✅ Comprehensive documentation

---

**End of Architecture Document**
