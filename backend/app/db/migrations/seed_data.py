"""Seed data for initial database population.

Customers are managed by the Mock Campaign API — they are NOT stored locally.
This script seeds: campaigns, variants, metrics, and placeholder segments.
"""

import logging
from datetime import datetime, timedelta
import random

from app.core.config import get_settings
from app.models.campaign import Campaign, CampaignStatus, ParsedData
from app.models.variant import CampaignVariant, VariantStatus
from app.models.metrics import Metrics
from app.models.segment import Segment, SegmentCriteria

logger = logging.getLogger(__name__)
random.seed(42)

MOCK_API_BASE = get_settings().MOCK_CAMPAIGN_API_URL
MOCK_API_TIMEOUT = get_settings().MOCK_API_TIMEOUT

_G1 = "Group 1"

# ── Indian-context campaign templates ─────────────────────────────

CAMPAIGN_TEMPLATES = [
    {
        "brief": "Launch Diwali sale for premium electronics targeting urban males aged 25-40 in Mumbai and Delhi. CTA: https://example.com/diwali-sale",
        "parsed": ParsedData(
            product_details={"product_name": "Premium Electronics Diwali Offer", "product_description": "Top electronics at festive prices", "cta_link": "https://example.com/diwali-sale"},
            target_audience={_G1: {"min_age": 25, "max_age": 40, "gender": "Male", "KYC_status": "Y"}},
            campaign_goal={"objective": "Drive 15% conversion rate"},
            campaign_preferences={"email_tone": "Friendly", "campaign_name": "Diwali Electronics 2026", "content_hints": ""},
        ),
        "segments": ["urban_young_males", "metro_tech_enthusiasts", "high_income_diwali"],
    },
    {
        "brief": "Promote KYC-verified savings account for existing customers with credit scores above 700.",
        "parsed": ParsedData(
            product_details={"product_name": "Premium Savings Account", "product_description": "Higher interest savings for verified customers", "cta_link": "https://example.com/savings"},
            target_audience={_G1: {"KYC_status": "Y", "Existing_Customer": "Y", "Credit_score": 700}},
            campaign_goal={"objective": "Open 5000 new accounts"},
            campaign_preferences={"email_tone": "Formal", "campaign_name": "Premium Savings Q2", "content_hints": ""},
        ),
        "segments": ["kyc_verified_high_credit", "existing_metro_customers"],
    },
    {
        "brief": "Back-to-school campaign for families with kids targeting parents aged 30-50 across all cities.",
        "parsed": ParsedData(
            product_details={"product_name": "Back to School Bundle", "product_description": "Everything for school season", "cta_link": "https://example.com/school"},
            target_audience={_G1: {"min_age": 30, "max_age": 50}},
            campaign_goal={"objective": "Drive 12% conversion"},
            campaign_preferences={"email_tone": "Friendly", "campaign_name": "Back to School 2026", "content_hints": ""},
        ),
        "segments": ["parents_with_kids", "family_oriented"],
    },
    {
        "brief": "App download push for non-app users on social media. Target social-media-active users aged 18-35.",
        "parsed": ParsedData(
            product_details={"product_name": "Mobile App", "product_description": "All services at your fingertips", "cta_link": "https://example.com/app"},
            target_audience={_G1: {"min_age": 18, "max_age": 35, "App_Installed": "N", "Social_Media_Active": "Y"}},
            campaign_goal={"objective": "50K downloads in 30 days"},
            campaign_preferences={"email_tone": "Friendly", "campaign_name": "App Download Push", "content_hints": ""},
        ),
        "segments": ["social_no_app", "young_digital_natives"],
    },
    {
        "brief": "Re-engage non-existing customers with introductory offer for self-employed workers.",
        "parsed": ParsedData(
            product_details={"product_name": "New Customer Welcome Offer", "product_description": "Exclusive introductory offer", "cta_link": "https://example.com/welcome"},
            target_audience={_G1: {"Existing_Customer": "N"}},
            campaign_goal={"objective": "Convert 10% to new customers"},
            campaign_preferences={"email_tone": "Friendly", "campaign_name": "New Customer Welcome", "content_hints": ""},
        ),
        "segments": ["non_existing_prospects", "new_customer_targets"],
    },
    {
        "brief": "Premium credit card upsell for high-credit-score professionals.",
        "parsed": ParsedData(
            product_details={"product_name": "Platinum Credit Card", "product_description": "Premium card for high earners", "cta_link": "https://example.com/platinum"},
            target_audience={_G1: {"Credit_score": 750, "KYC_status": "Y"}},
            campaign_goal={"objective": "8% upgrade rate"},
            campaign_preferences={"email_tone": "Formal", "campaign_name": "Platinum Upsell", "content_hints": ""},
        ),
        "segments": ["high_credit_professionals", "platinum_candidates"],
    },
    {
        "brief": "Student discount program for young customers aged 18-25.",
        "parsed": ParsedData(
            product_details={"product_name": "Student Discount Program", "product_description": "Exclusive discounts for students", "cta_link": "https://example.com/students"},
            target_audience={_G1: {"min_age": 18, "max_age": 25}},
            campaign_goal={"objective": "Enroll 10000 students"},
            campaign_preferences={"email_tone": "Friendly", "campaign_name": "Student Discount 2026", "content_hints": ""},
        ),
        "segments": ["young_customers", "budget_conscious_youth"],
    },
    {
        "brief": "Financial literacy webinar for retired customers. Emphasize ease and trust.",
        "parsed": ParsedData(
            product_details={"product_name": "Financial Literacy Webinar", "product_description": "Free webinar for retirement planning", "cta_link": "https://example.com/webinar"},
            target_audience={_G1: {"min_age": 60, "KYC_status": "Y"}},
            campaign_goal={"objective": "500 webinar registrations"},
            campaign_preferences={"email_tone": "Formal", "campaign_name": "Financial Literacy Series", "content_hints": ""},
        ),
        "segments": ["senior_customers", "retirement_planning"],
    },
    {
        "brief": "Festive personal loan campaign for salaried employees.",
        "parsed": ParsedData(
            product_details={"product_name": "Festive Personal Loan", "product_description": "Instant personal loan at low rates", "cta_link": "https://example.com/loan"},
            target_audience={_G1: {"min_income": 40000, "KYC_status": "Y", "Existing_Customer": "Y"}},
            campaign_goal={"objective": "Disburse 2000 loans"},
            campaign_preferences={"email_tone": "Urgent", "campaign_name": "Festive Loan 2026", "content_hints": ""},
        ),
        "segments": ["salaried_existing", "high_income_loan_eligible"],
    },
    {
        "brief": "Women's Day special campaign. Highlight exclusive offers for social-media-active customers.",
        "parsed": ParsedData(
            product_details={"product_name": "Women's Day Special", "product_description": "Exclusive offers for women", "cta_link": "https://example.com/womensday"},
            target_audience={_G1: {"gender": "Female", "Social_Media_Active": "Y"}},
            campaign_goal={"objective": "25% engagement increase"},
            campaign_preferences={"email_tone": "Friendly", "campaign_name": "Women's Day 2026", "content_hints": ""},
        ),
        "segments": ["female_social_active", "working_women"],
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


def generate_seed_segments(campaigns: list[Campaign]) -> list[Segment]:
    """Generate placeholder segments for campaigns.

    customer_ids are left empty — they are populated at runtime by the
    segmentation agent via POST /api/customers/filter on the Mock API.
    """
    all_segments: list[Segment] = []
    for campaign in campaigns:
        for seg_name in campaign.segments:
            segment = Segment(
                campaign_id=campaign.campaign_id,
                segment_name=seg_name,
                description=f"Seed segment: {seg_name.replace('_', ' ')}",
                customer_ids=[],
            )
            all_segments.append(segment)
    return all_segments


# ── Orchestrator functions ────────────────────────────────────────


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


async def seed_segments(db, campaigns: list[Campaign]) -> int:
    """Seed placeholder segments. Returns count."""
    segments = generate_seed_segments(campaigns)
    docs = [s.model_dump() for s in segments]
    await db["segments"].insert_many(docs)
    logger.info("Seeded %d segments", len(docs))
    return len(docs)


async def clear_database(db) -> None:
    """Drop all collections for a clean re-seed."""
    for col in ["campaigns", "campaign_variants", "metrics", "segments"]:
        await db[col].drop()
    logger.info("Cleared all collections")


async def seed_all(db) -> dict[str, int]:
    """Full database seeding orchestrator."""
    await clear_database(db)

    campaigns, campaign_count = await seed_campaigns(db)
    variants, variant_count = await seed_variants(db, campaigns)
    metric_count = await seed_metrics(db, variants)
    segment_count = await seed_segments(db, campaigns)

    summary = {
        "campaigns": campaign_count,
        "variants": variant_count,
        "metrics": metric_count,
        "segments": segment_count,
    }
    logger.info("Seed complete: %s", summary)
    return summary
