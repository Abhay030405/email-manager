'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Target } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import SegmentCard from "@/components/strategy/SegmentCard";
import TargetingStrategyCard from "@/components/strategy/TargetingStrategyCard";
import SendTimeCard from "@/components/strategy/SendTimeCard";
import ABTestingCard from "@/components/strategy/ABTestingCard";
import EmailVariantCard from "@/components/strategy/EmailVariantCard";
import { Button } from "@/components/ui/button";
import { useCampaigns } from "@/context/CampaignsContext";
import {
  getCampaignStrategy,
  getCampaignSegments,
  getCampaignVariants,
  ApiStrategy,
  ApiSegment,
} from "@/lib/api";

interface SegmentCardData {
  name: string; count: number; age: string; gender: string; location: string; description: string;
}

interface VariantData {
  variant: string; subject: string; body: string; segment: string;
}

function mapSegment(s: ApiSegment): SegmentCardData {
  const c = s.segment_criteria ?? {};
  return {
    name: s.segment_name.replaceAll("_", " "),
    count: s.customer_ids?.length ?? 0,
    age: c.age_range ? `${c.age_range.min ?? ""}–${c.age_range.max ?? ""}` : "All ages",
    gender: c.gender ?? "All",
    location: "All locations",
    description: s.description || `Segment: ${s.segment_name}`,
  };
}

const LABELS = ["A", "B", "C", "D", "E", "F"];

export default function CampaignStrategy() {
  const params = useParams();
  const id = params.id as string;
  const { getCampaign } = useCampaigns();
  const campaign = id ? getCampaign(id) : undefined;

  const [strategy, setStrategy] = useState<ApiStrategy | null>(null);
  const [segments, setSegments] = useState<SegmentCardData[]>([]);
  const [variants, setVariants] = useState<VariantData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      getCampaignStrategy(id).then(({ strategy: s }) => setStrategy(s)),
      getCampaignSegments(id).then(({ segments: apiSegs }) => setSegments(apiSegs.map(mapSegment))),
      getCampaignVariants(id).then(({ variants: apiVars }) =>
        setVariants(apiVars.map((v, i) => ({
          variant: LABELS[i] ?? String(i + 1),
          subject: v.subject_line,
          body: v.email_body,
          segment: v.segment_name.replaceAll("_", " "),
        })))
      ),
    ]).finally(() => setLoading(false));
  }, [id]);

  const campaignName = campaign?.name ?? "Campaign Strategy";

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-10">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground/60 mb-6">
          <Link href="/" className="hover:text-foreground transition-colors">home</Link>
          <span className="text-border">/</span>
          <Link href="/campaigns" className="hover:text-foreground transition-colors">campaigns</Link>
          <span className="text-border">/</span>
          {id && (
            <>
              <Link href={`/campaigns/${id}`} className="hover:text-foreground transition-colors truncate max-w-[120px]">
                {campaignName}
              </Link>
              <span className="text-border">/</span>
            </>
          )}
          <span className="text-foreground/80">strategy</span>
        </nav>

        {/* Page header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-stat-green/80 bg-stat-green/8 border border-stat-green/20 px-2.5 py-1 rounded mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-stat-green" aria-hidden="true" />
            {"AI Generated"}
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Campaign Strategy
          </h1>
          <p className="text-sm text-muted-foreground mt-1.5">{campaignName}</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24 border border-border/40 rounded-lg bg-card">
            <p className="font-mono text-sm text-muted-foreground/60">Loading strategy…</p>
          </div>
        ) : (
          <>
            {/* Main grid */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">
              {/* Left: Segments */}
              <div className="lg:col-span-3 space-y-4">
                <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-primary/80 bg-primary/8 border border-primary/15 px-2.5 py-1 rounded">
                  Customer Segments
                </div>
                {segments.length > 0 ? (
                  segments.map((s) => <SegmentCard key={s.name} {...s} />)
                ) : (
                  <p className="font-mono text-sm text-muted-foreground/60">No segments found for this campaign.</p>
                )}
              </div>

              {/* Right: Strategy cards */}
              <div className="lg:col-span-2 space-y-4">
                <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-primary/80 bg-primary/8 border border-primary/15 px-2.5 py-1 rounded">
                  <Target className="h-3 w-3" />
                  Campaign Strategy
                </div>
                <TargetingStrategyCard
                  selectedSegments={strategy?.selected_segments}
                  reasoning={strategy?.reasoning}
                />
                <SendTimeCard sendSchedule={strategy?.send_schedule} />
                <ABTestingCard abTestPlan={strategy?.ab_test_plan} />
              </div>
            </div>

            {/* Email variants */}
            {variants.length > 0 && (
              <div className="mb-8">
                <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-primary/80 bg-primary/8 border border-primary/15 px-2.5 py-1 rounded mb-4">
                  Email Variants Preview
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-border/40 rounded-lg overflow-hidden border border-border/40">
                  {variants.map((v) => (
                    <EmailVariantCard key={v.variant} {...v} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Action bar */}
        <div className="flex items-center justify-end gap-3 border-t border-border/40 pt-5">
          <Button variant="outline" asChild className="font-mono text-sm border-border/60">
            <Link href={id ? `/campaigns/${id}` : "/campaigns"}>Back to Campaign</Link>
          </Button>
          {id && (
            <Button asChild className="font-mono text-sm bg-primary hover:bg-primary/90 text-white">
              <Link href={`/campaigns/${id}`}>Proceed to Approval</Link>
            </Button>
          )}
        </div>

      </main>
    </div>
  );
}
