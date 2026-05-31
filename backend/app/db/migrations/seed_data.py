"""Seed data for initial database population.

Customers are fetched from the Mock Campaign API (5 000 records).
Campaigns, variants, metrics, and segments are generated locally with
Indian-context templates aligned to the Mock API schema.
"""

import logging
from datetime import datetime, timedelta
import random

import httpx

from app.core.config import get_settings
from app.models.customer import Customer
from app.models.campaign import Campaign, CampaignStatus, ParsedData
from app.models.variant import CampaignVariant, VariantStatus
from app.models.metrics import Metrics
from app.models.segment import Segment, SegmentCriteria

logger = logging.getLogger(__name__)
random.seed(42)

MOCK_API_BASE = get_settings().MOCK_CAMPAIGN_API_URL
MOCK_API_TIMEOUT = get_settings().MOCK_API_TIMEOUT

# ── Indian-context campaign templates ─────────────────────────────

CAMPAIGN_TEMPLATES = [
    {
        "brief": "Launch Diwali sale for premium electronics targeting urban males aged 25-40 in Mumbai and Delhi. Budget ₹5,00,000. CTA: https://example.com/diwali-sale",
        "parsed": ParsedData(product_name="Premium Electronics Diwali Offer", target_audience="Urban males aged 25-40 in metro cities", campaign_goal="Drive 15% conversion rate", cta_link="https://example.com/diwali-sale", budget=500000.0),
        "segments": ["urban_young_males", "metro_tech_enthusiasts", "high_income_diwali"],
    },
    {
        "brief": "Promote KYC-verified savings account for existing customers in Kolkata and Chennai with credit scores above 700. Budget ₹3,00,000.",
        "parsed": ParsedData(product_name="Premium Savings Account", target_audience="KYC-verified existing customers in Tier-1 cities", campaign_goal="Open 5000 new accounts", cta_link="https://example.com/savings", budget=300000.0),
        "segments": ["kyc_verified_high_credit", "existing_metro_customers"],
    },
    {
        "brief": "Back-to-school campaign for families with kids targeting parents aged 30-50 across all cities. Budget ₹2,00,000.",
        "parsed": ParsedData(product_name="Back to School Bundle", target_audience="Parents with kids in household", campaign_goal="Drive 12% conversion", cta_link="https://example.com/school", budget=200000.0),
        "segments": ["parents_with_kids", "family_oriented"],
    },
    {
        "brief": "App download push for non-app users on social media. Target social-media-active users aged 18-35. Budget ₹1,50,000.",
        "parsed": ParsedData(product_name="Mobile App", target_audience="Social-media-active users without app", campaign_goal="50K downloads in 30 days", cta_link="https://example.com/app", budget=150000.0),
        "segments": ["social_no_app", "young_digital_natives"],
    },
    {
        "brief": "Re-engage non-existing customers with introductory offer. Self-employed and part-time workers in Tier-2 cities. Budget ₹1,00,000.",
        "parsed": ParsedData(product_name="New Customer Welcome Offer", target_audience="Non-existing customers in smaller cities", campaign_goal="Convert 10% to new customers", cta_link="https://example.com/welcome", budget=100000.0),
        "segments": ["non_existing_self_employed", "tier2_prospects"],
    },
    {
        "brief": "Premium credit card upsell for high-credit-score married professionals. Budget ₹4,00,000.",
        "parsed": ParsedData(product_name="Platinum Credit Card", target_audience="Married professionals with credit score 750+", campaign_goal="8% upgrade rate", cta_link="https://example.com/platinum", budget=400000.0),
        "segments": ["high_credit_married", "full_time_professionals"],
    },
    {
        "brief": "Student discount program for college students aged 18-25. Budget ₹80,000.",
        "parsed": ParsedData(product_name="Student Discount Program", target_audience="Students aged 18-25", campaign_goal="Enroll 10000 students", cta_link="https://example.com/students", budget=80000.0),
        "segments": ["college_students", "young_budget_conscious"],
    },
    {
        "brief": "Financial literacy webinar for retired customers. Emphasize ease and trust. Budget ₹60,000.",
        "parsed": ParsedData(product_name="Financial Literacy Webinar", target_audience="Retired customers", campaign_goal="500 webinar registrations", cta_link="https://example.com/webinar", budget=60000.0),
        "segments": ["retired_customers", "senior_digital_learners"],
    },
    {
        "brief": "Festive personal loan campaign for salaried employees in Bangalore and Hyderabad. Budget ₹6,00,000.",
        "parsed": ParsedData(product_name="Festive Personal Loan", target_audience="Full-time salaried in Bangalore/Hyderabad", campaign_goal="Disburse 2000 loans", cta_link="https://example.com/loan", budget=600000.0),
        "segments": ["salaried_south_metro", "high_income_full_time"],
    },
    {
        "brief": "Women's Day special campaign for female customers across all cities. Highlight exclusive offers. Budget ₹2,50,000.",
        "parsed": ParsedData(product_name="Women's Day Special", target_audience="Female customers all cities", campaign_goal="25% engagement increase", cta_link="https://example.com/womensday", budget=250000.0),
        "segments": ["all_female_customers", "working_women", "female_app_users"],
    },
]

# ── Variant templates (Indian context) ────────────────────────────

VARIANT_TEMPLATES = [
    [
        ("Diwali Dhamaka – Premium Electronics Sale!", "<h1>Light Up Your Diwali</h1><p>Exclusive deals on top electronics. Limited period offer for metro customers.</p>"),
        ("This Diwali, Upgrade Your Tech", "<h1>Festival of Deals</h1><p>Premium gadgets at festive prices. Shop now and celebrate with savings.</p>"),
        ("Don't Miss the Diwali Electronics Rush", "<h1>Diwali Countdown</h1><p>Biggest discounts of the year on premium electronics. Hurry, stock is limited!</p>"),
    ],
    [
        ("Secure Your Savings – Open Premium Account Today", "<h1>Your Money, Better Protected</h1><p>As a KYC-verified customer, unlock premium savings with higher interest rates.</p>"),
        ("Exclusive for Verified Customers – Premium Savings", "<h1>Premium Benefits Await</h1><p>Higher returns, zero hassle. Open your premium savings account in minutes.</p>"),
    ],
    [
        ("School Season Sorted – All-in-One Bundle", "<h1>Back to School Made Easy</h1><p>Everything your child needs, bundled at great prices. Order now for early delivery.</p>"),
        ("Parents, Save Big This School Season", "<h1>Smart Savings for Smart Families</h1><p>Quality school supplies at affordable prices. Bundle discounts up to 35% off.</p>"),
        ("Get Ready for School – Special Family Offer", "<h1>Family-First Savings</h1><p>Backpacks, books, and electronics – all at special family rates.</p>"),
    ],
    [
        ("Download Our App & Get Exclusive Rewards", "<h1>Your Pocket Companion</h1><p>All deals, all services, at your fingertips. Download now for instant rewards.</p>"),
        ("Social Media Star? Get App-Only Deals!", "<h1>App-Exclusive Offers</h1><p>We know you love deals. Get the best ones only on our mobile app.</p>"),
    ],
    [
        ("Welcome Aboard – Special Introductory Offer", "<h1>New Here? We've Got You Covered</h1><p>Exclusive welcome benefits for new customers. Start your journey with us today.</p>"),
        ("Start Fresh with Our Welcome Package", "<h1>Hello, New Friend!</h1><p>Special rates and benefits designed just for you. Sign up and save.</p>"),
    ],
    [
        ("Upgrade to Platinum – You've Earned It", "<h1>Platinum Awaits</h1><p>Your excellent credit score qualifies you for our premium Platinum Credit Card.</p>"),
        ("Exclusive Platinum Card for Top Customers", "<h1>The Card You Deserve</h1><p>Premium rewards, airport lounge access, and cashback. Apply now.</p>"),
        ("Limited Offer: Platinum Card – Zero Joining Fee", "<h1>Premium, No Catch</h1><p>Apply today and enjoy zero joining fee on our Platinum Credit Card.</p>"),
    ],
    [
        ("Students Save More – Exclusive Discount Program", "<h1>Student Perks</h1><p>Special discounts across categories for enrolled students. Verify and save.</p>"),
        ("College Life, Better Prices", "<h1>Study Hard, Save Smart</h1><p>Exclusive student pricing on essentials. Valid with student ID verification.</p>"),
    ],
    [
        ("Learn to Grow Your Wealth – Free Webinar", "<h1>Financial Freedom Starts Here</h1><p>Join our free webinar on smart financial planning for your retirement years.</p>"),
        ("Expert Financial Advice – Register Now", "<h1>Plan Your Future</h1><p>Our experts share tips on maximizing your savings. Limited seats available.</p>"),
    ],
    [
        ("Festive Personal Loan at Best Rates", "<h1>Celebrate Without Worry</h1><p>Quick approval, low interest, flexible tenure. Apply for your festive loan today.</p>"),
        ("Your Festival Plans Deserve the Best Loan", "<h1>Instant Approval</h1><p>Get funds in 24 hours. Special festive rates for salaried professionals.</p>"),
        ("Don't Wait – Festive Loan Offer Ends Soon", "<h1>Last Few Days</h1><p>Our lowest interest rates of the year. Apply before the festive window closes.</p>"),
    ],
    [
        ("Celebrating You – Women's Day Special", "<h1>Because You Deserve It</h1><p>Exclusive offers curated just for you. Celebrate Women's Day with amazing deals.</p>"),
        ("Empowered Women, Empowered Offers", "<h1>Strength in Savings</h1><p>Special Women's Day discounts across all categories. Shop and celebrate.</p>"),
        ("Happy Women's Day – Exclusive Rewards Inside", "<h1>Our Gift to You</h1><p>Unlock special rewards and cashback this Women's Day. Valid for a limited time.</p>"),
    ],
]


# ── Fetch customers from Mock API ─────────────────────────────────


async def fetch_customers_from_mock_api(
    batch_size: int = 1000,
    max_customers: int = 5000,
    max_retries: int = 3,
) -> list[Customer]:
    """Fetch customers from the Mock Campaign API with retry logic.

    Handles Render cold starts (30-50 s) by using a long timeout and retries.
    """
    customers: list[Customer] = []
    offset = 0

    async with httpx.AsyncClient(timeout=MOCK_API_TIMEOUT) as client:
        while offset < max_customers:
            url = f"{MOCK_API_BASE}/api/customers?limit={batch_size}&offset={offset}"
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info("Fetching customers offset=%d attempt=%d", offset, attempt)
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    logger.warning("Attempt %d failed: %s", attempt, exc)
                    if attempt == max_retries:
                        logger.error("All retries exhausted for offset=%d", offset)
                        return customers
            else:
                break

            # data may be a list or a dict with a 'customers' key
            records = data if isinstance(data, list) else data.get("customers", [])
            if not records:
                break

            for record in records:
                try:
                    customer = Customer.from_mock_api(record)
                    customers.append(customer)
                except Exception as exc:
                    logger.warning("Skipping invalid customer record: %s", exc)

            offset += batch_size
            logger.info("Fetched %d customers so far", len(customers))

    logger.info("Total customers fetched from Mock API: %d", len(customers))
    return customers


# ── Generator helpers ─────────────────────────────────────────────


def generate_seed_campaigns() -> list[Campaign]:
    """Generate 10 sample campaigns from Indian-context templates."""
    campaigns: list[Campaign] = []
    statuses = [
        CampaignStatus.DRAFT,
        CampaignStatus.PENDING_APPROVAL,
        CampaignStatus.APPROVED,
        CampaignStatus.EXECUTING,
        CampaignStatus.COMPLETED,
        CampaignStatus.OPTIMIZING,
        CampaignStatus.DRAFT,
        CampaignStatus.APPROVED,
        CampaignStatus.EXECUTING,
        CampaignStatus.DRAFT,
    ]
    for idx, tmpl in enumerate(CAMPAIGN_TEMPLATES):
        campaign = Campaign(
            campaign_brief=tmpl["brief"],
            parsed_data=tmpl["parsed"],
            status=statuses[idx],
            segments=tmpl["segments"],
            created_by="marketing_team",
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
        )
        campaigns.append(campaign)
    return campaigns


def generate_seed_variants(campaigns: list[Campaign]) -> list[CampaignVariant]:
    """Generate 2-5 variants per campaign from templates."""
    all_variants: list[CampaignVariant] = []
    for idx, campaign in enumerate(campaigns):
        templates = VARIANT_TEMPLATES[idx]
        segment_names = campaign.segments
        for v_idx, (subject, body) in enumerate(templates):
            variant = CampaignVariant(
                campaign_id=campaign.campaign_id,
                segment_name=segment_names[v_idx % len(segment_names)],
                subject_line=subject,
                email_body=body,
                send_time=datetime.utcnow() + timedelta(days=random.randint(1, 30)),
                variant_type=f"var_{v_idx + 1}",
                personalization_tags=random.sample(
                    ["Full_name", "City", "Occupation", "Credit_score"],
                    k=random.randint(1, 3),
                ),
                status=VariantStatus.DRAFT,
            )
            all_variants.append(variant)
    return all_variants


def generate_seed_metrics(variants: list[CampaignVariant]) -> list[Metrics]:
    """Generate realistic metrics (0.0–1.0 rates) for each variant."""
    metrics_list: list[Metrics] = []
    for variant in variants:
        open_rate = round(random.uniform(0.15, 0.45), 4)
        click_rate = round(random.uniform(0.02, 0.15), 4)
        ctr = round(random.uniform(0.01, 0.10), 4)
        sent = random.randint(500, 5000)
        unique_opens = int(sent * open_rate)
        unique_clicks = int(sent * click_rate)

        m = Metrics(
            variant_id=variant.variant_id,
            campaign_id=variant.campaign_id,
            mock_campaign_id=f"mock_{variant.variant_id[:8]}",
            open_rate=open_rate,
            click_rate=click_rate,
            click_through_rate=ctr,
            total_sent=sent,
            unique_opens=unique_opens,
            unique_clicks=unique_clicks,
        )
        metrics_list.append(m)
    return metrics_list


def generate_seed_segments(
    campaigns: list[Campaign], customers: list[Customer]
) -> list[Segment]:
    """Generate segments matching Mock API customer fields."""
    INDIAN_CITIES = [
        "Mumbai", "Delhi", "Bangalore", "Kolkata", "Chennai",
        "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    ]
    all_segments: list[Segment] = []
    for campaign in campaigns:
        for seg_name in campaign.segments:
            sample_size = random.randint(20, min(200, len(customers)))
            selected = random.sample(customers, k=sample_size)
            segment = Segment(
                campaign_id=campaign.campaign_id,
                segment_name=seg_name,
                description=f"Auto-generated segment: {seg_name.replace('_', ' ')}",
                customer_ids=[c.customer_id for c in selected],
                segment_criteria=SegmentCriteria(
                    age_range={
                        "min": random.randint(18, 25),
                        "max": random.randint(35, 65),
                    },
                    gender=random.sample(["Male", "Female", "Other"], k=random.randint(1, 2)),
                    cities=random.sample(INDIAN_CITIES, k=random.randint(2, 5)),
                    occupation_type=random.sample(
                        ["Full-time", "Part-time", "Self-employed", "Retired", "Student"],
                        k=random.randint(1, 3),
                    ),
                    app_installed=random.choice(["Y", "N", None]),
                    existing_customer=random.choice(["Y", "N", None]),
                ),
            )
            all_segments.append(segment)
    return all_segments


# ── Orchestrator functions ────────────────────────────────────────


async def seed_customers(db) -> int:
    """Seed the customers collection from Mock API. Falls back to empty if API is down."""
    customers = await fetch_customers_from_mock_api()
    if not customers:
        logger.warning("Mock API returned no customers — seeding 0 customers")
        return 0
    docs = [c.to_dict() for c in customers]
    await db["customers"].insert_many(docs)
    logger.info("Seeded %d customers from Mock API", len(docs))
    return len(docs)


async def seed_campaigns(db) -> tuple[list[Campaign], int]:
    """Seed campaigns. Returns (campaign objects, count)."""
    campaigns = generate_seed_campaigns()
    docs = [c.model_dump() for c in campaigns]
    await db["campaigns"].insert_many(docs)
    logger.info("Seeded %d campaigns", len(docs))
    return campaigns, len(docs)


async def seed_variants(db, campaigns: list[Campaign]) -> tuple[list[CampaignVariant], int]:
    """Seed variants for given campaigns. Returns (variant objects, count)."""
    variants = generate_seed_variants(campaigns)
    docs = [v.model_dump() for v in variants]
    await db["campaign_variants"].insert_many(docs)
    logger.info("Seeded %d variants", len(docs))
    return variants, len(docs)


async def seed_metrics(db, variants: list[CampaignVariant]) -> int:
    """Seed metrics for given variants. Returns count."""
    metrics = generate_seed_metrics(variants)
    docs = [m.model_dump() for m in metrics]
    await db["metrics"].insert_many(docs)
    logger.info("Seeded %d metrics", len(docs))
    return len(docs)


async def seed_segments(db, campaigns: list[Campaign], customers: list[Customer] | None = None) -> int:
    """Seed segments. Returns count."""
    if not customers:
        # Fetch from DB if already seeded
        cursor = db["customers"].find().limit(5000)
        customers = [Customer(**doc) async for doc in cursor]
    if not customers:
        logger.warning("No customers available for segment generation")
        return 0
    segments = generate_seed_segments(campaigns, customers)
    docs = [s.model_dump() for s in segments]
    await db["segments"].insert_many(docs)
    logger.info("Seeded %d segments", len(docs))
    return len(docs)


async def clear_database(db) -> None:
    """Drop all collections for a clean re-seed."""
    for col in ["customers", "campaigns", "campaign_variants", "metrics", "segments"]:
        await db[col].drop()
    logger.info("Cleared all collections")


async def seed_all(db) -> dict[str, int]:
    """Full database seeding orchestrator.

    Clears existing data, fetches customers from Mock API,
    then populates all collections.
    """
    await clear_database(db)

    customer_count = await seed_customers(db)
    campaigns, campaign_count = await seed_campaigns(db)
    variants, variant_count = await seed_variants(db, campaigns)
    metric_count = await seed_metrics(db, variants)

    # Re-fetch customers from DB for segment assignment
    cursor = db["customers"].find().limit(5000)
    customers = [Customer(**doc) async for doc in cursor]
    segment_count = await seed_segments(db, campaigns, customers)

    summary = {
        "customers": customer_count,
        "campaigns": campaign_count,
        "variants": variant_count,
        "metrics": metric_count,
        "segments": segment_count,
    }
    logger.info("Seed complete: %s", summary)
    return summary
