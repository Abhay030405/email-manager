# Phase 3: Core AI Agent Development

## Status: Complete

---

## Overview

Phase 3 implemented all five core AI agents that form the intelligence layer of CampaignX.
Every agent inherits from a shared `BaseAgent` class and follows a consistent pattern:
Pydantic-validated input → GPT-4 LLM call with retry/backoff → heuristic post-processing →
Pydantic-validated output → structured logging.

---

## Task 3.1 – BaseAgent Architecture ✅

**File:** `backend/app/agents/base_agent.py`

### Summary

Created the abstract foundation class for all CampaignX agents. Provides shared LLM
initialisation, conversation memory, prompt templating, resilient retry logic, structured
logging, Pydantic validation, and LLM output parsing.

### Class: `BaseAgent(ABC)`

| Method / Attribute | Description |
|--------------------|-------------|
| `__init__(model_name, temperature, max_tokens, timeout)` | Wires all parameters; calls `setup_llm()` and `setup_memory()` on construction |
| `setup_llm()` | Creates `ChatOpenAI` (GPT-4) reading `OPENAI_API_KEY` from `Settings`; raises `ValueError` if key is missing |
| `setup_memory()` | Returns a fresh `ConversationBufferMemory` (key=`chat_history`, message-list mode) |
| `create_prompt_template(template, input_variables)` | Factory for `PromptTemplate` |
| `execute(input_data)` | `@abstractmethod` — every subclass must implement |
| `_retry_with_backoff(func, *args, max_retries=3)` | Async-aware retry with 1 s → 2 s → 4 s exponential back-off; wraps each call in `asyncio.wait_for(timeout)` |
| `_log_action(action, data)` | Emits structured `INFO` log with agent name, action label, and context dict |
| `_validate_input(data, schema)` | Runs `schema.model_validate(data)`; wraps `ValidationError` in `ValueError` |
| `_parse_llm_output(raw_output)` | Strips markdown fences → JSON decode; falls back to `{"content": raw}` |

### Key Design Decisions

- **LLM import**: Tries `langchain_openai.ChatOpenAI` first, falls back to `langchain.chat_models.ChatOpenAI` for older environments (guarded by `try/except ImportError`).
- **Timeout enforcement**: Every LLM call is wrapped with `asyncio.wait_for` so no call can hang indefinitely (default 30 s).
- **Retry is call-site agnostic**: `_retry_with_backoff` works with both `async` coroutines and sync callables via `loop.run_in_executor`.
- **Constants** are class-level so subclasses can override: `DEFAULT_MODEL`, `DEFAULT_TEMPERATURE`, `DEFAULT_MAX_TOKENS`, `DEFAULT_TIMEOUT`, `MAX_RETRIES`.

---

## Task 3.2 – Campaign Brief Parser Agent ✅

**File:** `backend/app/agents/brief_parser.py`

### Summary

Extracts structured campaign data from free-form natural language briefs using GPT-4
with a detailed extraction prompt. Handles partial information gracefully and validates
all critical fields.

### Schemas

| Schema | Fields |
|--------|--------|
| `BriefInput` | `brief_text: str` — stripped, non-empty |
| `ParsedBrief` | `product_name`, `product_description`, `target_audience`, `campaign_goal` (enum), `cta_link` (URL-validated), `budget: Optional[float]`, `preferred_tone` (enum), `key_messages: List[str]`, `constraints: Optional[str]` |

### Class: `CampaignBriefParserAgent`

| Aspect | Detail |
|--------|--------|
| Temperature | 0.1 (deterministic extraction) |
| Max tokens | 1 024 |
| `campaign_goal` validation | Enum guard: `awareness \| conversion \| retention \| engagement` |
| `preferred_tone` validation | Enum guard with safe fallback to `"professional"` |
| `cta_link` validation | `urlparse` checks scheme + netloc; sentinel values ("n/a", "unknown") normalised to `""` |
| Budget parsing | Regex strips `$`, `,`, handles `k`/`K` multiplier (e.g. `"$5k"` → `5000.0`) |
| `key_messages` | Comma-separated strings are split; blank entries are stripped |
| Critical fields | `model_validator` raises `ValueError` if `product_name` or `target_audience` remain unknown after LLM extraction |
| Prompt | Two worked examples (full brief + minimal/ambiguous brief); explicit field-mapping rules (e.g. "sales"→conversion) |

---

## Task 3.3 – Customer Segmentation Agent ✅

**File:** `backend/app/agents/segmentation.py`

### Summary

Segments a customer list into 3–7 prioritised groups using a two-stage approach:
a pure-Python rule engine builds candidate groups from demographics, then GPT-4
selects, merges, and prioritises the most relevant segments for the campaign goal.

### Schemas

| Schema | Fields |
|--------|--------|
| `SegmentationInput` | `customers: List[Customer]`, `target_audience: str`, `campaign_goal: str` |
| `SegmentOut` | `segment_name`, `description`, `customer_ids`, `size` (auto-synced), `targeting_priority` (1–5), `recommended_approach` |
| `SegmentationResult` | `segments` (sorted by priority desc), `total_customers`, `coverage_pct`, `distribution: Dict[str, int]` |

### Class: `CustomerSegmentationAgent`

| Aspect | Detail |
|--------|--------|
| Temperature | 0.2 (semi-deterministic) |
| Max tokens | 2 048 |
| Age brackets | gen_z (18-24), millennials (25-34), gen_x_young (35-44), gen_x_senior (45-54), seniors (55+) |
| Candidate groups | Age bracket, activity status, goal-aligned high-priority status, gender (male/female), combined age+activity multi-dimensional |
| Micro-segment filter | Groups covering <5% of population are hidden from the LLM prompt |
| Goal-to-status mapping | `awareness` → inactive first; `conversion`/`retention`/`engagement` → active first |
| Coverage guarantee | `_ensure_coverage()` — unassigned customers appended to lowest-priority segment; catch-all `"all_customers"` segment created if no segments exist |
| Edge cases | Small datasets (<50 customers) still produce valid candidate groups; homogeneous populations fall back gracefully |

---

## Task 3.4 – Campaign Strategy Agent ✅

**File:** `backend/app/agents/strategy.py`

### Summary

Generates optimal campaign targeting strategy, send schedule, A/B test plan, budget
allocation, and expected open rates. Uses heuristic pre-computation as LLM prompt hints,
then refines the strategy with GPT-4 reasoning.

### Schemas

| Schema | Fields |
|--------|--------|
| `StrategyInput` | `parsed_brief: ParsedBrief`, `segments: List[SegmentOut]`, `current_time: datetime` (UTC-forced) |
| `ABTestPlan` | `num_variants` (2–4), `variant_distribution: Dict[str, float]` (must sum to 100), `test_dimension: str` |
| `CampaignStrategy` | `selected_segments`, `send_schedule: Dict[str, datetime]`, `ab_test_plan`, `budget_allocation` (sums to 100), `expected_metrics`, `reasoning` |

### Class: `CampaignStrategyAgent`

| Aspect | Detail |
|--------|--------|
| Temperature | 0.3 |
| Max tokens | 2 048 |
| Segment selection | Top 2–5 by `(priority, size)`; conversion goal requires priority ≥ 4 |
| Send schedule | Marketing best-practice hour pools per goal × weekday/weekend; awareness staggers sends 2 h apart |
| Budget allocation | `priority × size` weighted; **conversion** squares priority to concentrate spend |
| Open rate estimation | Name-heuristic base rates (active=28%, inactive=14%, dormant=8%) + per-goal boost; capped at 0.99 |
| A/B variant count | Budget-aware: `<$2k`→2, `<$10k`→3, `≥$10k`→4 variants |
| Post-processing | Normalises ISO datetime strings; re-normalises distributions that don't sum to 100; fills all missing keys from pre-computed fallbacks |

---

## Task 3.5 – Content Generation Agent ✅

**File:** `backend/app/agents/content_gen.py`

### Summary

Generates personalised, mobile-responsive HTML email content for each campaign variant.
Uses a variant-archetype system to ensure A/B variants are meaningfully differentiated
while maintaining brand consistency.

### Schemas

| Schema | Fields |
|--------|--------|
| `ContentGenerationInput` | `parsed_brief: ParsedBrief`, `segment: SegmentOut`, `variant_id: str`, `strategy: CampaignStrategy` |
| `EmailContent` | `variant_id`, `segment_name`, `subject_lines` (≥5, 40–60 chars), `email_body` (HTML), `preview_text` (50–100 chars), `personalization_tags`, `tone`, `estimated_read_time` |

### Class: `ContentGenerationAgent`

| Aspect | Detail |
|--------|--------|
| Temperature | 0.75 (creative diversity) |
| Max tokens | 3 000 |
| Variant archetypes | A=Benefit/Emotional, B=Feature/Logical, C=Urgency/FOMO, D=Social-proof — injected into prompt |
| HTML shell | Full responsive wrapper with inline CSS, `@media` mobile query, per-tone accent/header colours, unsubscribe + privacy footer |
| Subject lines | 8 options requested; fallback generator produces 5 if LLM output is unusable |
| Personalisation tags | Auto-detected from `[TOKEN]` patterns in body + subject lines via regex if not supplied by LLM |
| Read time | Inferred from word count (strip HTML tags; 200 wpm reading speed) |
| Performance logging | `time.perf_counter()` tracks per-call execution time; prompt length and response length logged for token auditing |
| Fallback chain | Bare HTML fragments wrapped in responsive shell; missing preview text generated from product + segment name |

### Tone → Colour Mapping

| Tone | Accent colour | Header colour |
|------|--------------|--------------|
| professional | `#1a73e8` (blue) | `#1a1a2e` (navy) |
| casual | `#f4511e` (orange) | `#16213e` (dark blue) |
| friendly | `#34a853` (green) | `#0f3460` (midnight) |
| urgent | `#d93025` (red) | `#950101` (dark red) |

---

## Cross-Cutting Concerns (Applied to All Agents)

### Error Handling
- Try/except inside `_retry_with_backoff` for all LLM calls
- `asyncio.TimeoutError` caught separately and logged with timeout duration
- Malformed LLM JSON falls back to `{"content": raw_output}` in `_parse_llm_output`
- ValidationError wrapped in ValueError with human-readable message at every `_validate_input` call
- Post-process methods fill all required keys before Pydantic validation to prevent hard failures

### Logging
- Every agent logs: `execute_start`, `prompt_sent`, `llm_response_received`, `execute_complete`
- Retry attempts logged with attempt number, max retries, and error message
- Validation errors logged with full Pydantic error list
- Coverage gaps logged with unassigned count and percentage
- Execution time (seconds) logged in content generation

### Performance
- All LLM calls use `async/await` (`llm.ainvoke`)
- Temperature tuned per agent (0.1 extraction → 0.75 creative)
- Max token budgets sized per task (1024 extraction → 3000 content generation)
- Pre-computed heuristics reduce LLM workload (strategy, segmentation)
- Prompt fences stripped before JSON parsing to avoid decode failures

### Testability
- All agents instantiate without live credentials (validation happens at call time)
- `_call_llm` is a thin private method — easily mockable in unit tests
- Every schema has `json_schema_extra` examples for documentation and test data generation
- Input/output types are fully typed with Pydantic models

---

## Updated Files Summary

| File | Action | Description |
|------|--------|-------------|
| `backend/app/agents/base_agent.py` | Created | Abstract base class with LLM, memory, retry, logging, validation |
| `backend/app/agents/brief_parser.py` | Created | Brief parsing agent with full extraction prompt |
| `backend/app/agents/segmentation.py` | Created | Customer segmentation agent with rule-engine + LLM |
| `backend/app/agents/strategy.py` | Created | Strategy agent with scheduling, budget, A/B plan |
| `backend/app/agents/content_gen.py` | Created | Email content agent with responsive HTML shell |
| `backend/app/agents/__init__.py` | Updated | Exports all 5 agents + 12 schema classes |
| `backend/app/models/schemas.py` | Updated | Added 10 agent I/O schemas with field descriptions and examples |

---

## Dependencies Required

All already listed in `backend/requirements.txt`:

```
langchain>=0.1.0
openai>=1.0
pydantic>=2.0
```

Optional (for `langchain_openai` import path):
```
langchain-openai>=0.1.0
```

---

## Next Phase

**Phase 4: LangGraph Orchestration**
- Wire all 5 agents into `backend/app/orchestration/campaign_graph.py`
- Implement `optimization_graph.py` for post-campaign feedback loops
- Define LangGraph `StateGraph` nodes, edges, and conditional routing
- Integrate with the existing FastAPI service layer
