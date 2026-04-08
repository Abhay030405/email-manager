# Phase 2: Database Design & Data Models

## Status: Complete

---

## Task 2.1 – Database Schema Design ✅

**Completed:** 2026-04-08

### Summary

Implemented all 5 MongoDB collection schemas as Pydantic models with index definitions, request/response schemas, async MongoDB connection manager, repository pattern data access layer, and seed data generator.

### Files Written

| File | Description |
|------|-------------|
| `backend/app/core/config.py` | Application settings (MongoDB URL, DB name) via pydantic-settings |
| `backend/app/models/customer.py` | Customer model – enums (Gender, ActivityStatus), PurchaseRecord, Preferences, indexes |
| `backend/app/models/campaign.py` | Campaign model – CampaignStatus enum, ParsedData, auto-generated UUID, indexes |
| `backend/app/models/variant.py` | CampaignVariant model – VariantStatus enum, personalization_tags, indexes |
| `backend/app/models/metrics.py` | Metrics model – auto-calculated performance_score via model_validator, indexes |
| `backend/app/models/segment.py` | Segment model – SegmentCriteria for demographic filters, indexes |
| `backend/app/models/schemas.py` | Pydantic request/response schemas (Create, Update, Response) for all 5 entities |
| `backend/app/models/__init__.py` | Models package exports |
| `backend/app/db/mongodb.py` | MongoDB async connection manager (Motor), auto index creation on connect |
| `backend/app/db/__init__.py` | Database package exports |
| `backend/app/db/repositories/customer_repo.py` | CustomerRepository – CRUD + find_by_criteria + count |
| `backend/app/db/repositories/campaign_repo.py` | CampaignRepository – CRUD + find_by_status + count |
| `backend/app/db/repositories/variant_repo.py` | VariantRepository – CRUD + find_by_campaign + find_by_segment |
| `backend/app/db/repositories/metrics_repo.py` | MetricsRepository – CRUD + find_by_variant/campaign + get_top_performers |
| `backend/app/db/repositories/__init__.py` | Repositories package exports |
| `backend/app/db/migrations/seed_data.py` | Seed data generator (50 customers, 1 campaign, 3 segments, 3 variants, 3 metrics) |

### Collections & Indexes

| Collection | Indexes |
|------------|---------|
| `customers` | customer_id (unique), age, gender, location, activity_status |
| `campaigns` | campaign_id (unique), status, created_at (desc) |
| `campaign_variants` | variant_id (unique), campaign_id, segment_name, status |
| `metrics` | metric_id (unique), variant_id, campaign_id, performance_score (desc), timestamp (desc) |
| `segments` | segment_id (unique), campaign_id, segment_name |

### Key Design Decisions

- **Auto-generated IDs:** campaign_id and all *_id fields use UUID4 by default
- **Performance score:** Automatically calculated via `model_validator` → `0.7 * click_rate + 0.3 * open_rate`
- **Repository pattern:** Each collection has a dedicated async repository with Motor driver
- **Index creation:** Indexes are ensured automatically on MongoDB connection startup

---

## Task 2.2 – Pydantic Models Implementation ✅

**Completed:** 2026-04-08

### Summary

Enhanced all 5 Pydantic models with strict field validation, custom validators, `to_dict()` serialization methods, and added example data to API schemas.

### Files Updated

| File | Changes |
|------|---------|
| `backend/app/models/customer.py` | Age range tightened to 0-120, `field_validator` for customer_id (non-empty) and location (min 2 chars), `to_dict()` method |
| `backend/app/models/campaign.py` | Budget validation (must be ≥ 0) on `ParsedData`, `field_validator` for campaign_brief (non-empty/trimmed), `to_dict()` method |
| `backend/app/models/variant.py` | Subject line max 100 chars, email body min 50 chars when provided, send_time validator, `to_dict()` method |
| `backend/app/models/metrics.py` | `to_dict()` method added; existing rate validation (0-100), auto-calculated `performance_score` unchanged |
| `backend/app/models/segment.py` | `model_validator` to auto-sync `size` with `len(customer_ids)`, `to_dict()` method |
| `backend/app/models/schemas.py` | `json_schema_extra` examples on `CustomerCreate`, `CampaignCreate`, `VariantCreate`, `MetricsCreate`, `SegmentCreate`; age range updated to 0-120; subject_line max_length on VariantCreate/VariantUpdate; removed explicit `size` from SegmentCreate/SegmentUpdate (auto-calculated) |

### Validation Rules Added

| Model | Validator | Rule |
|-------|-----------|------|
| Customer | `validate_customer_id` | Must not be empty, auto-trimmed |
| Customer | `validate_location` | Must not be empty, min 2 chars, auto-trimmed |
| Customer | `age` field | Range 0-120 |
| Campaign | `validate_brief` | Must not be empty, auto-trimmed |
| ParsedData | `validate_budget` | Must be ≥ 0, rounded to 2 decimal places |
| CampaignVariant | `validate_subject_line` | Max 100 characters |
| CampaignVariant | `validate_email_body` | Min 50 characters when provided |
| Segment | `sync_size_with_customer_ids` | Auto-sets `size = len(customer_ids)` |
| Metrics | `calculate_performance_score` | Auto-sets `0.7 * click_rate + 0.3 * open_rate` |

---

## Task 2.3 – Repository Pattern Implementation ✅

**Completed:** 2026-04-08

### Summary

Created a generic `BaseRepository` with reusable async CRUD, enhanced all 4 entity repositories with specialised query methods, and hardened the MongoDB connection manager with pooling, ping-on-connect, and error handling.

### Files Written / Updated

| File | Description |
|------|-------------|
| `backend/app/db/repositories/base_repository.py` | **NEW** – Generic `BaseRepository[T]` with `create`, `find_by_id`, `find_all`, `update`, `delete`, `count`; logging and error handling |
| `backend/app/db/mongodb.py` | Connection pooling (maxPoolSize=50, minPoolSize=10), `ping` on connect, timeout config, `ConnectionFailure`/`ServerSelectionTimeoutError` handling |
| `backend/app/db/repositories/campaign_repo.py` | Extends `BaseRepository[Campaign]`; added `update_status`, `find_pending_approval`, `find_active_campaigns`, `get_campaign_with_variants` ($lookup aggregation) |
| `backend/app/db/repositories/customer_repo.py` | Extends `BaseRepository[Customer]`; added typed `find_by_criteria(age_range, gender, location, activity_status)`, `get_active_customers`, `bulk_insert_customers`, `get_customer_count_by_segment` |
| `backend/app/db/repositories/variant_repo.py` | Extends `BaseRepository[CampaignVariant]`; added `find_by_segment(segment_name)`, `update_status_bulk`, `get_scheduled_variants(start, end)` |
| `backend/app/db/repositories/metrics_repo.py` | Extends `BaseRepository[Metrics]`; added `find_by_variant` (single latest), `get_top_performers(limit, min_score)`, `get_bottom_performers`, `calculate_campaign_aggregates` ($group pipeline), `get_metrics_time_series` |
| `backend/app/db/repositories/__init__.py` | Added `BaseRepository` to exports |

### Repository Method Matrix

| Repository | Base CRUD | Specialised Methods |
|------------|-----------|---------------------|
| `CampaignRepository` | 6 | `find_by_status`, `update_status`, `find_pending_approval`, `find_active_campaigns`, `get_campaign_with_variants`, `list_all` |
| `CustomerRepository` | 6 | `find_by_criteria`, `get_active_customers`, `bulk_insert_customers`, `get_customer_count_by_segment` |
| `VariantRepository` | 6 | `find_by_campaign`, `find_by_segment`, `update_status_bulk`, `get_scheduled_variants` |
| `MetricsRepository` | 6 | `find_by_variant`, `find_by_campaign`, `get_top_performers`, `get_bottom_performers`, `calculate_campaign_aggregates`, `get_metrics_time_series` |

---

## Task 2.4 – Database Seeding & Mock Data ✅

**Completed:** 2026-04-08

### Summary

Rewrote `seed_data.py` with Faker-powered realistic mock data generation. Created 500 customers, 10 campaigns across all lifecycle stages, 37 variants (3-5 per campaign), 37 metrics records with realistic open/click rates, and 26 segments. Added CLI seeding script.

### Files Written / Updated

| File | Description |
|------|-------------|
| `backend/app/db/migrations/seed_data.py` | **REWRITTEN** – Faker-based generators for all 5 collections with weighted distributions and reproducible seeds |
| `backend/scripts/seed_database.py` | **NEW** – CLI script (`asyncio.run`) to connect MongoDB, seed all collections, print summary |
| `backend/requirements.txt` | Added `faker>=22.0` dependency |

### Data Generation Summary

| Collection | Count | Key Details |
|------------|-------|-------------|
| `customers` | 500 | Ages 18-75; gender weighted 45% male / 45% female / 10% other; status weighted 60% active / 30% inactive / 10% churned; 0-20 purchases; 50 cities |
| `campaigns` | 10 | Template-based with realistic product names, budgets, target audiences; spread across all 6 CampaignStatus stages |
| `campaign_variants` | 37 | 3-5 variants per campaign from 10 variant templates; personalised subject lines and email bodies |
| `metrics` | 37 | 1 per variant; open_rate 15-45%, click_rate 2-8%; auto-calculated performance_score 6.26–18.10 |
| `segments` | 26 | 2-4 per campaign; populated with random customer IDs matching criteria |

### Reference Data Pools

- **50 cities** across US for realistic location distribution
- **15 interest tags** (fitness, tech, fashion, travel, etc.)
- **20 products** across 5 categories (Electronics, Fashion, Health, Home, Food)
- **10 campaign templates** with pre-defined ParsedData (product, budget, target audience, duration)
- **10 variant templates** with 3-5 subject/body variants each

### Reproducibility

- `Faker.seed(42)` and `random.seed(42)` ensure deterministic output across runs
- All generators use weighted distributions for realistic data skew

### Validation Results

```
Customers: 500 (ages 18-75, 50 locations, up to 20 purchases)
Campaigns: 10 (draft×3, pending_approval×1, approved×2, executing×2, completed×1, optimizing×1)
Variants: 37 across 10 campaigns
Metrics: 37 (performance score 6.26–18.10)
Segments: 26
ALL SEED DATA GENERATION TESTS PASSED
```

---

## Task 2.5 – Database Testing & Validation ✅

**Completed:** 2026-04-08

### Summary

Built a comprehensive async test suite for all 4 repository classes using `pytest`, `pytest-asyncio`, and `mongomock-motor` (in-memory MongoDB mock). Covers CRUD operations, specialised queries, Pydantic model validation, and error handling. **97 tests, all passing.**

### Files Written / Updated

| File | Description |
|------|-------------|
| `backend/tests/conftest.py` | **REWRITTEN** – Shared async fixtures: `mock_db` (per-test in-memory MongoDB), `event_loop` (session-scoped), sample data factories for all 5 models |
| `backend/tests/test_repositories/__init__.py` | **NEW** – Package init |
| `backend/tests/test_repositories/test_campaign_repo.py` | **NEW** – 25 tests: CRUD, find_by_status, update_status, find_pending_approval, find_active_campaigns, get_campaign_with_variants, list_all, Pydantic validation, error handling |
| `backend/tests/test_repositories/test_customer_repo.py` | **NEW** – 27 tests: CRUD, find_by_criteria (age/gender/location/status/combined), get_active_customers, bulk_insert, get_customer_count_by_segment, Pydantic validation, error handling |
| `backend/tests/test_repositories/test_variant_repo.py` | **NEW** – 22 tests: CRUD, find_by_campaign, find_by_segment, update_status_bulk (full/empty/partial), get_scheduled_variants (time windows), Pydantic validation, error handling |
| `backend/tests/test_repositories/test_metrics_repo.py` | **NEW** – 23 tests: CRUD, find_by_variant, find_by_campaign, get_top/bottom_performers, calculate_campaign_aggregates, get_metrics_time_series, Pydantic validation, error handling |
| `backend/requirements.txt` | Added `pytest>=9.0`, `pytest-asyncio>=1.0`, `mongomock-motor>=0.0.36` |

### Test Coverage Matrix

| Repository | CRUD | Specialised Queries | Validation | Error Handling | Total |
|------------|------|---------------------|------------|----------------|-------|
| CampaignRepository | 8 | 8 | 6 | 3 | 25 |
| CustomerRepository | 8 | 8 | 7 | 4 | 27 |
| VariantRepository | 6 | 9 | 4 | 3 | 22 |
| MetricsRepository | 6 | 8 | 6 | 3 | 23 |
| **Total** | **28** | **33** | **23** | **13** | **97** |

### Test Categories

- **CRUD Operations:** create, find_by_id (found + not found), update (found + not found), delete (found + not found), count (total + filtered), pagination
- **Specialised Queries:** status filters, demographic criteria, bulk operations, aggregation pipelines, time series, top/bottom performers, $lookup joins
- **Pydantic Validation:** field constraints (age range, budget, rates), auto-calculated fields (performance_score, segment size), string validators (trimming, min/max length), auto-generated UUIDs, to_dict serialization
- **Error Handling:** duplicate inserts (documented mongomock limitation — unique indexes enforced on real MongoDB only)

### Test Infrastructure

- **mongomock-motor:** In-memory async MongoDB mock, fresh DB per test via `mock_db` fixture
- **pytest-asyncio:** `mode=strict`, function-scoped event loops
- **Fixtures:** Session-scoped event loop, per-test mock DB, reusable sample data factories for Customer, Campaign, Variant, Metrics, Segment

### Test Results

```
97 passed in 1.39s
```
