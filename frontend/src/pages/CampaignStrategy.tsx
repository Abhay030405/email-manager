import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import SegmentCard from "@/components/strategy/SegmentCard";
import TargetingStrategyCard from "@/components/strategy/TargetingStrategyCard";
import SendTimeCard from "@/components/strategy/SendTimeCard";
import ABTestingCard from "@/components/strategy/ABTestingCard";
import EmailVariantCard from "@/components/strategy/EmailVariantCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCampaigns } from "@/context/CampaignsContext";
import {
  getCampaignStrategy,
  getCampaignSegments,
  getCampaignVariants,
  ApiStrategy,
  ApiSegment,
} from "@/lib/api";

interface SegmentCardData {
  name: string;
  count: number;
  age: string;
  gender: string;
  location: string;
  description: string;
}

interface VariantData {
  variant: string;
  subject: string;
  body: string;
  segment: string;
}

function mapSegment(s: ApiSegment): SegmentCardData {
  const c = s.segment_criteria ?? {};
  return {
    name: s.segment_name.replace(/_/g, " "),
    count: s.customer_ids?.length ?? 0,
    age: c.age_range ? `${c.age_range.min ?? ""}–${c.age_range.max ?? ""}` : "All ages",
    gender: c.gender?.join(", ") ?? "All",
    location: c.cities?.slice(0, 3).join(", ") ?? "All locations",
    description: s.description || `Segment: ${s.segment_name}`,
  };
}

const LABELS = ["A", "B", "C", "D", "E", "F"];

const CampaignStrategy = () => {
  const { id } = useParams<{ id: string }>();
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
      getCampaignSegments(id).then(({ segments: apiSegs }) =>
        setSegments(apiSegs.map(mapSegment))
      ),
      getCampaignVariants(id).then(({ variants: apiVars }) =>
        setVariants(
          apiVars.map((v, i) => ({
            variant: LABELS[i] ?? String(i + 1),
            subject: v.subject_line,
            body: v.email_body,
            segment: v.segment_name.replace(/_/g, " "),
          }))
        )
      ),
    ]).finally(() => setLoading(false));
  }, [id]);

  const campaignName = campaign?.name ?? "Campaign Strategy";

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
            {id && (
              <>
                <Link to={`/campaigns/${id}`} className="hover:text-foreground">{campaignName}</Link>
                <ChevronRight className="h-3.5 w-3.5" />
              </>
            )}
            <span className="text-foreground font-medium">Strategy</span>
          </nav>

          {/* Header */}
          <div className="flex flex-wrap items-center gap-3 mb-6">
            <h1 className="text-2xl font-semibold text-foreground">
              Campaign Strategy — {campaignName}
            </h1>
            <Badge variant="secondary" className="bg-stat-green/10 text-stat-green border-0 text-xs font-medium">
              AI Generated
            </Badge>
          </div>

          {loading ? (
            <p className="text-sm text-muted-foreground">Loading strategy…</p>
          ) : (
            <>
              {/* Main grid */}
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">
                {/* Left: Segments */}
                <div className="lg:col-span-3 space-y-4">
                  <h2 className="text-base font-semibold text-foreground">Customer Segments</h2>
                  {segments.length > 0 ? (
                    segments.map((s) => <SegmentCard key={s.name} {...s} />)
                  ) : (
                    <p className="text-sm text-muted-foreground">No segments found for this campaign.</p>
                  )}
                </div>

                {/* Right: Strategy */}
                <div className="lg:col-span-2 space-y-4">
                  <h2 className="text-base font-semibold text-foreground">Campaign Strategy</h2>
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
                  <h2 className="text-base font-semibold text-foreground mb-4">Email Variants Preview</h2>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {variants.map((v) => (
                      <EmailVariantCard key={v.variant} {...v} />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Action bar */}
          <div className="flex items-center justify-end gap-3 border-t pt-5">
            <Button variant="outline" asChild>
              <Link to={id ? `/campaigns/${id}` : "/campaigns"}>Back to Campaign</Link>
            </Button>
            {id && (
              <Button asChild>
                <Link to={`/campaigns/${id}`}>Proceed to Approval</Link>
              </Button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default CampaignStrategy;
