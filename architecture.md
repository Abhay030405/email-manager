# CampaignX — Agentic System Architecture

## Table of Contents
1. [System Overview](#system-overview)
2. [Agent Catalogue](#agent-catalogue)
   - [CampaignBriefParserAgent](#1-campaignbriefparseragent)
   - [CustomerSegmentationAgent](#2-customersegmentationagent)
   - [CampaignStrategyAgent](#3-campaignstrategyagent)
   - [ContentGenerationAgent](#4-contentgenerationagent)
   - [ApprovalAgent](#5-approvalagent)
   - [ExecutionAgent](#6-executionagent)
   - [MonitoringAgent](#7-monitoringagent)
   - [OptimizationAgent](#8-optimizationagent)
3. [Shared Infrastructure — BaseAgent](#shared-infrastructure--baseagent)
4. [Orchestration Graphs](#orchestration-graphs)
   - [Main Campaign Graph](#main-campaign-graph)
   - [Optimization Feedback Loop](#optimization-feedback-loop)
5. [State & Persistence](#state--persistence)
6. [Full System Architecture Diagram](#full-system-architecture-diagram)

---

## System Overview

CampaignX is an **LLM-powered multi-agent marketing automation platform**. A user submits a natural-language campaign brief; the system autonomously parses it, segments customers via the Mock Campaign API, devises a strategy, generates personalised email variants, waits for human approval, executes the campaign via a Mock Campaign API, monitors results, and iteratively optimises underperforming variants.

The orchestration layer is built on **LangGraph** (state-machine graph), with each node delegating to a specialised **agent** that wraps an OpenAI LLM call with retry logic, Pydantic validation, structured logging, and deterministic fallbacks.

> **Customer data is never stored in MongoDB.** All customer filtering and ID resolution is delegated to the Mock Campaign API via `POST /api/customers/filter`. The `customers` collection and the `fetch_customers` graph node have been removed.

---

## Agent Catalogue

---

### 1. `CampaignBriefParserAgent`
**File:** `backend/app/agents/brief_parser.py`  
**Purpose:** Converts a raw natural-language marketing brief into a fully structured, validated data object, including multi-group audience segmentation criteria.

#### Input

Schema: `BriefInput`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `brief_text` | `str` | `min_length=1` | Raw campaign brief in any natural language |

**Example input:**
```json
{
  "brief_text": "Launch XDeposit for salaried professionals aged 25–45 in metro cities. Monthly income > ₹50k, app installed. Goal: drive sign-ups at https://example.com/xdeposit."
}
```

#### API Response

The `/api/v1/campaigns/parse-brief` endpoint wraps the agent output into `ParsedBriefSections` — a nested structure that maps directly to the 4-step confirmation wizard and to the `parsed_data` field stored in MongoDB.

**Top-level sections:**

| Section | Type | Description |
|---------|------|-------------|
| `product_details` | `object` | Product name, description, CTA link |
| `target_audience` | `dict[GroupName, AudienceGroup]` | One entry per audience group extracted from the brief |
| `campaign_goal` | `object` | Full descriptive campaign objective |
| `campaign_preferences` | `object` | Tone, campaign name, content hints |

**`product_details`**

| Field | Type | Description |
|-------|------|-------------|
| `product_name` | `str` | Name of the product/service |
| `product_description` | `str` | Short product description |
| `cta_link` | `str` | Call-to-action URL |

**`target_audience`** — keyed by group label (e.g. `"Group 1"`, `"Group 2"`, …)

Each group is an `AudienceGroup` object with 10 fields. These are sent as-is to the Mock API filter endpoint — no local customer data is loaded.

| Field | Type | Mock API filter field |
|-------|------|-----------------------|
| `min_age` | `int \| null` | `min_age` |
| `max_age` | `int \| null` | `max_age` |
| `gender` | `str \| null` | `gender` (sent as single-element array) |
| `min_income` | `int \| null` | `min_monthly_income` |
| `max_income` | `int \| null` | `max_monthly_income` |
| `KYC_status` | `str \| null` | `kyc_status` |
| `App_Installed` | `str \| null` | Sub-segmentation only — not sent in base filter |
| `Existing_Customer` | `str \| null` | Sub-segmentation only — not sent in base filter |
| `Credit_score` | `int \| null` | `min_credit_score` (minimum threshold) |
| `Social_Media_Active` | `str \| null` | `social_media_active` |

`null` means the field is omitted from the filter request (Mock API returns all values).

> The segmentation agent accepts **both** the PascalCase names above and their snake_case equivalents (`kyc_status`, `min_credit_score`, `social_media_active`, etc.) which the LLM brief parser may output. If `min_age > max_age` the values are silently swapped before the API call.

**`campaign_goal`**

| Field | Type | Description |
|-------|------|-------------|
| `objective` | `str` | Full descriptive objective including success metrics |

**`campaign_preferences`**

| Field | Type | Description |
|-------|------|-------------|
| `email_tone` | `str` | One of: `Formal \| Friendly \| Urgent` |
| `campaign_name` | `str` | Auto-generated campaign label |
| `content_hints` | `str` | Key messages, timing rules, personalisation instructions |

**Example output:**
```json
{
  "product_details": {
    "product_name": "XDeposit Smart Savings Plan",
    "product_description": "A premium investment product offering guaranteed returns of 8.5% per annum with complete capital protection and zero market risk.",
    "cta_link": "https://superbfsi.com/xdeposit/explore/"
  },
  "target_audience": {
    "Group 1": {
      "min_age": 25, "max_age": 35,
      "gender": null,
      "min_income": 40000, "max_income": null,
      "KYC_status": "Y", "App_Installed": "Y",
      "Existing_Customer": null, "Credit_score": null,
      "Social_Media_Active": "Y"
    },
    "Group 2": {
      "min_age": 35, "max_age": 55,
      "gender": null,
      "min_income": 80000, "max_income": null,
      "KYC_status": "Y", "App_Installed": "Y",
      "Existing_Customer": "N", "Credit_score": 700,
      "Social_Media_Active": null
    }
  },
  "campaign_goal": {
    "objective": "Generate completed applications for XDeposit from distinct customer segments, aiming for open rate > 40% and click rate > 14%."
  },
  "campaign_preferences": {
    "email_tone": "Friendly",
    "campaign_name": "XDeposit_June2026",
    "content_hints": "Guaranteed 8.5% returns per annum. Emails scheduled Tuesday/Wednesday 8–10 AM IST."
  }
}
```

#### Internal Steps
1. LLM temperature `0.1` — deterministic, factual extraction
2. Max tokens `2048` (supports long briefs up to ~15k chars)
3. `_retry_with_backoff` — up to 3 attempts (1s → 2s → 4s)
4. **Post-processing:** CTA sentinel removal, key_messages coercion, budget normalisation (`"$5k"` → `5000.0`), tone normalisation
5. **Multi-group extraction:** LLM identifies distinct audience groups and maps each to the 10-field `AudienceGroup` schema; `null` = no filter for that field
6. **Validation:** `product_name` is hard-required (raises `ValueError`); missing audience groups fall back to `"General audience"`

---

### 2. `CustomerSegmentationAgent`
**File:** `backend/app/agents/segmentation.py`  
**Purpose:** Calls `POST /api/customers/filter` on the Mock API for each audience group, then sub-segments the returned IDs by `App_Installed × Existing_Customer` status using parallel filter calls. **No LLM calls. No local customer data.**

> **Key design principle:** no customer records are loaded or stored locally.  
> All filtering is delegated to the Mock API. If an `AudienceGroup` field is `null`, it is simply omitted from the request body — the API returns all values for that field.

---

#### Step 1 — Build Filter Request (`_build_filter_body`)

For each audience group, non-null fields are mapped to Mock API request body keys:

| `AudienceGroup` field | Mock API body field |
|---|---|
| `min_age` / `max_age` | `min_age` / `max_age` (swapped if inverted) |
| `gender` | `gender` (single-element array — OR logic) |
| `min_income` / `max_income` | `min_monthly_income` / `max_monthly_income` |
| `KYC_status` / `kyc_status` | `kyc_status` |
| `Credit_score` / `min_credit_score` | `min_credit_score` |
| `Social_Media_Active` / `social_media_active` | `social_media_active` |

Both PascalCase (from `AudienceGroup` model) and snake_case (from LLM output) are accepted for each field.  
`App_Installed` / `Existing_Customer` are **excluded** from this body — they control the sub-segmentation API calls in Step 2.

---

#### Step 2 — Sub-segmentation by App × Existing Customer (parallel API calls)

| Condition | API calls made | Segments produced |
|---|---|---|
| Both `null` (unspecified) | 3 parallel calls | `{prefix}_active` (App=Y + Existing=Y), `{prefix}_inactive` (App=N + Existing=Y), `{prefix}_dormant` (Existing=N) |
| At least one specified | 1 call | Single segment with the specified filter values |

All groups run **in parallel** across the graph via `asyncio.gather`. Each sub-segment call returns `{ count, customer_ids[] }` from the Mock API.

---

#### Input

| Field | Type | Description |
|-------|------|-------------|
| `target_audience` | `dict[str, AudienceGroup]` | Group-keyed audience criteria from the parser agent |
| `campaign_goal` | `str` | `awareness \| conversion \| retention \| engagement` |

---

#### Output

| Field | Type | Description |
|-------|------|-------------|
| `segments` | `list[SegmentOut]` | All sub-segments across all groups |
| `total_customers` | `int` | Fixed Mock API cohort size (5 000) |
| `qualified_count` | `int` | Unique customer IDs across all segments |
| `coverage_pct` | `float` | `qualified_count / 5000 × 100` |
| `distribution` | `dict[str, int]` | `segment_name → customer_count` |
| `groups_detail` | `list[dict]` | Per-group breakdown: `filter_applied`, `qualified_count`, `segments`, `coverage_pct` |

Each `SegmentOut`:

| Field | Type | Description |
|-------|------|-------------|
| `segment_name` | `str` | `{group_prefix}_{active\|inactive\|dormant\|app\|no_app\|existing\|prospect}` |
| `description` | `str` | Human-readable segment summary |
| `customer_ids` | `list[str]` | IDs returned by Mock API filter call |
| `size` | `int` | Auto-synced from `len(customer_ids)` |
| `targeting_priority` | `int` | 1–5 (5 = highest; active existing = 5) |
| `recommended_approach` | `str` | Tactical messaging guidance |
| `applied_criteria` | `dict` | Exact filter body sent for this sub-segment |

**Example output:**
```json
{
  "segments": [
    {
      "segment_name": "group_1_active",
      "description": "Active customers — app installed + existing relationship",
      "customer_ids": ["CUST0042", "CUST0107"],
      "size": 22,
      "targeting_priority": 5,
      "recommended_approach": "Lead with loyalty and retention messaging. Upsell focus.",
      "applied_criteria": {"min_age": 25, "max_age": 45, "kyc_status": "Y", "App_Installed": "Y", "Existing_Customer": "Y"}
    },
    {
      "segment_name": "group_1_inactive",
      "description": "Existing customers without the app — re-engagement opportunity",
      "customer_ids": ["CUST0201"],
      "size": 26,
      "targeting_priority": 3,
      "recommended_approach": "Drive app install with benefit-led messaging.",
      "applied_criteria": {"min_age": 25, "max_age": 45, "kyc_status": "Y", "App_Installed": "N", "Existing_Customer": "Y"}
    },
    {
      "segment_name": "group_1_dormant",
      "description": "Non-customers — acquisition focus",
      "customer_ids": ["CUST0301"],
      "size": 48,
      "targeting_priority": 4,
      "recommended_approach": "Welcome framing. Emphasise simplicity of sign-up.",
      "applied_criteria": {"min_age": 25, "max_age": 45, "kyc_status": "Y", "Existing_Customer": "N"}
    }
  ],
  "total_customers": 5000,
  "qualified_count": 96,
  "coverage_pct": 1.9,
  "distribution": {"group_1_active": 22, "group_1_inactive": 26, "group_1_dormant": 48},
  "groups_detail": [...]
}
```

---

#### Internal Steps

1. **No LLM calls** (temperature `0.0`); no local customer data loaded
2. All groups processed **in parallel** via `asyncio.gather`
3. Per group: `_build_filter_body()` maps criteria → Mock API body; `_first_set()` resolves dual PascalCase / snake_case keys
4. Sub-segmentation fires 3 parallel filter calls (or 1 if App/Existing specified); each call uses `asyncio.run_in_executor` to wrap the synchronous `MockCampaignClient`
5. **Coverage** calculated as `unique_customer_ids / 5000` (fixed Mock API cohort)
6. **Fallback:** if `target_audience` is empty or not a dict → single `general_audience` segment with empty `customer_ids`

---

### 3. `CampaignStrategyAgent`
**File:** `backend/app/agents/strategy.py`  
**Purpose:** Produces targeting plan, send schedule, A/B test configuration, and budget allocation.

#### Input

Schema: `StrategyInput`

| Field | Type | Description |
|-------|------|-------------|
| `parsed_brief` | `ParsedBrief` | Structured campaign brief |
| `segments` | `list[SegmentOut]` | Non-empty list of available segments |
| `current_time` | `datetime` | Timezone-aware UTC datetime |

#### Output

Schema: `CampaignStrategy`

| Field | Type | Description |
|-------|------|-------------|
| `selected_segments` | `list[str]` | 2–5 segment names chosen for targeting |
| `send_schedule` | `dict[str, datetime]` | `segment_name → ISO-8601 send time` |
| `ab_test_plan.num_variants` | `int` | 2–4 variants based on budget |
| `ab_test_plan.test_dimension` | `str` | `subject_line \| content \| send_time \| cta \| tone` |
| `ab_test_plan.variant_distribution` | `dict[str, float]` | `variant_id → traffic %` (sums to 100) |
| `budget_allocation` | `dict[str, float]` | `segment_name → budget %` (sums to 100) |
| `expected_metrics` | `dict[str, float]` | `segment_name → expected open rate (0–1)` |
| `reasoning` | `dict[str, str]` | `segment_name → rationale` |

**Example output:**
```json
{
  "selected_segments": ["gen_x_young_active", "millennials_active"],
  "send_schedule": {
    "gen_x_young_active": "2025-06-10T09:00:00Z",
    "millennials_active": "2025-06-10T11:00:00Z"
  },
  "ab_test_plan": {
    "num_variants": 2,
    "test_dimension": "subject_line",
    "variant_distribution": {"variant_A": 50.0, "variant_B": 50.0}
  },
  "budget_allocation": {"gen_x_young_active": 65.0, "millennials_active": 35.0},
  "expected_metrics": {"gen_x_young_active": 0.32, "millennials_active": 0.28},
  "reasoning": {"gen_x_young_active": "Highest priority segment with active app users..."}
}
```

#### Internal Steps
1. LLM temperature `0.3`, max tokens `2048`
2. **Heuristic pre-computation** before LLM call:
   - Variant count: 2 if budget < ₹2k, 3 if < ₹10k, 4 if ≥ ₹10k
   - Send time: goal-specific best-practice hours; staggered 2h offsets for awareness
   - Budget: proportional to `priority² × size`
   - Open rate estimation: base by activity × goal boost
3. LLM refines and validates heuristic hints
4. Post-processing normalises allocations to sum to 100

---

### 4. `ContentGenerationAgent`
**File:** `backend/app/agents/content_gen.py`  
**Purpose:** Generates personalised, mobile-responsive HTML email content for each A/B variant.

#### Input

Schema: `ContentGenerationInput`

| Field | Type | Description |
|-------|------|-------------|
| `parsed_brief` | `ParsedBrief` | Full campaign brief |
| `segment` | `SegmentOut` | Target customer segment |
| `variant_id` | `str` | A/B variant identifier (e.g. `"abc123_v1"`) |
| `strategy` | `CampaignStrategy` | Full campaign strategy |

#### Output

Schema: `EmailContent`

| Field | Type | Description |
|-------|------|-------------|
| `variant_id` | `str` | Matches input |
| `segment_name` | `str` | Target segment name |
| `subject_lines` | `list[str]` | 5–10 options, 40–60 characters each |
| `email_body` | `str` | Mobile-responsive HTML (`min_length=100`) |
| `preview_text` | `str` | 50–100 char inbox preview snippet |
| `personalization_tags` | `list[str]` | Auto-detected tokens e.g. `["[FIRST_NAME]", "[LOCATION]"]` |
| `tone` | `str` | Applied tone |
| `estimated_read_time` | `str` | `"< 1 min"`, `"1 min"`, or `"2 min"` |

**Example output:**
```json
{
  "variant_id": "abc123_v1",
  "segment_name": "gen_x_young_active",
  "subject_lines": [
    "Secure your future with XDeposit, [FIRST_NAME]",
    "Higher returns, zero risk — XDeposit for [LOCATION] professionals"
  ],
  "email_body": "<html>...</html>",
  "preview_text": "Earn 1% more than market rate. Sign up in under 2 minutes.",
  "personalization_tags": ["[FIRST_NAME]", "[LOCATION]"],
  "tone": "professional",
  "estimated_read_time": "< 1 min"
}
```

#### Internal Steps
1. LLM temperature `0.75` (creative diversity), max tokens `3000`
2. **Variant archetype system** (last letter of variant_id → archetype):
   - `v1 / A` → Benefit-focused / Emotional appeal
   - `v2 / B` → Feature-focused / Logical appeal
   - `v3 / C` → Urgency / FOMO
   - `v4 / D` → Social proof / Testimonial
3. **Tone-driven accent colours** in HTML wrapper: professional `#1a73e8`, casual `#f4511e`, friendly `#34a853`, urgent `#d93025`
4. **Personalisation token detection:** auto-scans body + subjects for `[TOKEN]` patterns
5. **Variant ID scoped to campaign:** `{campaign_prefix}_v{index}` — prevents duplicate key errors across campaigns

---

### 5. `ApprovalAgent`
**File:** `backend/app/agents/approval.py`  
**Purpose:** Non-LLM agent that reads campaign approval status from MongoDB and surfaces it to the workflow.

#### Input

| Field | Type | Description |
|-------|------|-------------|
| `campaign_id` | `str` | Campaign identifier |

#### Output

| Field | Type | Values |
|-------|------|--------|
| `approval_status` | `str` | `"approved" \| "rejected" \| "pending"` |

#### Internal Steps
1. No LLM call — pure database read (temperature `0.0`)
2. Maps `CampaignStatus` enum → approval string
3. Returns `"pending"` as safe default if campaign not found

---

### 6. `ExecutionAgent`
**File:** `backend/app/agents/execution.py`  
**Purpose:** Schedules approved email variants via the Mock Campaign API.

#### Input

| Field | Type | Description |
|-------|------|-------------|
| `campaign_id` | `str` | Campaign identifier |
| `variants` | `list[dict]` | Approved variants with `subject_line`, `email_body`, `send_time`, `customer_ids`, `segment_name`, `variant_id` |

#### Output

| Field | Type | Description |
|-------|------|-------------|
| `execution_status` | `str` | `"completed" \| "failed"` |
| `mock_api_campaign_ids` | `dict[str, str]` | `variant_id → mock_campaign_id` |
| `metrics.emails_scheduled` | `int` | Total emails queued |
| `metrics.executed_at` | `str` | ISO-8601 timestamp |
| `metrics.errors` | `list[str]` | Per-variant error messages |

#### Internal Steps
1. No LLM call (temperature `0.0`, acts as orchestrator)
2. Per variant: validates customer IDs → Mock API, filters invalids, calls `schedule_campaign()`
3. Persists `mock_campaign_id` to `VariantRepository` and writes `ExecutionLog` records
4. Uses `asyncio.run_in_executor` for blocking Mock API calls

---

### 7. `MonitoringAgent`
**File:** `backend/app/agents/monitoring.py`  
**Purpose:** Fetches aggregated and per-customer performance metrics from the Mock Campaign API.

#### Input

| Field | Type | Description |
|-------|------|-------------|
| `campaign_id` | `str` | Campaign identifier |
| `mock_api_campaign_ids` | `dict[str, str] \| null` | `variant_id → mock_campaign_id` |

#### Output

| Field | Type | Description |
|-------|------|-------------|
| `variant_metrics` | `list[dict]` | Per-variant: `open_rate`, `click_rate`, `click_through_rate`, `total_sent`, `unique_opens`, `unique_clicks`, `collected_at` |
| `aggregates` | `dict` | `avg_open_rate`, `avg_click_rate`, `avg_ctr`, `total_sent`, overall rates |
| `customer_results` | `list[dict]` | Per customer: `customer_id`, `opened`, `clicked`, `open_probability`, `click_probability` |

#### Internal Steps
1. No LLM call (temperature `0.0`)
2. Calls `get_campaign_metrics()` + `get_campaign_results()` per variant
3. Stores `Metrics` model in MongoDB (rates stored as 0–1)
4. In-memory cache per `campaign_id`; falls back to `MetricsRepository` if API unavailable

---

### 8. `OptimizationAgent`
**File:** `backend/app/agents/optimization.py`  
**Purpose:** Analyses metric data and produces actionable improvement recommendations for underperforming variants.

#### Input

| Field | Type | Description |
|-------|------|-------------|
| `campaign_id` | `str` | Campaign identifier |
| `metrics` | `dict` | Collected metrics from MonitoringAgent |

#### Output

| Field | Type | Description |
|-------|------|-------------|
| `optimization_recommendations` | `list[dict]` | Each: `{variant_id, changes: [str, ...], priority: "high"\|"medium"\|"low"}` |

**Example:**
```json
{
  "optimization_recommendations": [
    {
      "variant_id": "abc123_v2",
      "changes": [
        "Shorten subject line to < 50 characters",
        "Add first name personalisation in opening line",
        "Move CTA button above the fold"
      ],
      "priority": "high"
    }
  ]
}
```

#### Internal Steps
1. LLM temperature `0.3`, max tokens `2000`
2. **Scoring:** `score = 0.7 × click_rate + 0.3 × open_rate`
3. **Poor performer threshold:** variants scoring < 75% of average
4. **Rule-based fallback** (if LLM fails):
   - `open_rate < 20%` → shorten subject, add urgency, personalise, reschedule to Tue/Wed 8–10 AM
   - `click_rate < 5%` → CTA above fold, 2–3 benefit statements, trim to 100–200 words
5. **Convergence check:** improvement < 5% between iterations → stop

---

## Shared Infrastructure — BaseAgent

All agents inherit from `BaseAgent` (`backend/app/agents/base_agent.py`):

| Feature | Implementation |
|---------|----------------|
| **LLM client** | OpenAI wrapper; tries Responses API (gpt-5/o-series) first, falls back to Chat Completions |
| **Model** | Read from `settings.OPENAI_MODEL` (`.env`) — never hardcoded |
| **Retry** | Exponential backoff: 1s → 2s → 4s, max 3 attempts |
| **Output parsing** | 1) strip markdown fences → 2) direct JSON → 3) extract `{...}` → 4) extract `[...]` → 5) wrap as `{"content": raw}` |
| **Input validation** | Pydantic `model_validate()`; raises `ValueError` on failure, logged before re-raise |
| **Structured logging** | `_log_action(action, data)` on every key event (start, complete, validation_error, etc.) |
| **Prompt templates** | LangChain `PromptTemplate` with named variables |
| **Memory** | `ConversationBufferMemory` (with no-op fallback stub if LangChain unavailable) |

---

## Orchestration Graphs

### Main Campaign Graph

**File:** `backend/app/orchestration/campaign_graph.py`  
**Framework:** LangGraph `StateGraph`  
**State type:** `CampaignState` (TypedDict, 18 fields)

#### Node Execution Order

```
START
  │
  ▼
┌─────────────┐
│ parse_brief │  CampaignBriefParserAgent
│             │  IN:  campaign_brief (str)
│             │  OUT: parsed_data (dict)
└──────┬──────┘
       │
  ▼
┌───────────────┐
│ segmentation  │  CustomerSegmentationAgent
│               │  IN:  target_audience, campaign_goal
│               │  OUT: segments {name→ids}, checkpoint_data.segments_detail
│               │  CALLS: POST /api/customers/filter (Mock API, parallel)
│               │  PERSISTS: Segment docs to MongoDB
│               │  FALLBACK: general_audience placeholder segment
└──────┬────────┘
       │
  ▼
┌──────────┐
│ strategy │  CampaignStrategyAgent
│          │  IN:  parsed_data, segments_detail, current_time
│          │  OUT: strategy {selected_segments, send_schedule, ab_test_plan, budget_allocation}
└────┬─────┘
     │
  ▼
┌────────────────────┐
│ content_generation │  ContentGenerationAgent (one call per selected segment)
│                    │  IN:  parsed_brief, segment, variant_id, strategy
│                    │  OUT: variants[]
│                    │  PERSISTS: CampaignVariant docs to MongoDB
└─────────┬──────────┘
          │
  ▼
┌──────────┐
│ approval │  ApprovalAgent
│          │  IN:  campaign_id
│          │  OUT: approval_status
└─────┬────┘
      │
      ├─── "approved" ──────────────────────────────────────────┐
      │                                                         │
      ├─── "rejected" ──────────────────────────────────────── END
      │
      └─── "pending" ─────────────────────────────────────┐
                                                          │
                                               ┌──────────▼──────────┐
                                               │   wait_approval     │
                                               │  (polls, max 3×)    │
                                               └──────────┬──────────┘
                                                          │
                                               loops back to ──► approval
                                                          │
                                               (if max waits reached) ──► END

"approved" path:
      │
  ▼
┌───────────┐
│ execution │  ExecutionAgent
│           │  IN:  campaign_id, variants[]
│           │  OUT: execution_status, mock_api_campaign_ids, metrics
│           │  PERSISTS: ExecutionLog, variant.mock_campaign_id
└─────┬─────┘
      │
     END
```

#### State Fields

| Field | Type | Populated By |
|-------|------|-------------|
| `campaign_id` | `str` | Initial state |
| `campaign_brief` | `str` | Initial state |
| `parsed_data` | `dict` | Pre-populated from user-confirmed form (`POST /campaigns`); merged with LLM re-extraction in `parse_brief` node — user values win |
| `segments` | `dict[str, list[str]]` | `segmentation` node |
| `strategy` | `dict` | `strategy` node |
| `variants` | `list[dict]` | `content_generation` node |
| `approval_status` | `str` | `approval` node |
| `execution_status` | `str` | `execution` node |
| `mock_api_campaign_ids` | `dict[str, str]` | `execution` node |
| `metrics` | `dict` | `execution` node |
| `customer_results` | `list` | Reserved for monitoring |
| `optimization_suggestions` | `list` | Reserved for optimization |
| `error_messages` | `list[str]` | Any failing node |
| `checkpoint_data` | `dict` | Cross-node transient data (includes `segments_detail`) |

#### Error Handling Per Node

Every node is wrapped in `_execute_node_with_retries()`:
- **3 attempts** with exponential backoff (1s → 2s → 4s)
- On exhaustion → deterministic **fallback** function runs
- State saved to MongoDB after every attempt (success or fallback)
- Checkpoint snapshot created before each attempt

---

### Optimization Feedback Loop

**File:** `backend/app/orchestration/campaign_graph.py` (optimization section)  
**State type:** `OptimizationState` (TypedDict, 11 fields)

#### Node Execution Order

```
START
  │
  ▼
┌─────────────────┐
│ collect_metrics │  MonitoringAgent
│                 │  IN:  campaign_id, mock_api_campaign_ids
│                 │  OUT: current_metrics, customer_results
│                 │  FALLBACK: MetricsRepository
└────────┬────────┘
         │
  ▼
┌──────────────────────────┐
│ identify_poor_performers │  (Python logic, no LLM)
│                          │  score = 0.7×click_rate + 0.3×open_rate
│                          │  poor = bottom 25% by score
│                          │  OUT: poor_performers[], performance_scores{}
└────────────┬─────────────┘
             │
  ▼
┌──────────────┐
│ optimization │  OptimizationAgent
│              │  IN:  campaign_id, current_metrics
│              │  OUT: optimization_recommendations[]
│              │  FALLBACK: rule-based subject/body/timing fixes
└──────┬───────┘
       │
  ▼
┌─────────────────────┐
│ regenerate_variants │  ContentGenerationAgent
│                     │  IN:  recommendations, original parsed_brief
│                     │  OUT: new_variants[]
│                     │  Cancels poor performers, schedules improved via Mock API
└────────┬────────────┘
         │
  ▼
┌─────────────────┐
│ update_strategy │  CampaignStrategyAgent (optional)
│                 │  Schedules new variants, increments iteration_count
└────────┬────────┘
         │
         ├─── check_convergence() ──► "end"  ────────────────► END
         │
         └─── check_convergence() ──► "continue" ──► collect_metrics (loop)
```

#### Convergence Conditions (stops loop)

| Condition | Reason |
|-----------|--------|
| `iteration_count >= 3` | Max iterations reached |
| All variant scores ≥ 12.0 | Performance threshold met |
| No poor performers identified | Campaign already optimal |
| `error_messages` present | Error recovery — stop safely |

---

## State & Persistence

### MongoDB Collections

| Collection | Model | Contents |
|------------|-------|----------|
| `campaigns` | `Campaign` | Campaign document with `parsed_data`, `status`, `segments` (name list) |
| `campaign_variants` | `CampaignVariant` | Email variant per segment — `subject_line`, `email_body`, `variant_id`, `mock_campaign_id` |
| `segments` | `Segment` | Rich segment documents — `customer_ids` (from Mock API), `segment_criteria`, `description`, `size` |
| `metrics` | `Metrics` | Variant performance — `open_rate`, `click_rate`, `click_through_rate` (stored 0–1) |
| `workflow_states` | `CampaignStateModel` | Full `CampaignState` snapshot per campaign |
| `workflow_checkpoints` | — | State snapshot before each node attempt |
| `execution_logs` | `ExecutionLog` | Per-variant execution records (SUCCESS / FAILED / SKIPPED) |

> The `customers` collection has been removed. Customer IDs are fetched on-demand from the Mock API at segmentation time and stored in `segments.customer_ids`.

### What lives where

```
campaigns.parsed_data     ← nested 4-section dict matching parser API output:
                             {
                               product_details:      { product_name, product_description, cta_link }
                               target_audience:      { "Group 1": {...}, "Group 2": {...}, ... }
                               campaign_goal:        { objective }
                               campaign_preferences: { email_tone, campaign_name, content_hints }
                             }
                             User-confirmed values (from wizard) are stored here and
                             win over LLM re-extraction when the workflow runs.
campaigns.segments        ← list[str] of segment names only
segments collection       ← full Segment docs with customer_ids, criteria, size
campaign_variants         ← EmailContent output, one doc per variant per segment
```

---

## Full System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER / FRONTEND                                   │
│                                                                             │
│  POST /campaigns/parse-brief   POST /campaigns        POST /{id}/run-workflow│
│  (brief → wizard pre-fill)     (brief + parsed_data)  (triggers LangGraph)  │
└────────────────┬───────────────────────────────────┬────────────────────────┘
                 │                                   │
                 ▼                                   ▼
┌────────────────────────┐           ┌───────────────────────────────────────┐
│   FastAPI REST Layer   │           │         LangGraph Orchestrator        │
│   /api/v1/campaigns    │           │         (campaign_graph.py)           │
│   /api/v1/segments     │           │                                       │
│   /api/v1/variants     │           │  ┌──────────────────────────────────┐ │
│   /api/v1/metrics      │           │  │         CampaignState            │ │
│   /api/v1/approval     │           │  │  (16 fields, persisted after     │ │
└────────┬───────────────┘           │  │   every node)                    │ │
         │                           │  └──────────────────────────────────┘ │
         ▼                           │                                       │
┌────────────────────────┐           │  parse_brief ──► segmentation         │
│      MongoDB           │◄──────────│       ──► strategy                    │
│                        │           │       ──► content_generation          │
│  campaigns             │           │       ──► approval                    │
│  campaign_variants     │           │       ──► [wait / reject / execute]   │
│  segments              │           │                                       │
│  metrics               │           │  Optimization Loop (separate graph):  │
│  workflow_states       │           │  collect_metrics ──► identify_poor    │
│  workflow_checkpoints  │           │       ──► optimize ──► regenerate      │
│  execution_logs        │           │       ──► update_strategy             │
└────────────────────────┘           │       ──► [converge or loop]          │
                                     └──────────────┬────────────────────────┘
                                                    │
                                    ┌───────────────┴────────────────────────┐
                                    │              AGENTS                    │
                                    │                                        │
                                    │  ┌────────────────────────────────┐    │
                                    │  │       BaseAgent                │    │
                                    │  │  • OpenAI LLM wrapper          │    │
                                    │  │  • Pydantic input validation   │    │
                                    │  │  • Exponential retry (3×)      │    │
                                    │  │  • JSON output parsing         │    │
                                    │  │  • Structured logging          │    │
                                    │  │  • Model from OPENAI_MODEL env │    │
                                    │  └────────────┬───────────────────┘    │
                                    │               │ (inherited by)         │
                                    │   ┌───────────┼───────────┐            │
                                    │   ▼           ▼           ▼            │
                                    │  Brief    Segment    Strategy           │
                                    │  Parser   Agent      Agent             │
                                    │   ▼           ▼           ▼            │
                                    │  Content  Approval  Execution          │
                                    │  Agent    Agent     Agent              │
                                    │   ▼           ▼                        │
                                    │  Monitor  Optimize                     │
                                    │  Agent    Agent                        │
                                    └────────────────┬───────────────────────┘
                                                     │
                                     ┌───────────────▼──────────────┐
                                     │    Mock Campaign API         │
                                     │  (mock-campaign-api.onrender)│
                                     │                              │
                                     │  POST /api/customers/filter  │ ← segmentation
                                     │  GET  /api/customers/count   │
                                     │  POST /api/customers/validate│
                                     │  POST /api/campaigns/schedule│
                                     │  GET  /api/campaigns/{id}/   │
                                     │       metrics                │
                                     │  GET  /api/campaigns/{id}/   │
                                     │       results                │
                                     └──────────────────────────────┘
```

### Data Flow Summary

```
User provides raw brief (text / .txt upload)
    │
    ▼  POST /campaigns/parse-brief  →  CampaignBriefParserAgent
ParsedBriefSections {
  product_details, target_audience (per-group criteria), campaign_goal, campaign_preferences
}
    │
    ▼  Frontend 4-step wizard — user reviews and edits each section
User-confirmed ParsedBriefSections
    │
    ▼  POST /campaigns  (campaign_brief + parsed_data)
Campaign document created in MongoDB (status = draft)
No created_by field — campaigns are system-owned.
    │
    ▼  POST /campaigns/{id}/run-workflow  →  LangGraph
    │
    ▼  parse_brief node — CampaignBriefParserAgent (re-runs on brief)
      Merges LLM output with user-confirmed parsed_data (user values win)
    │
    ▼  segmentation node — CustomerSegmentationAgent (no LLM, no local customer data)
      Step 1: _build_filter_body() maps AudienceGroup fields → Mock API request body
              (handles both PascalCase and snake_case keys; swaps inverted min/max age)
      Step 2: POST /api/customers/filter × 3 parallel calls per group
              (active: App=Y+Existing=Y, inactive: App=N+Existing=Y, dormant: Existing=N)
              OR 1 call if App_Installed / Existing_Customer explicitly specified
      Result: named segments with customer_ids[], targeting_priority, coverage_pct
    │
    ▼  strategy node — CampaignStrategyAgent
      campaign_goal.objective resolved to enum via _safe_goal()
      Produces: selected segments, send schedule, A/B plan, budget split
    │
    ▼  content_generation node — ContentGenerationAgent (× num_segments)
      Email variants: HTML body, subject lines, personalisation tokens
    │
    ▼  approval node — ApprovalAgent
      approval_status: pending → [human sets via API] → approved
    │
    ▼  execution node — ExecutionAgent
      Schedules via Mock API → mock_campaign_id per variant
    │
    ▼  MonitoringAgent
      open_rate, click_rate, per-customer outcomes
    │
    ▼  OptimizationAgent (feedback loop, max 3 iterations)
      Recommendations → regenerated variants → re-scheduled → converge
```
