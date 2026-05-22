import { Megaphone, Mail, Sparkles, Target, Zap, Users } from "lucide-react";

export type CampaignStatus = "draft" | "pending" | "active" | "completed" | "rejected";

export interface Segment {
  name: string;
  count: number;
  age: string;
  gender: string;
  location: string;
  description: string;
}

export interface EmailVariant {
  variant: string;
  subject: string;
  body: string;
  segment: string;
}

export interface CampaignMetrics {
  openRate: number;
  clickRate: number;
  conversions: number;
  roi: string;
  performance: { date: string; openRate: number; clickRate: number }[];
  segmentPerformance: {
    name: string;
    recipients: number;
    openRate: number;
    clickRate: number;
    conversions: number;
  }[];
  variantComparison: { name: string; variantA: number; variantB: number }[];
}

export interface Campaign {
  id: string;
  name: string;
  product: string;
  brief: string;
  goal: string;
  budget: string;
  scheduledSend: string;
  status: CampaignStatus;
  createdAt: string;
  segments: Segment[];
  variants: EmailVariant[];
  metrics: CampaignMetrics;
  revisionNotes?: string;
}

const baseSegments: Segment[] = [
  {
    name: "Urban Professionals",
    count: 12400,
    age: "28–42",
    gender: "Mixed",
    location: "Major metro areas",
    description:
      "Career-oriented individuals in metropolitan cities with above-average income who value convenience, quality, and early access to new products.",
  },
  {
    name: "Young Trendsetters",
    count: 8750,
    age: "18–27",
    gender: "Female-leaning",
    location: "Urban & suburban",
    description:
      "Socially active consumers who follow trends and influencers, highly engaged on social media and responsive to authentic visual messaging.",
  },
  {
    name: "Value Seekers",
    count: 15200,
    age: "30–55",
    gender: "Mixed",
    location: "Suburban areas",
    description:
      "Budget-conscious shoppers who prioritize deals and value-for-money; respond well to promotions and loyalty programs.",
  },
];

const baseVariants: EmailVariant[] = [
  {
    variant: "A",
    subject: "Unlock Exclusive Early Access — Just for You",
    body: "Hi {{first_name}}, we're launching something special and wanted you to be the first to know. As a valued customer, you get exclusive early access to our newest collection.",
    segment: "Urban Professionals",
  },
  {
    variant: "B",
    subject: "🔥 Trending Now: Don't Miss Out on What's New",
    body: "Hey {{first_name}}! The wait is over — our latest drop is here and it's already turning heads. Your feed is about to get a whole lot better.",
    segment: "Young Trendsetters",
  },
  {
    variant: "C",
    subject: "Save 25% This Week — Your Exclusive Offer",
    body: "Hi {{first_name}}, for a limited time, enjoy 25% off our most popular items. We know you love a great deal — this one is too good to pass up.",
    segment: "Value Seekers",
  },
];

const buildMetrics = (seed: number): CampaignMetrics => ({
  openRate: 42 + seed,
  clickRate: 14 + seed / 2,
  conversions: 600 + seed * 30,
  roi: `$${(3000 + seed * 220).toLocaleString()}`,
  performance: Array.from({ length: 10 }).map((_, i) => ({
    date: `Day ${i + 1}`,
    openRate: 38 + seed + i + Math.round(Math.sin(i) * 3),
    clickRate: 10 + seed / 2 + i / 2 + Math.round(Math.cos(i) * 2),
  })),
  segmentPerformance: [
    { name: "Urban Professionals", recipients: 12500, openRate: 58.2 + seed / 4, clickRate: 22.1, conversions: 312 },
    { name: "Young Trendsetters", recipients: 8700, openRate: 51.4, clickRate: 18.7, conversions: 198 },
    { name: "Value Seekers", recipients: 15200, openRate: 45.8, clickRate: 14.3, conversions: 245 },
  ],
  variantComparison: [
    { name: "Open Rate", variantA: 54 + seed / 3, variantB: 48 + seed / 4 },
    { name: "Click Rate", variantA: 21, variantB: 17 },
    { name: "Conversions", variantA: 8.4, variantB: 6.1 },
  ],
});

export const initialCampaigns: Campaign[] = [
  {
    id: "summer-sale-2025",
    name: "Summer Sale 2025",
    product: "Summer Collection",
    brief: "Drive summer collection sales with a vibrant, time-limited promotion targeting urban shoppers and young trendsetters.",
    goal: "Sales Conversion",
    budget: "$12,500",
    scheduledSend: "Tue, Jun 10 · 10:00 AM",
    status: "active",
    createdAt: "Jun 1, 2025",
    segments: baseSegments,
    variants: baseVariants,
    metrics: buildMetrics(8),
  },
  {
    id: "product-launch-x",
    name: "Product Launch — Series X",
    product: "Series X Headphones",
    brief: "Build awareness and pre-orders for the new Series X audio line with premium positioning and exclusive early-access offers.",
    goal: "Pre-orders",
    budget: "$18,000",
    scheduledSend: "Mon, Jun 16 · 9:00 AM",
    status: "pending",
    createdAt: "Jun 10, 2025",
    segments: baseSegments,
    variants: baseVariants,
    metrics: buildMetrics(2),
  },
  {
    id: "retention-q3",
    name: "Customer Retention Q3",
    product: "Loyalty Program",
    brief: "Re-engage lapsed customers with personalized offers and a refreshed loyalty program to lift Q3 retention by 12%.",
    goal: "Retention",
    budget: "$8,200",
    scheduledSend: "Wed, Jul 3 · 11:00 AM",
    status: "pending",
    createdAt: "Jun 15, 2025",
    segments: baseSegments,
    variants: baseVariants,
    metrics: buildMetrics(4),
  },
  {
    id: "holiday-gift-guide",
    name: "Holiday Gift Guide",
    product: "Holiday Catalog",
    brief: "Showcase curated gift recommendations across price tiers to drive holiday season conversions and average order value.",
    goal: "Sales Conversion",
    budget: "$22,000",
    scheduledSend: "Mon, May 26 · 8:00 AM",
    status: "completed",
    createdAt: "May 20, 2025",
    segments: baseSegments,
    variants: baseVariants,
    metrics: buildMetrics(12),
  },
  {
    id: "welcome-series",
    name: "Welcome Series Redesign",
    product: "Onboarding Flow",
    brief: "Refresh the new-subscriber welcome flow to lift activation rates with a five-email automated sequence.",
    goal: "Activation",
    budget: "$5,500",
    scheduledSend: "Fri, Jun 13 · 10:00 AM",
    status: "active",
    createdAt: "Jun 5, 2025",
    segments: baseSegments,
    variants: baseVariants,
    metrics: buildMetrics(6),
  },
  {
    id: "flash-sale-weekend",
    name: "Flash Sale Weekend",
    product: "Site-wide Flash Sale",
    brief: "Drive a 48-hour spike in conversions with an aggressive site-wide discount and urgency-driven creative.",
    goal: "Sales Conversion",
    budget: "$9,800",
    scheduledSend: "Sat, May 17 · 7:00 AM",
    status: "completed",
    createdAt: "May 10, 2025",
    segments: baseSegments,
    variants: baseVariants,
    metrics: buildMetrics(10),
  },
];

export const productHighlights = [
  {
    icon: Sparkles,
    title: "AI Audience Segmentation",
    description:
      "Generate rich customer segments with demographics, psychographics, and behavioral insights in seconds.",
  },
  {
    icon: Mail,
    title: "Variant-Ready Email Drafts",
    description:
      "Get multiple on-brand email variants tailored to each segment, ready for A/B testing.",
  },
  {
    icon: Target,
    title: "Smart Send-Time Optimization",
    description:
      "Send when each audience is most likely to open with channel and time recommendations.",
  },
  {
    icon: Zap,
    title: "Built-in Approval Workflow",
    description:
      "Review, request revisions, or approve campaigns with full traceability before launch.",
  },
  {
    icon: Megaphone,
    title: "Live Performance Metrics",
    description:
      "Track open rate, click rate, conversions, and ROI with beautiful real-time dashboards.",
  },
  {
    icon: Users,
    title: "Team Collaboration",
    description:
      "Share strategy reviews, collect feedback, and iterate together — no spreadsheets required.",
  },
];

export const flowSteps = [
  { step: "01", title: "Brief", description: "Describe your product, audience, and goals in plain language." },
  { step: "02", title: "Strategy", description: "AI generates segments, variants, and a send-time plan." },
  { step: "03", title: "Approval", description: "Review side-by-side variants and approve or request revisions." },
  { step: "04", title: "Metrics", description: "Track live performance and iterate with confidence." },
];
