import { useState, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  RotateCcw,
  XCircle,
  Clock,
  Target,
  Users,
  Calendar,
  DollarSign,
  Flag,
  Mail,
} from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCampaigns } from "@/context/CampaignsContext";
import { CampaignStatus, Segment, EmailVariant } from "@/data/campaignsData";
import { getCampaignSegments, getCampaignVariants } from "@/lib/api";
import { fillPlaceholders, stripHtml } from "@/lib/emailUtils";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const statusConfig: Record<CampaignStatus, { label: string; className: string }> = {
  draft: { label: "Draft", className: "bg-muted text-muted-foreground" },
  pending: { label: "Pending Approval", className: "bg-stat-amber/15 text-stat-amber" },
  active: { label: "Approved", className: "bg-primary/10 text-primary" },
  completed: { label: "Completed", className: "bg-stat-green/15 text-stat-green" },
  rejected: { label: "Rejected", className: "bg-destructive/10 text-destructive" },
};

const lineConfig = {
  openRate: { label: "Open Rate", color: "hsl(217, 91%, 60%)" },
  clickRate: { label: "Click Rate", color: "hsl(142, 71%, 45%)" },
};

const barConfig = {
  variantA: { label: "Variant A", color: "hsl(217, 91%, 60%)" },
  variantB: { label: "Variant B", color: "hsl(215, 16%, 47%)" },
};

type View = "overview" | "metrics";

const CampaignDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getCampaign, setStatus } = useCampaigns();
  const campaign = id ? getCampaign(id) : undefined;

  const [view, setView] = useState<View>("overview");
  const [revisionOpen, setRevisionOpen] = useState(false);
  const [revisionNote, setRevisionNote] = useState("");

  const [segments, setSegments] = useState<Segment[]>([]);
  const [variants, setVariants] = useState<EmailVariant[]>([]);

  useEffect(() => {
    if (!id) return;

    const LABELS = ["A", "B", "C", "D", "E", "F"];

    getCampaignSegments(id).then(({ segments: apiSegs }) => {
      setSegments(
        apiSegs.map((s) => {
          const c = s.segment_criteria ?? {};
          const age =
            c.age_range
              ? `${c.age_range.min ?? ""}–${c.age_range.max ?? ""}`
              : "All ages";
          const gender = c.gender?.join(", ") ?? "All";
          const location = c.cities?.slice(0, 3).join(", ") ?? "All locations";
          return {
            name: s.segment_name.replace(/_/g, " "),
            count: s.customer_ids?.length ?? 0,
            age,
            gender,
            location,
            description: s.description || `Segment: ${s.segment_name}`,
          };
        }),
      );
    });

    getCampaignVariants(id).then(({ variants: apiVars }) => {
      setVariants(
        apiVars.map((v, i) => ({
          variantId: v.variant_id,
          variant: LABELS[i] ?? String(i + 1),
          subject: v.subject_line,
          body: v.email_body,
          segment: v.segment_name.replace(/_/g, " "),
        })),
      );
    });
  }, [id]);

  if (!campaign) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <main className="max-w-3xl mx-auto px-4 py-20 text-center">
          <h1 className="text-2xl font-semibold text-foreground">Campaign not found</h1>
          <p className="text-muted-foreground mt-2">The campaign you're looking for doesn't exist.</p>
          <Button asChild className="mt-6">
            <Link to="/campaigns">Back to campaigns</Link>
          </Button>
        </main>
      </div>
    );
  }

  const status = statusConfig[campaign.status];
  const isPending = campaign.status === "pending";
  const isApproved = campaign.status === "active" || campaign.status === "completed";

  const handleApprove = () => {
    setStatus(campaign.id, "active");
    toast({ title: "Campaign approved", description: `${campaign.name} is now approved.` });
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
    toast({
      title: "Revision requested",
      description: "The campaign has been moved back to pending approval.",
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm text-muted-foreground mb-3">
          <Link to="/" className="hover:text-foreground">Home</Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <Link to="/campaigns" className="hover:text-foreground">Campaigns</Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground font-medium truncate min-w-0">{campaign.name}</span>
        </nav>

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4 mb-2">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight break-words">{campaign.name}</h1>
              <Badge className={cn("border-0 text-xs font-medium", status.className)}>
                {status.label}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1.5">
              {campaign.product} · Created {campaign.createdAt}
            </p>
          </div>
          <Button variant="outline" size="sm" className="shrink-0" onClick={() => navigate("/campaigns")}>
            <ArrowLeft className="h-4 w-4 mr-1.5" /> All campaigns
          </Button>
        </div>

        {/* View toggle (only when approved -> can view metrics) */}
        {isApproved && (
          <div className="mt-6 inline-flex w-full sm:w-auto p-1 bg-secondary rounded-lg border">
            {(["overview", "metrics"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={cn(
                  "flex-1 sm:flex-none px-3 sm:px-4 py-1.5 text-sm font-medium rounded-md transition-all capitalize whitespace-nowrap",
                  view === v ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {v === "overview" ? "Brief & Strategy" : "Metrics"}
              </button>
            ))}
          </div>
        )}

        {view === "overview" ? (
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main column */}
            <div className="lg:col-span-2 space-y-6">
              {/* About Product */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">About Product</CardTitle>
                </CardHeader>
                <CardContent className="space-y-8">
                  <p className="text-sm text-foreground leading-relaxed">
                    {campaign.productDescription || "No product description available."}
                  </p>
                  {campaign.ctaLink && (
                    <div className="flex items-center gap-2 rounded-md border bg-secondary/40 px-3 py-2">
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <a
                        href={campaign.ctaLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary hover:underline truncate"
                      >
                        {campaign.ctaLink}
                      </a>
                    </div>
                  )}
                  {campaign.audienceTags.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Targeting Audience</p>
                      <div className="flex flex-wrap gap-1.5">
                        {campaign.audienceTags.map((tag) => (
                          <span
                            key={tag}
                            className="inline-flex items-center rounded-full border bg-secondary px-2.5 py-0.5 text-xs font-medium text-foreground"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {campaign.contentHints.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Content Hints</p>
                      <div className="flex flex-wrap gap-1.5">
                        {campaign.contentHints.map((hint) => (
                          <span
                            key={hint}
                            className="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-2.5 py-0.5 text-xs font-medium text-violet-700"
                          >
                            {hint}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-3 border-t">
                    <BriefStat icon={Flag} label="Goal" value={campaign.goal} />
                    <BriefStat icon={DollarSign} label="Budget" value={campaign.budget} />
                    <BriefStat icon={Calendar} label="Send" value={campaign.scheduledSend} />
                    <BriefStat icon={Users} label="Reach" value={segments.reduce((acc, s) => acc + s.count, 0).toLocaleString()} />
                  </div>
                  {campaign.revisionNotes && (
                    <div className="rounded-md border border-stat-amber/30 bg-stat-amber/5 p-3">
                      <p className="text-xs font-medium text-stat-amber mb-0.5">Latest revision note</p>
                      <p className="text-sm text-foreground">{campaign.revisionNotes}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Strategy - segments */}
              <Card>
                <CardHeader className="pb-3 flex-row items-center justify-between">
                  <CardTitle className="text-base font-semibold">Customer Segments</CardTitle>
                  <Badge variant="secondary" className="bg-stat-green/10 text-stat-green border-0">
                    AI generated
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-3">
                  {segments.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No segments generated yet. Run the workflow to create segments.</p>
                  ) : segments.map((s) => (
                    <div key={s.name} className="rounded-lg border bg-secondary/30 p-4">
                      <div className="flex items-start justify-between mb-1.5">
                        <h3 className="text-sm font-semibold text-foreground">{s.name}</h3>
                        <Badge variant="secondary" className="gap-1 text-xs">
                          <Users className="h-3 w-3" />
                          {s.count.toLocaleString()}
                        </Badge>
                      </div>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground mb-1.5">
                        <span>Age {s.age}</span>
                        <span>{s.gender}</span>
                        <span>{s.location}</span>
                      </div>
                      <p className="text-sm text-muted-foreground leading-relaxed">{s.description}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Email variants */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Email Variants</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {variants.length === 0 ? (
                    <p className="text-sm text-muted-foreground col-span-3">No email variants generated yet. Run the workflow to generate content.</p>
                  ) : variants.map((v) => (
                    <button
                      key={v.variant}
                      type="button"
                      onClick={() => navigate(`/campaigns/${id}/${v.variantId}`)}
                      className="rounded-lg border bg-card overflow-hidden text-left transition-all hover:shadow-md hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <div className="px-4 py-2.5 border-b bg-muted/40 flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-xs font-semibold">Variant {v.variant}</span>
                        </div>
                        <Badge variant="secondary" className="text-[10px]">{v.segment}</Badge>
                      </div>
                      <div className="p-3 space-y-1.5">
                        <p className="text-xs font-medium text-foreground">{fillPlaceholders(v.subject)}</p>
                        <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                          {fillPlaceholders(stripHtml(v.body))}
                        </p>
                      </div>
                    </button>
                  ))}
                </CardContent>
              </Card>
            </div>

            {/* Sidebar - strategy + actions */}
            <div className="space-y-6">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Strategy Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <StrategyRow icon={Target} label="Targeting" value="Prioritize high-engagement segments first, then expand reach." />
                  <StrategyRow icon={Clock} label="Send time" value={campaign.scheduledSend} />
                  <StrategyRow icon={BarChart3} label="A/B test" value="Subject line, CTA copy, and send time." />
                </CardContent>
              </Card>

              {/* Action panel */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {isApproved && (
                    <>
                      <Button className="w-full justify-start" onClick={() => setView("metrics")}>
                        <BarChart3 className="h-4 w-4 mr-2" /> View Metrics
                      </Button>
                      <Button
                        variant="outline"
                        className="w-full justify-start"
                        onClick={() => setRevisionOpen(true)}
                      >
                        <RotateCcw className="h-4 w-4 mr-2" /> Request Revision
                      </Button>
                    </>
                  )}
                  {isPending && (
                    <>
                      <Button
                        className="w-full justify-start bg-stat-green hover:bg-stat-green/90 text-primary-foreground"
                        onClick={handleApprove}
                      >
                        <CheckCircle2 className="h-4 w-4 mr-2" /> Approve Campaign
                      </Button>
                      <Button
                        variant="outline"
                        className="w-full justify-start"
                        onClick={() => setRevisionOpen(true)}
                      >
                        <RotateCcw className="h-4 w-4 mr-2" /> Request Revision
                      </Button>
                      <Button
                        variant="outline"
                        className="w-full justify-start border-destructive text-destructive hover:bg-destructive/10"
                        onClick={handleReject}
                      >
                        <XCircle className="h-4 w-4 mr-2" /> Reject
                      </Button>
                    </>
                  )}
                  {campaign.status === "rejected" && (
                    <Button className="w-full justify-start" onClick={() => setStatus(campaign.id, "pending")}>
                      Move back to Pending
                    </Button>
                  )}
                  {campaign.status === "draft" && (
                    <Button className="w-full justify-start" onClick={() => setStatus(campaign.id, "pending")}>
                      Submit for Approval
                    </Button>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        ) : (
          /* METRICS VIEW */
          <div className="mt-6 space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricKpi label="Open Rate" value={`${campaign.metrics.openRate.toFixed(1)}%`} change="+3.1%" positive />
              <MetricKpi label="Click Rate" value={`${campaign.metrics.clickRate.toFixed(1)}%`} change="+2.4%" positive />
              <MetricKpi label="Conversions" value={campaign.metrics.conversions.toLocaleString()} change="+12%" positive />
              <MetricKpi label="ROI" value={campaign.metrics.roi} change="+8%" positive />
            </div>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">Performance Over Time</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={lineConfig} className="h-[300px] w-full">
                  <LineChart data={campaign.metrics.performance} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="date" tick={{ fill: "hsl(215, 16%, 47%)" }} className="text-xs" />
                    <YAxis tick={{ fill: "hsl(215, 16%, 47%)" }} className="text-xs" unit="%" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Line type="monotone" dataKey="openRate" stroke="var(--color-openRate)" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="clickRate" stroke="var(--color-clickRate)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold">Segment Performance</CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Segment</TableHead>
                        <TableHead>Recipients</TableHead>
                        <TableHead>Open</TableHead>
                        <TableHead>Click</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {campaign.metrics.segmentPerformance.map((s, i) => (
                        <TableRow key={s.name} className={i % 2 ? "bg-secondary/40" : ""}>
                          <TableCell className="font-medium">{s.name}</TableCell>
                          <TableCell>{s.recipients.toLocaleString()}</TableCell>
                          <TableCell>{s.openRate.toFixed(1)}%</TableCell>
                          <TableCell>{s.clickRate.toFixed(1)}%</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold">Variant Comparison</CardTitle>
                </CardHeader>
                <CardContent>
                  <ChartContainer config={barConfig} className="h-[260px] w-full">
                    <BarChart data={campaign.metrics.variantComparison} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="name" tick={{ fill: "hsl(215, 16%, 47%)" }} />
                      <YAxis tick={{ fill: "hsl(215, 16%, 47%)" }} />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <ChartLegend content={<ChartLegendContent />} />
                      <Bar dataKey="variantA" fill="var(--color-variantA)" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="variantB" fill="var(--color-variantB)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ChartContainer>
                </CardContent>
              </Card>
            </div>

            <div className="flex justify-end">
              <Button variant="outline" onClick={() => setView("overview")}>
                Back to Overview
              </Button>
            </div>
          </div>
        )}
      </main>

      {/* Request revision dialog */}
      <Dialog open={revisionOpen} onOpenChange={setRevisionOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request revision</DialogTitle>
            <DialogDescription>
              The campaign will be moved back to <span className="font-medium text-foreground">Pending Approval</span>{" "}
              for the team to update.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label className="text-sm">Notes for the team</Label>
            <Textarea
              rows={5}
              placeholder="Describe what needs to change…"
              value={revisionNote}
              onChange={(e) => setRevisionNote(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevisionOpen(false)}>Cancel</Button>
            <Button onClick={submitRevision} disabled={!revisionNote.trim()}>
              Submit revision
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const BriefStat = ({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) => (
  <div>
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-0.5">
      <Icon className="h-3.5 w-3.5" /> {label}
    </div>
    <div className="text-sm font-medium text-foreground">{value}</div>
  </div>
);

const StrategyRow = ({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) => (
  <div className="flex gap-3">
    <div className="h-8 w-8 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
      <Icon className="h-4 w-4" />
    </div>
    <div>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground">{value}</p>
    </div>
  </div>
);

const MetricKpi = ({
  label,
  value,
  change,
  positive,
}: {
  label: string;
  value: string;
  change: string;
  positive: boolean;
}) => (
  <Card>
    <CardContent className="p-5">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="flex items-end justify-between mt-1.5">
        <span className="text-2xl font-semibold text-foreground">{value}</span>
        <span className={cn("text-xs font-medium", positive ? "text-stat-green" : "text-destructive")}>
          {positive ? "↑" : "↓"} {change}
        </span>
      </div>
    </CardContent>
  </Card>
);

export default CampaignDetail;