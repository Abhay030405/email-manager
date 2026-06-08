'use client';

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, BarChart3, CheckCircle2, ExternalLink,
  RotateCcw, XCircle, Clock, Target, Users, Calendar,
  DollarSign, Flag, Mail,
} from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  ChartContainer, ChartLegend, ChartLegendContent,
  ChartTooltip, ChartTooltipContent,
} from "@/components/ui/chart";
import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCampaigns } from "@/context/CampaignsContext";
import { CampaignStatus, Segment, EmailVariant } from "@/data/campaignsData";
import {
  getCampaignSegments, getCampaignVariants, getCampaignStrategy,
  getCampaignLiveMetrics, executeApprovedCampaign, ApiStrategy, ApiMetrics,
} from "@/lib/api";
import { fillPlaceholders, stripHtml } from "@/lib/emailUtils";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const statusConfig: Record<CampaignStatus, { label: string; className: string }> = {
  draft:     { label: "Draft",            className: "bg-muted/60 text-muted-foreground border-border/40" },
  pending:   { label: "Pending Approval", className: "bg-stat-amber/10 text-stat-amber border-stat-amber/20" },
  active:    { label: "Approved",         className: "bg-primary/10 text-primary border-primary/20" },
  completed: { label: "Completed",        className: "bg-stat-green/10 text-stat-green border-stat-green/20" },
  rejected:  { label: "Rejected",         className: "bg-destructive/10 text-destructive border-destructive/20" },
};

const lineConfig = {
  openRate:  { label: "Open Rate",  color: "hsl(var(--chart-color-1))" },
  clickRate: { label: "Click Rate", color: "hsl(var(--chart-color-2))" },
};

const barConfig = {
  variantA: { label: "Variant A", color: "hsl(var(--chart-color-1))" },
  variantB: { label: "Variant B", color: "hsl(var(--chart-color-3))" },
};

type View = "overview" | "metrics";

export default function CampaignDetail() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();
  const { getCampaign, setStatus } = useCampaigns();
  const campaign = id ? getCampaign(id) : undefined;

  const [view, setView] = useState<View>("overview");
  const [revisionOpen, setRevisionOpen] = useState(false);
  const [revisionNote, setRevisionNote] = useState("");

  const [segments, setSegments] = useState<Segment[]>([]);
  const [variants, setVariants] = useState<EmailVariant[]>([]);
  const [strategy, setStrategy] = useState<ApiStrategy | null>(null);
  const [liveMetrics, setLiveMetrics] = useState<ApiMetrics[] | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    const LABELS = ["A", "B", "C", "D", "E", "F"];
    getCampaignStrategy(id).then(({ strategy: s }) => setStrategy(s));
    getCampaignSegments(id).then(({ segments: apiSegs }) => {
      setSegments(apiSegs.map((s) => {
        const c = s.segment_criteria ?? {};
        return {
          name: s.segment_name.replaceAll("_", " "),
          count: s.customer_ids?.length ?? 0,
          age: c.age_range ? `${c.age_range.min ?? ""}–${c.age_range.max ?? ""}` : "All ages",
          gender: c.gender ?? "All",
          location: "All locations",
          description: s.description || `Segment: ${s.segment_name}`,
        };
      }));
    });
    getCampaignVariants(id).then(({ variants: apiVars }) => {
      setVariants(apiVars.map((v, i) => ({
        variantId: v.variant_id,
        variant: LABELS[i] ?? String(i + 1),
        subject: v.subject_line,
        body: v.email_body,
        segment: v.segment_name.replace(/_/g, " "),
      })));
    });
  }, [id]);

  useEffect(() => {
    if (view !== "metrics" || !id || liveMetrics !== null) return;
    setMetricsLoading(true);
    getCampaignLiveMetrics(id).then(setLiveMetrics).finally(() => setMetricsLoading(false));
  }, [view, id, liveMetrics]);

  if (!campaign) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <main className="max-w-3xl mx-auto px-4 py-24 text-center">
          <h1 className="font-display text-2xl font-bold text-foreground">Campaign not found</h1>
          <p className="text-muted-foreground mt-2 text-sm">The campaign you&apos;re looking for doesn&apos;t exist.</p>
          <Button asChild className="mt-6 bg-primary hover:bg-primary/90 text-white">
            <Link href="/campaigns">Back to campaigns</Link>
          </Button>
        </main>
      </div>
    );
  }

  const status = statusConfig[campaign.status];
  const isPending  = campaign.status === "pending";
  const isApproved = campaign.status === "active" || campaign.status === "completed";

  const VARIANT_LABELS = ["A", "B", "C", "D", "E", "F"];
  const labelMap = Object.fromEntries(
    variants.map((v) => [v.variantId, { label: v.variant, segment: v.segment }])
  );
  const metricRows = (liveMetrics ?? []).map((m, i) => ({
    label:        labelMap[m.variant_id]?.label    ?? VARIANT_LABELS[i] ?? String(i + 1),
    segment:      labelMap[m.variant_id]?.segment  ?? m.variant_id,
    openRate:     +(m.open_rate  * 100).toFixed(1),
    clickRate:    +(m.click_rate * 100).toFixed(1),
    totalSent:    m.total_sent,
    uniqueClicks: m.unique_clicks,
  }));
  const avgOpen  = metricRows.length ? +(metricRows.reduce((s, r) => s + r.openRate,  0) / metricRows.length).toFixed(1) : 0;
  const avgClick = metricRows.length ? +(metricRows.reduce((s, r) => s + r.clickRate, 0) / metricRows.length).toFixed(1) : 0;
  const totalClicks = metricRows.reduce((s, r) => s + r.uniqueClicks, 0);
  const perfChartData = metricRows.map((r) => ({ date: `Var. ${r.label}`, openRate: r.openRate, clickRate: r.clickRate }));
  const [varA, varB] = metricRows;
  const compChartData = varA && varB
    ? [
        { name: "Open Rate",    variantA: varA.openRate,              variantB: varB.openRate },
        { name: "Click Rate",   variantA: varA.clickRate,             variantB: varB.clickRate },
        { name: "Sent (÷100)", variantA: +(varA.totalSent / 100).toFixed(1), variantB: +(varB.totalSent / 100).toFixed(1) },
      ]
    : [];

  const handleApprove = () => {
    setStatus(campaign.id, "active");
    if (id) executeApprovedCampaign(id);
    toast({ title: "Campaign approved", description: `${campaign.name} is now approved and being scheduled.` });
  };
  const handleReject = () => {
    setStatus(campaign.id, "rejected");
    toast({ title: "Campaign rejected", description: `${campaign.name} has been rejected.` });
  };
  const submitRevision = () => {
    setStatus(campaign.id, "pending", revisionNote);
    setRevisionOpen(false);
    setRevisionNote("");
    setView("overview");
    toast({ title: "Revision requested", description: "The campaign has been moved back to pending approval." });
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground/60 mb-5">
          <Link href="/" className="hover:text-foreground transition-colors">home</Link>
          <span className="text-border">/</span>
          <Link href="/campaigns" className="hover:text-foreground transition-colors">campaigns</Link>
          <span className="text-border">/</span>
          <span className="text-foreground/80 truncate max-w-[180px]">{campaign.name}</span>
        </nav>

        {/* Page header */}
        <div className="flex flex-wrap items-start justify-between gap-3 mb-2">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2.5 mb-1">
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-foreground tracking-tight break-words">
                {campaign.name}
              </h1>
              <span className={cn("text-[10px] font-mono font-medium border px-1.5 py-0.5 rounded shrink-0", status.className)}>
                {status.label}
              </span>
            </div>
            <p className="font-mono text-[11px] text-muted-foreground/60">
              {campaign.product} · Created {campaign.createdAt}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="shrink-0 font-mono text-xs border-border/60 h-8"
            onClick={() => router.push("/campaigns")}
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
            All campaigns
          </Button>
        </div>

        {/* Tab switcher (approved campaigns only) */}
        {isApproved && (
          <div className="mt-5 flex items-center gap-0 border-b border-border/40">
            {(["overview", "metrics"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={cn(
                  "relative px-4 py-2.5 font-mono text-xs transition-colors capitalize whitespace-nowrap",
                  view === v ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {v === "overview" ? "brief & strategy" : "metrics"}
                {view === v && (
                  <span
                    className="absolute bottom-0 left-0 right-0 h-px bg-primary"
                    style={{ boxShadow: "0 0 6px hsl(34 72% 52% / 0.7)" }}
                  />
                )}
              </button>
            ))}
          </div>
        )}

        {/* ── Overview tab ── */}
        {view === "overview" ? (
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Main column */}
            <div className="lg:col-span-2 space-y-5">

              {/* About Product */}
              <div className="border border-border/60 bg-card rounded-lg overflow-hidden">
                <div className="px-5 py-3 border-b border-border/40 bg-secondary/20">
                  <h2 className="font-display font-semibold text-sm text-foreground">About Product</h2>
                </div>
                <div className="p-5 space-y-5">
                  <p className="text-sm text-foreground/80 leading-relaxed">
                    {campaign.productDescription || "No product description available."}
                  </p>

                  {campaign.ctaLink && (
                    <div className="flex items-center gap-2 rounded-md border border-border/40 bg-secondary/20 px-3 py-2">
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <a href={campaign.ctaLink} target="_blank" rel="noopener noreferrer"
                         className="font-mono text-xs text-primary hover:underline truncate">
                        {campaign.ctaLink}
                      </a>
                    </div>
                  )}

                  {campaign.audienceTags.length > 0 && (
                    <div>
                      <p className="font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest mb-2">Targeting Audience</p>
                      <div className="flex flex-wrap gap-1.5">
                        {campaign.audienceTags.map((tag) => (
                          <span key={tag} className="inline-flex items-center rounded border border-border/40 bg-secondary px-2 py-0.5 font-mono text-xs text-foreground">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {campaign.contentHints.length > 0 && (
                    <div>
                      <p className="font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest mb-2">Content Hints</p>
                      <div className="flex flex-wrap gap-1.5">
                        {campaign.contentHints.map((hint) => (
                          <span key={hint} className="inline-flex items-center rounded border border-content-hint-border bg-content-hint-bg px-2 py-0.5 font-mono text-xs text-content-hint-text">
                            {hint}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Brief stats grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border/40 rounded-lg overflow-hidden border border-border/40 mt-2">
                    <BriefStat icon={Flag}       label="Goal"   value={campaign.goal} />
                    <BriefStat icon={DollarSign} label="Budget" value={campaign.budget} />
                    <BriefStat icon={Calendar}   label="Send"   value={campaign.scheduledSend} />
                    <BriefStat icon={Users}      label="Reach"  value={segments.reduce((a, s) => a + s.count, 0).toLocaleString()} />
                  </div>

                  {campaign.revisionNotes && (
                    <div className="rounded-md border border-stat-amber/25 bg-stat-amber/5 p-3">
                      <p className="font-mono text-[10px] text-stat-amber uppercase tracking-widest mb-1">Latest revision note</p>
                      <p className="text-sm text-foreground">{campaign.revisionNotes}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Customer Segments */}
              <div className="border border-border/60 bg-card rounded-lg overflow-hidden">
                <div className="px-5 py-3 border-b border-border/40 bg-secondary/20 flex items-center justify-between">
                  <h2 className="font-display font-semibold text-sm text-foreground">Customer Segments</h2>
                  <span className="font-mono text-[10px] text-stat-green/80 bg-stat-green/8 border border-stat-green/20 px-2 py-0.5 rounded">
                    AI generated
                  </span>
                </div>
                <div className="divide-y divide-border/40">
                  {segments.length === 0 ? (
                    <p className="p-5 font-mono text-sm text-muted-foreground/60">No segments generated yet.</p>
                  ) : segments.map((s) => (
                    <div key={s.name} className="p-4 hover:bg-accent/20 transition-colors">
                      <div className="flex items-start justify-between mb-1.5">
                        <h3 className="font-display font-semibold text-sm text-foreground">{s.name}</h3>
                        <span className="font-mono text-[10px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded border border-border/40 shrink-0 ml-2">
                          <Users className="h-2.5 w-2.5 inline mr-1" />
                          {s.count.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-x-3 font-mono text-[11px] text-muted-foreground/70 mb-1.5">
                        <span>Age {s.age}</span>
                        <span>{s.gender}</span>
                        <span>{s.location}</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{s.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Email Variants */}
              <div className="border border-border/60 bg-card rounded-lg overflow-hidden">
                <div className="px-5 py-3 border-b border-border/40 bg-secondary/20">
                  <h2 className="font-display font-semibold text-sm text-foreground">Email Variants</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border/40">
                  {variants.length === 0 ? (
                    <p className="p-5 font-mono text-sm text-muted-foreground/60 col-span-3">No email variants generated yet.</p>
                  ) : variants.map((v) => (
                    <button
                      key={v.variant}
                      type="button"
                      onClick={() => router.push(`/campaigns/${id}/${v.variantId}`)}
                      className="text-left p-4 hover:bg-accent/20 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-1.5">
                          <Mail className="h-3.5 w-3.5 text-muted-foreground/60" />
                          <span className="font-mono text-xs font-medium text-foreground">Variant {v.variant}</span>
                        </div>
                        <span className="font-mono text-[10px] text-muted-foreground/70 bg-secondary px-1.5 py-0.5 rounded border border-border/40">
                          {v.segment}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-foreground mb-1">{fillPlaceholders(v.subject)}</p>
                      <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                        {fillPlaceholders(stripHtml(v.body))}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-5">

              {/* Strategy Summary */}
              <div className="border border-border/60 bg-card rounded-lg overflow-hidden">
                <div className="px-5 py-3 border-b border-border/40 bg-secondary/20">
                  <h2 className="font-display font-semibold text-sm text-foreground">Strategy Summary</h2>
                </div>
                <div className="p-4 space-y-4">
                  <StrategyRow icon={Target}   label="Targeting"
                    value={strategy?.reasoning ? Object.values(strategy.reasoning)[0] ?? "Prioritize high-engagement segments first." : "Prioritize high-engagement segments first, then expand reach."} />
                  <StrategyRow icon={Clock}    label="Send time"
                    value={strategy?.send_schedule && Object.keys(strategy.send_schedule).length > 0
                      ? (() => {
                          const [seg, iso] = Object.entries(strategy.send_schedule)[0];
                          try { return `${seg.replace(/_/g, " ")}: ${new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}`; }
                          catch { return iso; }
                        })()
                      : campaign.scheduledSend} />
                  <StrategyRow icon={BarChart3} label="A/B test"
                    value={strategy?.ab_test_plan ? `${strategy.ab_test_plan.num_variants} variants — testing ${strategy.ab_test_plan.test_dimension}` : "Subject line, CTA copy, and send time."} />
                </div>
              </div>

              {/* Actions */}
              <div className="border border-border/60 bg-card rounded-lg overflow-hidden">
                <div className="px-5 py-3 border-b border-border/40 bg-secondary/20">
                  <h2 className="font-display font-semibold text-sm text-foreground">Actions</h2>
                </div>
                <div className="p-4 space-y-2">
                  <Button variant="outline" className="w-full justify-start font-mono text-xs border-border/60 h-9" asChild>
                    <Link href={`/campaigns/${id}/strategy`}>
                      <Target className="h-3.5 w-3.5 mr-2" /> View Strategy
                    </Link>
                  </Button>

                  {isApproved && (
                    <>
                      <Button className="w-full justify-start font-mono text-xs bg-primary hover:bg-primary/90 text-white h-9" onClick={() => setView("metrics")}>
                        <BarChart3 className="h-3.5 w-3.5 mr-2" /> View Metrics
                      </Button>
                      <Button variant="outline" className="w-full justify-start font-mono text-xs border-border/60 h-9" onClick={() => setRevisionOpen(true)}>
                        <RotateCcw className="h-3.5 w-3.5 mr-2" /> Request Revision
                      </Button>
                    </>
                  )}

                  {isPending && (
                    <>
                      <Button className="w-full justify-start font-mono text-xs bg-stat-green hover:bg-stat-green/90 text-primary-foreground h-9" onClick={handleApprove}>
                        <CheckCircle2 className="h-3.5 w-3.5 mr-2" /> Approve Campaign
                      </Button>
                      <Button variant="outline" className="w-full justify-start font-mono text-xs border-border/60 h-9" onClick={() => setRevisionOpen(true)}>
                        <RotateCcw className="h-3.5 w-3.5 mr-2" /> Request Revision
                      </Button>
                      <Button variant="outline" className="w-full justify-start font-mono text-xs border-destructive/40 text-destructive hover:bg-destructive/10 h-9" onClick={handleReject}>
                        <XCircle className="h-3.5 w-3.5 mr-2" /> Reject
                      </Button>
                    </>
                  )}

                  {campaign.status === "rejected" && (
                    <Button className="w-full justify-start font-mono text-xs bg-primary hover:bg-primary/90 text-white h-9" onClick={() => setStatus(campaign.id, "pending")}>
                      Move back to Pending
                    </Button>
                  )}
                  {campaign.status === "draft" && (
                    <Button className="w-full justify-start font-mono text-xs bg-primary hover:bg-primary/90 text-white h-9" onClick={() => setStatus(campaign.id, "pending")}>
                      Submit for Approval
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>

        ) : (
          /* ── Metrics tab ── */
          metricsLoading ? (
            <div className="mt-6 flex items-center justify-center py-20 border border-border/40 rounded-lg bg-card">
              <p className="font-mono text-sm text-muted-foreground/60">Loading metrics…</p>
            </div>
          ) : !liveMetrics || liveMetrics.length === 0 ? (
            <div className="mt-6 flex flex-col items-center justify-center py-20 space-y-3 border border-border/40 rounded-lg bg-card">
              <p className="font-mono text-sm text-muted-foreground">No metrics available yet.</p>
              <p className="font-mono text-xs text-muted-foreground/60">Execution may still be in progress — try refreshing in a few seconds.</p>
              <Button variant="outline" className="font-mono text-xs border-border/60" onClick={() => setLiveMetrics(null)}>
                Refresh Metrics
              </Button>
              <Button variant="ghost" size="sm" className="font-mono text-xs" onClick={() => setView("overview")}>
                Back to Overview
              </Button>
            </div>
          ) : (
            <div className="mt-6 space-y-5">
              {/* KPI grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border/40 rounded-lg overflow-hidden border border-border/40">
                {[
                  { label: "Avg Open Rate",  value: `${avgOpen}%` },
                  { label: "Avg Click Rate", value: `${avgClick}%` },
                  { label: "Total Clicks",   value: totalClicks.toLocaleString() },
                  { label: "Variants",       value: String(metricRows.length) },
                ].map((kpi) => (
                  <div key={kpi.label} className="bg-card p-5">
                    <p className="font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest">{kpi.label}</p>
                    <p className="font-display text-2xl font-bold text-foreground mt-1.5">{kpi.value}</p>
                  </div>
                ))}
              </div>

              <Card className="bg-card border-border/60">
                <CardHeader className="pb-2">
                  <CardTitle className="font-display text-base font-semibold">Performance by Variant</CardTitle>
                </CardHeader>
                <CardContent>
                  <ChartContainer config={lineConfig} className="h-[300px] w-full">
                    <LineChart data={perfChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="date" tick={{ fill: "hsl(var(--chart-axis))" }} className="text-xs" />
                      <YAxis tick={{ fill: "hsl(var(--chart-axis))" }} className="text-xs" unit="%" />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <ChartLegend content={<ChartLegendContent />} />
                      <Line type="monotone" dataKey="openRate"  stroke="var(--color-openRate)"  strokeWidth={2} dot />
                      <Line type="monotone" dataKey="clickRate" stroke="var(--color-clickRate)" strokeWidth={2} dot />
                    </LineChart>
                  </ChartContainer>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <Card className="bg-card border-border/60">
                  <CardHeader className="pb-2">
                    <CardTitle className="font-display text-base font-semibold">Variant Performance</CardTitle>
                  </CardHeader>
                  <CardContent className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border/40">
                          {["Variant", "Segment", "Sent", "Open", "Click"].map(h => (
                            <TableHead key={h} className="font-mono text-[10px] uppercase tracking-wider">{h}</TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {metricRows.map((r, i) => (
                          <TableRow key={r.label} className={cn("border-border/30", i % 2 && "bg-secondary/30")}>
                            <TableCell className="font-mono font-medium text-sm">{r.label}</TableCell>
                            <TableCell className="text-muted-foreground text-sm">{r.segment}</TableCell>
                            <TableCell className="font-mono text-sm">{r.totalSent.toLocaleString()}</TableCell>
                            <TableCell className="font-mono text-sm">{r.openRate}%</TableCell>
                            <TableCell className="font-mono text-sm">{r.clickRate}%</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                {compChartData.length > 0 && (
                  <Card className="bg-card border-border/60">
                    <CardHeader className="pb-2">
                      <CardTitle className="font-display text-base font-semibold">Variant A vs B</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ChartContainer config={barConfig} className="h-[260px] w-full">
                        <BarChart data={compChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                          <XAxis dataKey="name" tick={{ fill: "hsl(var(--chart-axis))" }} />
                          <YAxis tick={{ fill: "hsl(var(--chart-axis))" }} />
                          <ChartTooltip content={<ChartTooltipContent />} />
                          <ChartLegend content={<ChartLegendContent />} />
                          <Bar dataKey="variantA" fill="var(--color-variantA)" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="variantB" fill="var(--color-variantB)" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ChartContainer>
                    </CardContent>
                  </Card>
                )}
              </div>

              <div className="flex justify-end">
                <Button variant="outline" className="font-mono text-xs border-border/60" onClick={() => setView("overview")}>
                  Back to Overview
                </Button>
              </div>
            </div>
          )
        )}
      </main>

      {/* Revision dialog */}
      <Dialog open={revisionOpen} onOpenChange={setRevisionOpen}>
        <DialogContent className="bg-card border-border/60">
          <DialogHeader>
            <DialogTitle className="font-display">Request revision</DialogTitle>
            <DialogDescription className="font-mono text-xs">
              The campaign will be moved back to{" "}
              <span className="font-medium text-foreground">Pending Approval</span>{" "}
              for the team to update.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label className="font-mono text-xs text-muted-foreground uppercase tracking-widest">Notes for the team</Label>
            <Textarea
              rows={5}
              placeholder="Describe what needs to change…"
              value={revisionNote}
              onChange={(e) => setRevisionNote(e.target.value)}
              className="bg-background border-border/60 font-mono text-sm"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" className="font-mono text-xs border-border/60" onClick={() => setRevisionOpen(false)}>Cancel</Button>
            <Button className="font-mono text-xs bg-primary hover:bg-primary/90 text-white" onClick={submitRevision} disabled={!revisionNote.trim()}>
              Submit revision
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const BriefStat = ({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string }) => (
  <div className="bg-card p-3">
    <div className="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest mb-1">
      <Icon className="h-3 w-3" /> {label}
    </div>
    <div className="font-display text-sm font-semibold text-foreground">{value}</div>
  </div>
);

const StrategyRow = ({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string }) => (
  <div className="flex gap-3">
    <div className="h-8 w-8 rounded-md bg-primary/8 border border-primary/15 text-primary flex items-center justify-center shrink-0">
      <Icon className="h-3.5 w-3.5" />
    </div>
    <div>
      <p className="font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest">{label}</p>
      <p className="text-sm text-foreground mt-0.5">{value}</p>
    </div>
  </div>
);
