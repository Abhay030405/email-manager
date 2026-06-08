# Mock Campaign API — Complete Reference

> **Local base URL:** `http://localhost:8000`
> **Deployed base URL:** `https://mock-campaign-api.onrender.com`
> **Interactive docs:** `http://localhost:8000/docs` (Swagger UI) | `http://localhost:8000/redoc` (ReDoc)

---

## Table of Contents

1. [General Notes](#general-notes)
2. [Root & Health](#1-root--health)
3. [Customers](#2-customers)
   - [GET /api/customers](#21-get-apicustomers)
   - [GET /api/customers/count](#22-get-apicustomerscount)
   - [GET /api/customers/{customer_id}](#23-get-apicustomerscustomer_id)
   - [POST /api/customers/validate](#24-post-apicustomersvalidate)
   - [POST /api/customers/filter](#25-post-apicustomersfilter)
4. [Campaigns](#3-campaigns)
   - [POST /api/campaigns/schedule](#31-post-apicampaignsschedule)
   - [GET /api/campaigns/{campaign_id}](#32-get-apicampaignscampaign_id)
   - [GET /api/campaigns/{campaign_id}/metrics](#33-get-apicampaignscampaign_idmetrics)
   - [GET /api/campaigns/{campaign_id}/results](#34-get-apicampaignscampaign_idresults)
5. [Customer Object Schema](#customer-object-schema)
6. [Simulation Logic](#simulation-logic)
7. [Error Responses](#error-responses)

---

## General Notes

- All request and response bodies are **JSON**.
- All dates/times are **ISO 8601** strings (e.g. `2026-06-10T09:00:00Z`).
- Rates (`open_rate`, `click_rate`, `click_through_rate`) are **decimals between 0.0 and 1.0** — multiply by 100 for percentages.
- `campaign_id` is a **UUID v4** generated on each schedule call.
- Metrics are **simulated instantly** — no background jobs, no waiting.
- Campaign data and results are stored in flat JSON files (`campaigns.json`, `results.json`) on the server. They reset on every Render redeploy (free tier has an ephemeral filesystem).

---

## 1. Root & Health

### `GET /`

Returns basic API info and docs link.

**Response `200`:**
```json
{
  "message": "Mock Campaign API",
  "docs": "/docs"
}
```

---

### `GET /health`

Health check — confirms the API is running and reports how many customers are loaded.

**Response `200`:**
```json
{
  "status": "healthy",
  "customers_loaded": 5000,
  "version": "1.0.0"
}
```

---

## 2. Customers

### 2.1 `GET /api/customers`

Returns the full customer cohort with optional pagination.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `5000` | Max number of customers to return |
| `offset` | integer | `0` | Number of customers to skip |

**Example:**
```
GET /api/customers?limit=3&offset=0
```

**Response `200`:** Array of [Customer objects](#customer-object-schema).

```json
[
  {
    "customer_id": "CUST0001",
    "Full_name": "Suresh Kapoor",
    "email": "suresh.kapoor1@example.com",
    "Age": 41,
    "Gender": "Male",
    "Marital_Status": "Married",
    "Family_Size": 3,
    "Dependent count": 1,
    "Occupation": "Engineer",
    "Occupation type": "Full-time",
    "Monthly_Income": 48267,
    "KYC status": "N",
    "City": "Kolkata",
    "Kids_in_Household": 1,
    "App_Installed": "Y",
    "Existing Customer": "N",
    "Credit score": 604,
    "Social_Media_Active": "Y"
  }
]
```

---

### 2.2 `GET /api/customers/count`

Returns the total number of customers in the cohort.

**Response `200`:**
```json
{
  "total_customers": 5000
}
```

---

### 2.3 `GET /api/customers/{customer_id}`

Returns a single customer by ID.

**Path Parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `customer_id` | string | e.g. `CUST0001` |

**Response `200`:** A single [Customer object](#customer-object-schema).

**Response `404`:**
```json
{
  "detail": "Customer CUST9999 not found"
}
```

---

### 2.4 `POST /api/customers/validate`

Checks whether all provided customer IDs exist in the database. Useful before scheduling a campaign.

**Request Body:**
```json
{
  "customer_ids": ["CUST0001", "CUST0002", "FAKE_ID_999"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer_ids` | `string[]` | Yes | List of customer IDs to validate |

**Response `200` — some invalid:**
```json
{
  "valid": false,
  "invalid_ids": ["FAKE_ID_999"]
}
```

**Response `200` — all valid:**
```json
{
  "valid": true,
  "invalid_ids": []
}
```

---

### 2.5 `POST /api/customers/filter`

Filters the customer cohort and returns matching customer IDs and count.

- All fields are **optional** — omit any field to skip that filter.
- `gender`, `marital_status`, `occupation`, `occupation_type`, and `city` accept **arrays** (OR logic — a customer matches if they belong to any of the provided values).
- Numeric range fields (`min_age`, `max_age`, etc.) are **inclusive** on both ends.

**Request Body:**
```json
{
  "min_age": 25,
  "max_age": 45,
  "gender": ["Male", "Female"],
  "marital_status": ["Married", "Single"],
  "family_size": 3,
  "dependent_count": 1,
  "occupation": ["Engineer", "Doctor"],
  "occupation_type": ["Professional", "Self-employed"],
  "min_monthly_income": 30000,
  "max_monthly_income": 100000,
  "kyc_status": "Y",
  "city": ["Mumbai", "Delhi", "Bangalore"],
  "kids_in_household": 2,
  "app_installed": "Y",
  "existing_customer": "N",
  "min_credit_score": 700,
  "social_media_active": "Y"
}
```

**All fields with types:**

| Field | Type | Filter behaviour |
|-------|------|-----------------|
| `min_age` | integer \| null | Age >= value |
| `max_age` | integer \| null | Age <= value |
| `gender` | string[] \| null | Exact match (any of) |
| `marital_status` | string[] \| null | Exact match (any of) |
| `family_size` | integer \| null | Exact match |
| `dependent_count` | integer \| null | Exact match |
| `occupation` | string[] \| null | Exact match (any of) |
| `occupation_type` | string[] \| null | Exact match (any of) |
| `min_monthly_income` | integer \| null | Monthly_Income >= value |
| `max_monthly_income` | integer \| null | Monthly_Income <= value |
| `kyc_status` | string \| null | Exact match (`"Y"` or `"N"`) |
| `city` | string[] \| null | Exact match (any of) |
| `kids_in_household` | integer \| null | Exact match |
| `app_installed` | string \| null | Exact match (`"Y"` or `"N"`) |
| `existing_customer` | string \| null | Exact match (`"Y"` or `"N"`) |
| `min_credit_score` | integer \| null | Credit_score >= value |
| `social_media_active` | string \| null | Exact match (`"Y"` or `"N"`) |

**Response `200`:**
```json
{
  "count": 47,
  "customer_ids": ["CUST0012", "CUST0089", "CUST0134"]
}
```

**Example — young professionals in Mumbai or Delhi:**
```json
{
  "min_age": 22,
  "max_age": 35,
  "occupation_type": ["Professional"],
  "city": ["Mumbai", "Delhi"],
  "app_installed": "Y"
}
```

---

## 3. Campaigns

### 3.1 `POST /api/campaigns/schedule`

Schedules an email campaign for a list of customers. Metrics are **calculated immediately** (simulated) and are available right away via the metrics and results endpoints.

**Request Body:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `customer_ids` | `string[]` | Yes | Non-empty, all IDs must exist | List of target customer IDs |
| `subject` | string | Yes | Max 200 chars, non-empty | Email subject line |
| `body` | string | Yes | Max 5000 chars, non-empty | Email body content |
| `scheduled_time` | datetime | Yes | ISO 8601 | When the email will be sent |
| `segment_name` | string \| null | No | — | Label for the customer segment |
| `variant_id` | string \| null | No | — | A/B test variant identifier |
| `campaign_metadata` | object \| null | No | — | Any additional metadata |

**Example Request:**
```json
{
  "customer_ids": ["CUST0001", "CUST0002", "CUST0003"],
  "subject": "🎉 Exclusive Offer: Higher Returns Await You!",
  "body": "Dear Customer,\n\nDiscover <b>XDeposit</b>, offering <b>1% higher returns</b> than competitors!\n\nClick here to explore: https://example.com/offer\n\nLimited time offer - Act now! 💰\n\nBest regards,\nThe Team",
  "scheduled_time": "2026-06-10T09:00:00Z",
  "segment_name": "young_professionals",
  "variant_id": "var_A",
  "campaign_metadata": {
    "source": "hackathon",
    "product": "XDeposit"
  }
}
```

**Response `201`:**
```json
{
  "campaign_id": "7d058918-35a2-4af5-b5fb-efd3d21cc4a6",
  "status": "scheduled",
  "total_customers": 3,
  "scheduled_time": "2026-06-10T09:00:00Z",
  "message": "Campaign scheduled successfully. Metrics available at /api/campaigns/7d058918-35a2-4af5-b5fb-efd3d21cc4a6/metrics"
}
```

**Error `400` — empty customer_ids:**
```json
{ "detail": "customer_ids must not be empty" }
```

**Error `400` — invalid customer ID:**
```json
{ "detail": "Customer IDs not found: ['FAKE_ID']" }
```

**Error `400` — empty subject or body:**
```json
{ "detail": "subject must not be empty" }
```

> **Tip:** Use `POST /api/customers/filter` first to get your target customer IDs, then pass them into this endpoint.

---

### 3.2 `GET /api/campaigns/{campaign_id}`

Returns full campaign details including subject, body, customer list, timestamps, and embedded metrics (if results exist).

**Path Parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `campaign_id` | string (UUID) | Returned from the schedule endpoint |

**Response `200`:**
```json
{
  "campaign_id": "7d058918-35a2-4af5-b5fb-efd3d21cc4a6",
  "subject": "🎉 Exclusive Offer: Higher Returns Await You!",
  "body": "Dear Customer...",
  "customer_ids": ["CUST0001", "CUST0002", "CUST0003"],
  "scheduled_time": "2026-06-10T09:00:00",
  "segment_name": "young_professionals",
  "variant_id": "var_A",
  "campaign_metadata": { "source": "hackathon", "product": "XDeposit" },
  "created_at": "2026-06-08T11:30:00.123456",
  "status": "scheduled",
  "metrics": {
    "total_sent": 3,
    "unique_opens": 2,
    "unique_clicks": 1,
    "open_rate": 0.6667,
    "click_rate": 0.3333,
    "click_through_rate": 0.5
  }
}
```

> `metrics` is only included if results have been calculated (always the case right after scheduling).

**Response `404`:**
```json
{ "detail": "Campaign 00000000-0000-0000-0000-000000000000 not found" }
```

---

### 3.3 `GET /api/campaigns/{campaign_id}/metrics`

Returns aggregated performance metrics for a campaign.

**Path Parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `campaign_id` | string (UUID) | Campaign to fetch metrics for |

**Response `200`:**
```json
{
  "campaign_id": "7d058918-35a2-4af5-b5fb-efd3d21cc4a6",
  "total_sent": 3,
  "unique_opens": 2,
  "unique_clicks": 1,
  "open_rate": 0.6667,
  "click_rate": 0.3333,
  "click_through_rate": 0.5,
  "calculated_at": "2026-06-08T11:30:01.234567"
}
```

**Field Definitions:**

| Field | Formula | Range |
|-------|---------|-------|
| `total_sent` | Count of `customer_ids` | — |
| `unique_opens` | Count of customers who opened | — |
| `unique_clicks` | Count of customers who clicked | — |
| `open_rate` | `unique_opens / total_sent` | 0.0 – 1.0 |
| `click_rate` | `unique_clicks / total_sent` | 0.0 – 1.0 |
| `click_through_rate` | `unique_clicks / unique_opens` | 0.0 – 1.0 |

**Response `404`:**
```json
{ "detail": "Campaign 00000000-0000-0000-0000-000000000000 not found" }
```

---

### 3.4 `GET /api/campaigns/{campaign_id}/results`

Returns per-customer open/click outcomes for debugging and analysis.

**Path Parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `campaign_id` | string (UUID) | Campaign to fetch results for |

**Query Parameter:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `100` | Max number of results to return |

**Response `200`:** Array of customer result objects.

```json
[
  {
    "campaign_id": "7d058918-35a2-4af5-b5fb-efd3d21cc4a6",
    "customer_id": "CUST0001",
    "opened": true,
    "clicked": false,
    "open_probability": 0.4823,
    "click_probability": 0.2145
  },
  {
    "campaign_id": "7d058918-35a2-4af5-b5fb-efd3d21cc4a6",
    "customer_id": "CUST0002",
    "opened": false,
    "clicked": false,
    "open_probability": 0.3201,
    "click_probability": 0.1876
  },
  {
    "campaign_id": "7d058918-35a2-4af5-b5fb-efd3d21cc4a6",
    "customer_id": "CUST0003",
    "opened": true,
    "clicked": true,
    "open_probability": 0.5412,
    "click_probability": 0.3034
  }
]
```

> `clicked` can only be `true` if `opened` is also `true`.
> `open_probability` and `click_probability` are the computed probabilities used to randomly determine `opened` and `clicked`.

**Response `404`:**
```json
{ "detail": "Campaign 00000000-0000-0000-0000-000000000000 not found" }
```

---

## Customer Object Schema

Every customer object returned by the API has the following shape:

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `customer_id` | string | `"CUST0001"` | Unique identifier |
| `Full_name` | string | `"Suresh Kapoor"` | Full name |
| `email` | string | `"suresh@example.com"` | Email address |
| `Age` | integer | `41` | Age in years |
| `Gender` | string | `"Male"`, `"Female"` | |
| `Marital_Status` | string | `"Married"`, `"Single"` | |
| `Family_Size` | integer | `3` | Total family members |
| `Dependent count` | integer | `1` | Number of dependents |
| `Occupation` | string | `"Engineer"` | Job title / role |
| `Occupation type` | string | `"Professional"`, `"Student"`, `"Self-employed"`, `"Retired"`, `"Full-time"` | Category |
| `Monthly_Income` | integer | `48267` | Monthly income in INR |
| `KYC status` | string | `"Y"`, `"N"` | KYC verified |
| `City` | string | `"Mumbai"` | City of residence |
| `Kids_in_Household` | integer | `1` | Number of children at home |
| `App_Installed` | string | `"Y"`, `"N"` | Has the mobile app |
| `Existing Customer` | string | `"Y"`, `"N"` | Existing vs new customer |
| `Credit score` | integer | `604` | Credit score |
| `Social_Media_Active` | string | `"Y"`, `"N"` | Active on social media |

---

## Simulation Logic

When a campaign is scheduled, every customer gets a simulated `opened` and `clicked` outcome based on three factor groups.

### Base Rates
| Metric | Base Rate |
|--------|-----------|
| Open probability | 35% |
| Click probability | 8% |

### Factor 1 — Subject Line (affects open probability)

| Condition | Modifier |
|-----------|----------|
| Length 40–60 chars | +5% |
| Length < 20 chars | −8% |
| Length > 80 chars | −10% |
| Contains emoji | +3% |
| Contains `you` / `your` | +4% |
| Contains `limited`, `now`, `today`, `hurry` | +6% |
| Contains `!!!`, `FREE!!!`, `ACT NOW!!!` | −15% |

### Factor 2 — Body Content (affects click probability)

| Condition | Modifier |
|-----------|----------|
| Word count 100–200 | +5% |
| Word count < 50 | −5% |
| Word count > 300 | −8% |
| Contains `https://` link | +10% |
| Contains `<b>`, `<strong>`, `<i>`, `<em>` | +3% |
| Contains emoji | +2% |
| Contains `higher returns`, `earn more`, `save`, `benefit` | +8% |
| Contains `limited`, `now`, `today`, `hurry`, `urgent` | +6% |
| Contains `!!!`, `FREE!!!`, `ACT NOW!!!` | −10% |

### Factor 3 — Send Timing (affects both)

**Day of week:**
| Day | Modifier |
|-----|----------|
| Tuesday / Wednesday | +8% |
| Monday | +3% |
| Thursday | +2% |
| Friday | −5% |
| Saturday / Sunday | −12% |

**Time of day:**
| Time (24h) | Modifier |
|------------|----------|
| 08:00–10:00 | +10% |
| 10:00–12:00 | +5% |
| 12:00–14:00 | −3% |
| 14:00–16:00 | +3% |
| 16:00–18:00 | 0% |
| 18:00–08:00 | −10% |

### Factor 4 — Customer Demographics (affects both)

| Condition | Open | Click |
|-----------|------|-------|
| Age 18–25 | +5% | +3% |
| Age 26–40 | +3% | +2% |
| Age 56+ | −8% | −5% |
| Female AND Age ≥ 60 | — | +10% |
| Social media active | +5% | +2% |
| Social media inactive | −3% | — |
| Occupation: Professional | +8% | — |
| Occupation: Self-employed | +2% | — |
| Occupation: Retired | −5% | — |
| Occupation: Student | — | +3% |
| App installed | — | +10% |
| Credit score > 750 | — | +5% |
| Credit score 650–750 | — | +2% |
| Credit score < 650 | — | −3% |
| Random noise | ±3% | ±3% |

**Final clamp:** Open → 5%–90% | Click → 2%–60%

### Outcome Determination
```
opened = random() < open_probability
clicked = opened AND random() < click_probability
```
A customer can only click if they opened the email first.

---

## Error Responses

All errors follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | When it happens |
|--------|----------------|
| `400` | Bad request — empty `customer_ids`, invalid IDs, blank subject/body |
| `404` | Customer or campaign not found |
| `422` | Request body fails schema validation (wrong types, missing required fields, exceeds max length) |
| `500` | Unexpected server error — check `.logs/app.log` |

### Validation Error Shape (`422`)
```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["body", "subject"],
      "msg": "String should have at most 200 characters",
      "input": "...",
      "ctx": { "max_length": 200 }
    }
  ]
}
```

---

## Endpoint Summary

| # | Method | Endpoint | Status Codes |
|---|--------|----------|--------------|
| 1 | `GET` | `/` | `200` |
| 2 | `GET` | `/health` | `200` |
| 3 | `GET` | `/api/customers` | `200` |
| 4 | `GET` | `/api/customers/count` | `200` |
| 5 | `GET` | `/api/customers/{customer_id}` | `200`, `404` |
| 6 | `POST` | `/api/customers/validate` | `200` |
| 7 | `POST` | `/api/customers/filter` | `200` |
| 8 | `POST` | `/api/campaigns/schedule` | `201`, `400`, `422` |
| 9 | `GET` | `/api/campaigns/{campaign_id}` | `200`, `404` |
| 10 | `GET` | `/api/campaigns/{campaign_id}/metrics` | `200`, `404` |
| 11 | `GET` | `/api/campaigns/{campaign_id}/results` | `200`, `404` |
