"""Seed data for initial database population using Faker."""

import logging
from datetime import datetime, timedelta
import random

from faker import Faker

from app.models.customer import (
    ActivityStatus,
    Customer,
    Gender,
    Preferences,
    PurchaseRecord,
)
from app.models.campaign import Campaign, CampaignStatus, ParsedData
from app.models.variant import CampaignVariant, VariantStatus
from app.models.metrics import Metrics
from app.models.segment import Segment, SegmentCriteria

logger = logging.getLogger(__name__)
fake = Faker()
Faker.seed(42)
random.seed(42)

# ── Reference data ────────────────────────────────────────────────

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
    "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte",
    "Indianapolis", "San Francisco", "Seattle", "Denver", "Nashville",
    "Oklahoma City", "Portland", "Las Vegas", "Memphis", "Louisville",
    "Baltimore", "Milwaukee", "Albuquerque", "Tucson", "Fresno",
    "Sacramento", "Mesa", "Kansas City", "Atlanta", "Omaha",
    "Colorado Springs", "Raleigh", "Long Beach", "Virginia Beach", "Miami",
    "Oakland", "Minneapolis", "Tampa", "Tulsa", "Arlington",
    "New Orleans", "Wichita", "Cleveland", "Bakersfield", "Aurora",
]

TAGS_POOL = [
    "electronics", "fashion", "sports", "home", "beauty",
    "books", "food", "travel", "fitness", "tech",
    "outdoor", "gaming", "music", "wellness", "automotive",
]

PRODUCTS = [
    "Laptop", "Sneakers", "Headphones", "Backpack", "Watch",
    "Sunglasses", "Phone Case", "Water Bottle", "T-Shirt", "Yoga Mat",
    "Bluetooth Speaker", "Running Shorts", "Protein Powder", "Desk Lamp",
    "Wireless Mouse", "Notebook", "Coffee Mug", "Fitness Tracker",
    "Canvas Bag", "Portable Charger",
]

CATEGORIES = ["premium", "budget", "mid-range", "luxury", "eco-friendly"]

# ── 10 Campaign templates ────────────────────────────────────────

CAMPAIGN_TEMPLATES = [
    {
        "brief": "Launch a summer sale campaign for our new running shoes targeting active fitness enthusiasts aged 20-40. Goal is to drive 15% conversion rate with a budget of $5000. CTA: Shop Now at https://example.com/summer-sale",
        "parsed": ParsedData(product_name="Running Shoes Pro X", target_audience="Active fitness enthusiasts aged 20-40", campaign_goal="Drive 15% conversion rate", cta_link="https://example.com/summer-sale", budget=5000.0),
        "segments": ["young_active_males", "young_active_females", "fitness_enthusiasts"],
    },
    {
        "brief": "Promote our new wireless headphones with a Black Friday deal to tech-savvy millennials. Target 20% click-through rate with $8000 budget. CTA: Grab the Deal at https://example.com/black-friday",
        "parsed": ParsedData(product_name="AuraSound Wireless Headphones", target_audience="Tech-savvy millennials aged 25-40", campaign_goal="Achieve 20% click-through rate", cta_link="https://example.com/black-friday", budget=8000.0),
        "segments": ["tech_millennials", "audio_enthusiasts", "deal_seekers"],
    },
    {
        "brief": "Re-engage dormant customers who haven't purchased in 6+ months with a personalized win-back offer of 25% off. Budget $3000. CTA: Come Back at https://example.com/winback",
        "parsed": ParsedData(product_name="Store-wide Win-Back Offer", target_audience="Dormant customers inactive 6+ months", campaign_goal="Re-activate 10% of dormant users", cta_link="https://example.com/winback", budget=3000.0),
        "segments": ["dormant_6months", "high_value_dormant"],
    },
    {
        "brief": "Announce our new eco-friendly clothing line to environmentally conscious shoppers aged 22-45. Drive awareness and 12% conversion with $6000 budget. CTA: Explore Green at https://example.com/eco-line",
        "parsed": ParsedData(product_name="GreenThread Eco Collection", target_audience="Environmentally conscious shoppers 22-45", campaign_goal="12% conversion rate", cta_link="https://example.com/eco-line", budget=6000.0),
        "segments": ["eco_conscious", "fashion_forward", "young_professionals"],
    },
    {
        "brief": "Introduce premium subscription service to loyal customers with 50+ lifetime purchases. Highlight exclusive perks. Budget $4000. CTA: Go Premium at https://example.com/premium",
        "parsed": ParsedData(product_name="CX Premium Membership", target_audience="Loyal customers with 50+ purchases", campaign_goal="Convert 8% to premium subscribers", cta_link="https://example.com/premium", budget=4000.0),
        "segments": ["loyal_high_spenders", "frequent_buyers"],
    },
    {
        "brief": "Drive downloads of our new mobile app with an exclusive in-app discount for first-time users aged 18-35. Budget $7000. CTA: Download Now at https://example.com/app",
        "parsed": ParsedData(product_name="CampaignX Mobile App", target_audience="Mobile-first users aged 18-35", campaign_goal="50K app downloads in 30 days", cta_link="https://example.com/app", budget=7000.0),
        "segments": ["mobile_users", "young_digital_natives"],
    },
    {
        "brief": "Seasonal holiday gift guide campaign targeting shoppers aged 25-55 looking for curated gift ideas. Budget $10000. CTA: Find the Perfect Gift at https://example.com/gifts",
        "parsed": ParsedData(product_name="Holiday Gift Guide 2026", target_audience="Gift shoppers aged 25-55", campaign_goal="Drive 25% increase in holiday sales", cta_link="https://example.com/gifts", budget=10000.0),
        "segments": ["holiday_shoppers", "gift_givers", "premium_buyers"],
    },
    {
        "brief": "Flash sale on fitness equipment for New Year's resolution crowd aged 20-50. 48-hour window. Budget $3500. CTA: Start Strong at https://example.com/newyear",
        "parsed": ParsedData(product_name="Fitness Gear Flash Sale", target_audience="New Year fitness crowd aged 20-50", campaign_goal="Sell 2000 units in 48 hours", cta_link="https://example.com/newyear", budget=3500.0),
        "segments": ["fitness_beginners", "active_athletes", "resolution_crowd"],
    },
    {
        "brief": "Announce new smart home product line to tech enthusiasts and homeowners aged 30-60. Emphasize ease of setup. Budget $9000. CTA: Make Your Home Smart at https://example.com/smarthome",
        "parsed": ParsedData(product_name="SmartNest Home Hub", target_audience="Tech-savvy homeowners aged 30-60", campaign_goal="Generate 5000 pre-orders", cta_link="https://example.com/smarthome", budget=9000.0),
        "segments": ["tech_homeowners", "smart_home_early_adopters"],
    },
    {
        "brief": "Back-to-school campaign for parents of kids aged 5-18 featuring backpacks, stationery, and electronics bundles. Budget $5500. CTA: Shop School Essentials at https://example.com/backtoschool",
        "parsed": ParsedData(product_name="Back-to-School Bundle", target_audience="Parents with school-aged children", campaign_goal="Drive 18% conversion rate", cta_link="https://example.com/backtoschool", budget=5500.0),
        "segments": ["parents_young_kids", "parents_teens", "budget_families"],
    },
]

# ── Variant templates per campaign ──────────────────────────────

VARIANT_TEMPLATES = [
    # Campaign 0: Running Shoes
    [
        ("Crush Your Next Run – 30% Off Pro X Shoes", "<h1>Run Faster. Go Further.</h1><p>Our new Running Shoes Pro X are built for performance. Engineered with cutting-edge tech for every mile.</p>"),
        ("Your Perfect Running Partner Awaits", "<h1>Engineered for Champions</h1><p>Discover the Pro X difference today. Comfort meets speed in our latest innovation.</p>"),
        ("Don't Miss Out – Limited Pro X Stock", "<h1>Limited Edition Alert</h1><p>Only a few pairs left of our Running Shoes Pro X. Grab yours before they're gone!</p>"),
    ],
    # Campaign 1: Headphones
    [
        ("Hear the Difference – AuraSound Black Friday", "<h1>Sound Reimagined</h1><p>Experience crystal-clear audio with AuraSound Wireless Headphones. Black Friday exclusive pricing.</p>"),
        ("Your Ears Deserve Better – Up to 50% Off", "<h1>Premium Sound, Unbeatable Price</h1><p>Upgrade your listening experience with AuraSound. Limited time Black Friday deal.</p>"),
        ("AuraSound: The Gift of Great Audio", "<h1>Give the Gift of Sound</h1><p>AuraSound Wireless Headphones make the perfect holiday gift. Order now for guaranteed delivery.</p>"),
    ],
    # Campaign 2: Win-Back
    [
        ("We Miss You! Here's 25% Off to Welcome You Back", "<h1>It's Been a While!</h1><p>We've noticed you've been away. Come back and enjoy an exclusive 25% discount on your next purchase.</p>"),
        ("A Special Offer Just for You", "<h1>Your Exclusive Return Offer</h1><p>As a valued customer, we'd love to see you again. Here's a personalized discount to sweeten the deal.</p>"),
        ("Things Have Changed – Come See What's New", "<h1>New Arrivals Await</h1><p>We've added tons of new products since your last visit. Explore what's new with 25% off today.</p>"),
        ("Last Chance: Your 25% Off Expires Soon", "<h1>Don't Miss Out</h1><p>Your exclusive win-back offer is expiring soon. Shop now and save 25% on everything in store.</p>"),
    ],
    # Campaign 3: Eco Clothing
    [
        ("Wear the Change – New Eco Collection", "<h1>Fashion Meets Sustainability</h1><p>Introducing GreenThread: clothing that looks good and does good. Made from 100% recycled materials.</p>"),
        ("Look Good, Feel Good, Do Good", "<h1>Sustainable Style</h1><p>Our new eco-friendly collection proves you don't have to choose between style and sustainability.</p>"),
        ("Join the Green Revolution in Fashion", "<h1>Eco-Friendly Never Looked So Good</h1><p>GreenThread Collection: Where every purchase helps plant a tree. Shop the planet-friendly way.</p>"),
    ],
    # Campaign 4: Premium Subscription
    [
        ("You've Earned It – Go Premium Today", "<h1>Exclusive Perks Await</h1><p>As one of our most loyal customers, unlock premium benefits: free shipping, early access, and VIP support.</p>"),
        ("Unlock VIP Status – Premium Membership", "<h1>The VIP Experience</h1><p>Premium members get 20% off everything, priority shipping, and exclusive access to new launches.</p>"),
        ("Premium Is Calling – Limited Time Offer", "<h1>Become a Premium Member</h1><p>Join today and get your first month free. Enjoy perks that make every purchase even more rewarding.</p>"),
    ],
    # Campaign 5: Mobile App
    [
        ("Your Pocket Shopping Companion Is Here", "<h1>Shop Smarter with Our App</h1><p>Download the CampaignX app and unlock exclusive in-app discounts. Your first order is 20% off!</p>"),
        ("Exclusive App-Only Deals Await You", "<h1>App-First Savings</h1><p>Get deals you won't find anywhere else. Download now and start saving with our mobile-exclusive offers.</p>"),
        ("Download & Save – 20% Off Your First Order", "<h1>Welcome to Mobile Shopping</h1><p>New to our app? Enjoy 20% off your first purchase. Fast, easy, and always at your fingertips.</p>"),
        ("Shop Faster, Save More – Get the App", "<h1>The Fastest Way to Shop</h1><p>Browse, compare, and buy in seconds. Download the CampaignX app for a seamless shopping experience.</p>"),
    ],
    # Campaign 6: Holiday Gift Guide
    [
        ("The Ultimate 2026 Holiday Gift Guide", "<h1>Gifts They'll Actually Love</h1><p>Explore our curated holiday gift guide with hand-picked items for everyone on your list.</p>"),
        ("Holiday Shopping Made Easy", "<h1>Stress-Free Gifting</h1><p>Find the perfect gift in minutes with our expertly curated collections. Free gift wrapping included!</p>"),
        ("Give the Gift of Wow This Holiday Season", "<h1>Unforgettable Gifts</h1><p>From tech gadgets to luxury accessories, discover gifts that will make this holiday unforgettable.</p>"),
        ("Last-Minute Gifts That Don't Look Last-Minute", "<h1>Procrastinator's Paradise</h1><p>Running out of time? These thoughtful gifts ship fast and look like you planned for months.</p>"),
        ("Personalized Gifts for Every Budget", "<h1>Thoughtful Gifting</h1><p>Whether your budget is $20 or $200, find personalized gifts that show you care. Shop by price range.</p>"),
    ],
    # Campaign 7: Fitness Flash Sale
    [
        ("48 Hours Only – Fitness Gear Flash Sale", "<h1>Start Strong in 2026</h1><p>Dumbbells, yoga mats, resistance bands – everything you need to crush your goals, now at flash prices.</p>"),
        ("New Year, New You – 40% Off All Fitness Gear", "<h1>Resolution-Ready Deals</h1><p>Turn your New Year's resolutions into reality. Shop our biggest fitness gear sale of the year.</p>"),
        ("Don't Wait – Flash Sale Ends Tomorrow!", "<h1>Tick Tock – Sale Ending Soon</h1><p>Only hours left to grab premium fitness equipment at rock-bottom prices. Act now!</p>"),
    ],
    # Campaign 8: Smart Home
    [
        ("Make Your Home Smarter – SmartNest Hub", "<h1>Welcome to the Future of Home</h1><p>SmartNest Home Hub connects all your devices. Easy setup, voice control, and seamless automation.</p>"),
        ("Control Everything From One Place", "<h1>One Hub. Total Control.</h1><p>Lights, locks, cameras, climate – manage your entire home with SmartNest. Pre-order today.</p>"),
        ("Smart Home for Everyone – Easy Setup", "<h1>No Tech Degree Required</h1><p>SmartNest makes smart home accessible to everyone. Set up in minutes, enjoy for years.</p>"),
        ("Pre-Order SmartNest & Save 20%", "<h1>Early Bird Special</h1><p>Be among the first to experience SmartNest Home Hub. Pre-order now and save 20% off retail price.</p>"),
    ],
    # Campaign 9: Back to School
    [
        ("Back to School Essentials – All in One Bundle", "<h1>School-Ready in One Click</h1><p>Everything your kid needs for a successful school year – backpacks, stationery, and electronics.</p>"),
        ("Save Big on School Supplies This Year", "<h1>Smart Savings for Smart Students</h1><p>Bundle and save up to 35% on our curated back-to-school collections. Shop by grade level.</p>"),
        ("Parents Love It – Kids Approved Gear", "<h1>Quality Meets Affordability</h1><p>Durable backpacks, fun stationery, and reliable electronics. Gear that survives the school year.</p>"),
        ("Tech for Teens – Back to School Electronics", "<h1>Level Up Their Learning</h1><p>Laptops, tablets, and accessories designed for students. Education-approved and budget-friendly.</p>"),
        ("Free Shipping on All School Orders Over $50", "<h1>Easy Back-to-School Shopping</h1><p>Stock up on essentials and get free shipping on orders over $50. Limited time only!</p>"),
    ],
]


# ── Generator functions ───────────────────────────────────────────


def generate_seed_customers(count: int = 500) -> list[Customer]:
    """Generate realistic mock customers using Faker."""
    gender_weights = [0.45, 0.45, 0.10]  # male, female, other
    status_weights = [0.60, 0.30, 0.10]  # active, inactive, dormant

    customers: list[Customer] = []
    for i in range(count):
        gender = random.choices(list(Gender), weights=gender_weights, k=1)[0]
        activity = random.choices(list(ActivityStatus), weights=status_weights, k=1)[0]
        num_purchases = random.randint(0, 20)
        purchase_history = [
            PurchaseRecord(
                product=random.choice(PRODUCTS),
                amount=round(random.uniform(5, 800), 2),
                date=datetime.utcnow() - timedelta(days=random.randint(1, 730)),
            )
            for _ in range(num_purchases)
        ]

        customer = Customer(
            customer_id=f"CUST-{i + 1:04d}",
            age=random.randint(18, 75),
            gender=gender,
            location=random.choice(CITIES),
            activity_status=activity,
            purchase_history=purchase_history,
            preferences=Preferences(
                tags=random.sample(TAGS_POOL, k=random.randint(1, 5)),
                categories=random.sample(CATEGORIES, k=random.randint(1, 3)),
            ),
        )
        customers.append(customer)
    return customers


def generate_seed_campaigns() -> list[Campaign]:
    """Generate 10 sample campaigns from templates."""
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
            created_by=fake.user_name(),
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
        )
        campaigns.append(campaign)
    return campaigns


def generate_seed_variants(campaigns: list[Campaign]) -> list[CampaignVariant]:
    """Generate 3-5 variants per campaign from templates."""
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
                variant_type=chr(65 + v_idx),  # A, B, C, D, E
                personalization_tags=random.sample(
                    ["first_name", "location", "product_name", "discount_code"],
                    k=random.randint(1, 3),
                ),
                status=VariantStatus.DRAFT,
            )
            all_variants.append(variant)
    return all_variants


def generate_seed_metrics(
    variants: list[CampaignVariant],
) -> list[Metrics]:
    """Generate realistic metrics for each variant."""
    metrics_list: list[Metrics] = []
    for variant in variants:
        open_rate = round(random.uniform(15, 45), 2)
        click_rate = round(random.uniform(2, 8), 2)
        sent = random.randint(500, 5000)
        opened = int(sent * open_rate / 100)
        clicked = int(sent * click_rate / 100)

        m = Metrics(
            variant_id=variant.variant_id,
            campaign_id=variant.campaign_id,
            open_rate=open_rate,
            click_rate=click_rate,
            conversion_rate=round(random.uniform(1, 10), 2),
            bounce_rate=round(random.uniform(0.5, 5), 2),
            unsubscribe_rate=round(random.uniform(0.1, 2), 2),
            emails_sent=sent,
            emails_opened=opened,
            emails_clicked=clicked,
        )
        metrics_list.append(m)
    return metrics_list


def generate_seed_segments(
    campaigns: list[Campaign], customers: list[Customer]
) -> list[Segment]:
    """Generate segments for each campaign, populated with matching customer IDs."""
    all_segments: list[Segment] = []
    for campaign in campaigns:
        for seg_name in campaign.segments:
            # Assign a random slice of customers to each segment
            sample_size = random.randint(20, min(100, len(customers)))
            selected = random.sample(customers, k=sample_size)
            segment = Segment(
                campaign_id=campaign.campaign_id,
                segment_name=seg_name,
                description=fake.sentence(nb_words=12),
                customer_ids=[c.customer_id for c in selected],
                segment_criteria=SegmentCriteria(
                    age_range=[random.randint(18, 25), random.randint(35, 60)],
                    gender=random.sample([g.value for g in Gender], k=random.randint(1, 2)),
                    locations=random.sample(CITIES, k=random.randint(2, 5)),
                    activity_status=random.sample(
                        [s.value for s in ActivityStatus], k=random.randint(1, 2)
                    ),
                    tags=random.sample(TAGS_POOL, k=random.randint(1, 4)),
                ),
            )
            all_segments.append(segment)
    return all_segments


# ── Orchestrator functions ────────────────────────────────────────


async def seed_customers(db) -> int:
    """Seed the customers collection. Returns count of inserted docs."""
    customers = generate_seed_customers(500)
    docs = [c.model_dump() for c in customers]
    await db["customers"].insert_many(docs)
    logger.info("Seeded %d customers", len(docs))
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
    if customers is None:
        customers = generate_seed_customers(500)
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
    """
    Full database seeding orchestrator.
    Clears existing data, then populates all collections.
    Returns summary of inserted document counts.
    """
    await clear_database(db)

    customers = generate_seed_customers(500)
    docs = [c.model_dump() for c in customers]
    await db["customers"].insert_many(docs)

    campaigns, campaign_count = await seed_campaigns(db)
    variants, variant_count = await seed_variants(db, campaigns)
    metric_count = await seed_metrics(db, variants)
    segment_count = await seed_segments(db, campaigns, customers)

    summary = {
        "customers": len(docs),
        "campaigns": campaign_count,
        "variants": variant_count,
        "metrics": metric_count,
        "segments": segment_count,
    }
    logger.info("Seed complete: %s", summary)
    return summary
