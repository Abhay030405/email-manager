# Phase 2: Database Design & Data Models (Mock Campaign API Rewrite)

## Status: Complete (Rewritten for Mock Campaign API integration)

**Original completion:** 2026-04-08 (97 tests, generic customer model)
**Rewritten:** 2026-04-17 (123 tests, Mock Campaign API aligned)

---

## Overview

Phase 2 was completely rewritten to integrate with the **Mock Campaign API** at `https://mock-campaign-api.onrender.com`. All models, repositories, seed data, and tests now use the API's 18-field Indian customer demographics schema, 0.0–1.0 decimal metrics, and mock_campaign_id tracking.

---

## Task 2.1 – Mock API-Aligned Models ✅

### Customer Model (18 fields + 4 internal)

| Field | Type | Validation |
|-------|------|------------|
| customer_id | str | Regex `^CUST\d{4}$` |
| Full_name | str | Non-empty |
| email | str | Valid email format |
| Age | int | 0–120 |
| Gender | Literal | Male / Female / Other |
| Marital_Status | Literal | Married / Single / Divorced / Widowed (default: Single) |
| Family_Size | int | 1–10 (default: 1) |
| Dependent_count | int | ≥0 (alias: "Dependent count", default: 0) |
| Occupation | str | (default: "") |
| Occupation_type | Literal | Full-time / Part-time / Self-employed / Retired / Student (default: Full-time) |
| Monthly_Income | int | ≥0 (default: 0) |
| KYC_status | Literal Y/N | (alias: "KYC status", default: N) |
| City | str | Required, Indian city name |
| Kids_in_Household | int | ≥0 (default: 0) |
| App_Installed | Literal Y/N | (default: N) |
| Existing_Customer | Literal Y/N | (alias: "Existing Customer", default: N) |
| Credit_score | int | 300–850 (default: 300) |
| Social_Media_Active | Literal Y/N | (default: N) |
| synced_from_mock_api | bool | Internal tracking |
| last_synced_at | Optional[datetime] | Internal tracking |
| created_at / updated_at | datetime | Auto-set |

**Key:** `from_mock_api()` classmethod handles alias fields. `populate_by_name=True` for both alias and field name access.

### Campaign Model

Added `mock_campaign_id: Optional[str]` and `scheduled_time: Optional[datetime]`. Budget changed to `Optional[float]`.

### Variant Model

- `subject_line` max 200 chars (was 100)
- `email_body` max 5000 chars (removed min 50 check)
- Added `mock_campaign_id`, `customer_ids: list[str]`, `campaign_metadata: Optional[dict]`, `variant_type`
- `to_mock_api_payload()` method for API scheduling

### Metrics Model

- All rates 0.0–1.0 (was 0–100): `open_rate`, `click_rate`, `click_through_rate`
- `mock_campaign_id` REQUIRED
- `total_sent`, `unique_opens`, `unique_clicks` (replaced emails_sent/opened/clicked)
- `calculated_at` / `collected_at` timestamps (replaced `timestamp`)
- Percentage convenience properties: `open_rate_percentage`, `click_rate_percentage`, `ctr_percentage`
- `from_mock_api()` classmethod
- Performance score: `0.7 * click_rate + 0.3 * open_rate`

### Segment Model

- `SegmentCriteria` uses Mock API fields: `age_range` dict, `cities` list, `occupation_type`, `min_income`/`max_income`, `credit_score_range` dict, `app_installed`/`social_media_active`/`existing_customer` (Y/N)
- `matches_customer()` method for segment evaluation

### Schemas

- 7 Mock API schemas added: `MockAPICustomerResponse`, `MockAPICampaignScheduleRequest/Response`, `MockAPIMetricsResponse`, `MockAPICustomerResultResponse`, `MockAPIValidateRequest/Response`
- All Create/Update/Response schemas updated for new field names

---

## Task 2.2 – Repository Pattern (Mock API Methods) ✅

### New/Updated Repository Methods

| Repository | New Methods |
|------------|------------|
| BaseRepository | `bulk_insert(documents)` via insert_many |
| CustomerRepository | `sync_from_mock_api(customers)` (upsert), `get_synced_customer_count()`, `validate_customer_ids(ids)`, rewritten `find_by_criteria()` with Mock API fields |
| CampaignRepository | `find_by_mock_campaign_id()`, `update_mock_campaign_id()` |
| VariantRepository | `find_by_mock_campaign_id()`, `update_mock_campaign_id()`, `get_variants_ready_for_execution()` |
| MetricsRepository | `create_from_mock_api()`, `update_from_mock_api()`, `get_latest_by_mock_campaign_id()`, `get_performance_distribution()` |

### Removed Methods

- `CustomerRepository.get_active_customers()`, `bulk_insert_customers()` (replaced by Mock API sync)

---

## Task 2.3 – Seed Data (Mock API Fetch) ✅

- Removed Faker dependency; now fetches customers from Mock API with `httpx.AsyncClient`
- Batch fetching (1000/batch, up to 5000 customers) with 60s timeout and 3 retries
- 10 Indian-context campaign templates (Diwali, KYC savings, back-to-school, app download, etc.)
- Metrics use 0.0–1.0 rates
- Segments use Indian cities and Mock API criteria fields

---

## Task 2.4 – Testing ✅

**123 tests passing** across 4 test files:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_campaign_repo.py | 28 | CRUD + status workflow + mock_campaign_id methods |
| test_customer_repo.py | 35 | CRUD + all find_by_criteria params + sync + validate + from_mock_api + validation |
| test_variant_repo.py | 27 | CRUD + scheduling + Mock API methods + payload + validation |
| test_metrics_repo.py | 33 | CRUD + aggregates + time series + Mock API methods + validation |

### Test Fixtures (Indian Context)

- `sample_customer`: CUST0001, Ravi Sharma, Mumbai, Age 30
- `sample_customers`: 5 diverse Indian customers (Priya/Kolkata, Amit/Delhi, Sanjay/Kolkata, Meena/Mumbai, Rahul/Bangalore)
- All metrics fixtures use 0.0–1.0 rates with mock_campaign_id

---

## Configuration Changes

| Setting | Value |
|---------|-------|
| `MOCK_CAMPAIGN_API_URL` | `https://mock-campaign-api.onrender.com` |
| `MOCK_API_TIMEOUT` | 60 seconds |
| `ENVIRONMENT` | development |

---

## Collections & Indexes (Updated)

| Collection | Indexes |
|------------|---------|
| `customers` | customer_id (unique), compound (Gender, Age, City) |
| `campaigns` | campaign_id (unique), status, mock_campaign_id, created_at (desc) |
| `campaign_variants` | variant_id (unique), campaign_id, mock_campaign_id, segment_name, status |
| `metrics` | metric_id (unique), variant_id, campaign_id, mock_campaign_id, performance_score (desc), calculated_at (desc) |
| `segments` | segment_id (unique), campaign_id, segment_name |
