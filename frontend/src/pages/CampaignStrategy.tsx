import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import SegmentCard from "@/components/strategy/SegmentCard";
import TargetingStrategyCard from "@/components/strategy/TargetingStrategyCard";
import SendTimeCard from "@/components/strategy/SendTimeCard";
import ABTestingCard from "@/components/strategy/ABTestingCard";
import EmailVariantCard from "@/components/strategy/EmailVariantCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const segments = [
  {
    name: "Urban Professionals",
    count: 12400,
    age: "28–42",
    gender: "Mixed",
    location: "Major metro areas",
    description:
      "Career-oriented individuals in metropolitan cities with above-average income. They value convenience, quality, and are early adopters of new products and services.",
  },
  {
    name: "Young Trendsetters",
    count: 8750,
    age: "18–27",
    gender: "Female-leaning",
    location: "Urban & suburban",
    description:
      "Socially active consumers who follow trends and influencers. Highly engaged on social media and responsive to visual-first marketing with authentic brand messaging.",
  },
  {
    name: "Value Seekers",
    count: 15200,
    age: "30–55",
    gender: "Mixed",
    location: "Suburban areas",
    description:
      "Budget-conscious shoppers who prioritize deals and value-for-money. Respond well to promotional offers, loyalty programs, and comparison-based messaging.",
  },
  {
    name: "Premium Buyers",
    count: 4300,
    age: "35–60",
    gender: "Mixed",
    location: "Affluent suburbs",
    description:
      "High-income consumers willing to pay a premium for quality and exclusivity. They appreciate personalized communication and exclusive early-access offers.",
  },
];

const emailVariants = [
  {
    variant: "A",
    subject: "Unlock Exclusive Early Access — Just for You",
    body: "Hi {{first_name}}, we're launching something special and wanted you to be the first to know. As a valued customer, you get exclusive early access to our newest collection before anyone else...",
    segment: "Urban Professionals",
  },
  {
    variant: "B",
    subject: "🔥 Trending Now: Don't Miss Out on What's New",
    body: "Hey {{first_name}}! The wait is over — our latest drop is here and it's already turning heads. Your feed is about to get a whole lot better. Check out what everyone is talking about...",
    segment: "Young Trendsetters",
  },
  {
    variant: "C",
    subject: "Save 25% This Week — Your Exclusive Offer Inside",
    body: "Hi {{first_name}}, great news! For a limited time, enjoy 25% off our most popular items. We know you love a great deal, and this one is too good to pass up. Shop now and save big...",
    segment: "Value Seekers",
  },
];

const CampaignStrategy = () => {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-10 overflow-auto">
        <div>
            {/* Breadcrumb */}
            <nav className="flex items-center gap-1.5 text-sm text-muted-foreground mb-4">
              <Link to="/" className="hover:text-foreground">Home</Link>
              <ChevronRight className="h-3.5 w-3.5" />
              <Link to="/campaigns" className="hover:text-foreground">Campaigns</Link>
              <ChevronRight className="h-3.5 w-3.5" />
              <span className="text-foreground font-medium">Strategy</span>
            </nav>

            {/* Header */}
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <h1 className="text-2xl font-semibold text-foreground">
                Campaign Strategy — Spring Product Launch
              </h1>
              <Badge variant="secondary" className="bg-stat-green/10 text-stat-green border-0 text-xs font-medium">
                AI Generated
              </Badge>
            </div>

            {/* Main grid */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">
              {/* Left: Segments */}
              <div className="lg:col-span-3 space-y-4">
                <h2 className="text-base font-semibold text-foreground">Customer Segments</h2>
                {segments.map((s) => (
                  <SegmentCard key={s.name} {...s} />
                ))}
              </div>

              {/* Right: Strategy */}
              <div className="lg:col-span-2 space-y-4">
                <h2 className="text-base font-semibold text-foreground">Campaign Strategy</h2>
                <TargetingStrategyCard />
                <SendTimeCard />
                <ABTestingCard />
              </div>
            </div>

            {/* Email variants */}
            <div className="mb-8">
              <h2 className="text-base font-semibold text-foreground mb-4">Email Variants Preview</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {emailVariants.map((v) => (
                  <EmailVariantCard key={v.variant} {...v} />
                ))}
              </div>
            </div>

            {/* Action bar */}
            <div className="flex items-center justify-end gap-3 border-t pt-5">
              <Button variant="outline" asChild>
                <Link to="/campaigns/create">Edit Strategy</Link>
              </Button>
              <Button>Proceed to Approval</Button>
            </div>
        </div>
      </main>
    </div>
  );
};

export default CampaignStrategy;
