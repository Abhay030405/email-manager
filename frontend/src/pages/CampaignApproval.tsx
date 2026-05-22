import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, ChevronDown, ChevronUp, CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { toast } from "@/hooks/use-toast";

interface VariantData {
  label: string;
  segment: string;
  subject: string;
  body: string;
  sendTime: string;
  reach: number;
}

const initialVariants: VariantData[] = [
  {
    label: "Variant A",
    segment: "Urban Professionals",
    subject: "Unlock Exclusive Early Access — Just for You",
    body: "Hi {{first_name}},\n\nWe're launching something special and wanted you to be the first to know. As a valued customer, you get exclusive early access to our newest collection before anyone else.\n\nExplore curated picks tailored to your style and preferences. This is your chance to stay ahead of the curve.\n\nShop the collection now and enjoy free shipping on your first order.",
    sendTime: "Tue, Apr 15 · 10:00 AM",
    reach: 12400,
  },
  {
    label: "Variant B",
    segment: "Young Trendsetters",
    subject: "🔥 Trending Now: Don't Miss Out on What's New",
    body: "Hey {{first_name}}!\n\nThe wait is over — our latest drop is here and it's already turning heads. Your feed is about to get a whole lot better.\n\nCheck out what everyone is talking about. Limited quantities available, so don't sleep on this one.\n\nTap below to shop the drop before it's gone. Trust us, you don't want to miss this.",
    sendTime: "Tue, Apr 15 · 2:00 PM",
    reach: 8750,
  },
];

const CampaignApproval = () => {
  const [variants, setVariants] = useState(initialVariants);
  const [comment, setComment] = useState("");
  const [summaryOpen, setSummaryOpen] = useState(false);

  const updateVariant = (index: number, field: keyof VariantData, value: string) => {
    setVariants((prev) =>
      prev.map((v, i) => (i === index ? { ...v, [field]: value } : v))
    );
  };

  const handleAction = (action: string) => {
    toast({
      title: `Campaign ${action}`,
      description: action === "Approved"
        ? "The campaign has been approved and is ready for execution."
        : action === "Revisions Requested"
        ? "Feedback has been sent to the campaign creator."
        : "The campaign has been rejected.",
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-10">
        <div>
            {/* Breadcrumb */}
            <nav className="flex items-center gap-1.5 text-sm text-muted-foreground mb-4">
              <Link to="/" className="hover:text-foreground">Home</Link>
              <ChevronRight className="h-3.5 w-3.5" />
              <Link to="/campaigns" className="hover:text-foreground">Campaigns</Link>
              <ChevronRight className="h-3.5 w-3.5" />
              <span className="text-foreground font-medium">Approval</span>
            </nav>

            {/* Header */}
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <h1 className="text-2xl font-semibold text-foreground">
                Campaign Approval — Spring Product Launch
              </h1>
              <Badge className="bg-stat-amber/15 text-stat-amber border-0 text-xs font-medium hover:bg-stat-amber/15">
                Pending Approval
              </Badge>
            </div>

            {/* Variant comparison */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
              {variants.map((v, i) => (
                <VariantCard key={v.label} variant={v} onChange={(field, value) => updateVariant(i, field, value)} />
              ))}
            </div>

            {/* Approval controls */}
            <div className="bg-card border rounded-lg p-5 mb-8">
              <h2 className="text-base font-semibold text-foreground mb-4">Review Decision</h2>
              <div className="mb-4">
                <Label className="text-sm font-medium text-foreground">Comments / Feedback</Label>
                <Textarea
                  rows={4}
                  className="mt-1.5"
                  placeholder="Add any feedback or revision notes for the campaign team..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                />
              </div>
              <div className="flex flex-wrap gap-3">
                <Button
                  className="bg-stat-green hover:bg-stat-green/90 text-primary-foreground"
                  onClick={() => handleAction("Approved")}
                >
                  <CheckCircle2 className="h-4 w-4 mr-1.5" />
                  Approve Campaign
                </Button>
                <Button
                  className="bg-stat-amber hover:bg-stat-amber/90 text-primary-foreground"
                  onClick={() => handleAction("Revisions Requested")}
                >
                  <RotateCcw className="h-4 w-4 mr-1.5" />
                  Request Revisions
                </Button>
                <Button
                  variant="outline"
                  className="border-destructive text-destructive hover:bg-destructive/10"
                  onClick={() => handleAction("Rejected")}
                >
                  <XCircle className="h-4 w-4 mr-1.5" />
                  Reject
                </Button>
              </div>
            </div>

            {/* Campaign summary collapsible */}
            <Collapsible open={summaryOpen} onOpenChange={setSummaryOpen}>
              <CollapsibleTrigger asChild>
                <button className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3 hover:text-primary">
                  {summaryOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  Campaign Summary
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="bg-card border rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
                  <SummaryRow label="Product" value="Spring Collection 2026" />
                  <SummaryRow label="Goal" value="Sales Conversion" />
                  <SummaryRow label="Target Segments" value="Urban Professionals, Young Trendsetters, Value Seekers" />
                  <SummaryRow label="Budget" value="$12,500" />
                  <SummaryRow label="Scheduled Send" value="Tue, Apr 15 · 10:00 AM" />
                  <SummaryRow label="Expected Total Reach" value="21,150 contacts" />
                </div>
              </CollapsibleContent>
            </Collapsible>
        </div>
      </main>
    </div>
  );
};

const VariantCard = ({
  variant,
  onChange,
}: {
  variant: VariantData;
  onChange: (field: keyof VariantData, value: string) => void;
}) => (
  <div className="bg-card border rounded-lg overflow-hidden">
    <div className="flex items-center justify-between px-5 py-3 border-b bg-muted/50">
      <span className="text-sm font-semibold text-foreground">{variant.label}</span>
      <Badge variant="secondary" className="text-xs">{variant.segment}</Badge>
    </div>
    <div className="p-5 space-y-4">
      <div className="space-y-1.5">
        <Label className="text-xs font-medium text-muted-foreground">Subject Line</Label>
        <Input
          value={variant.subject}
          onChange={(e) => onChange("subject", e.target.value)}
          className="text-sm"
        />
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs font-medium text-muted-foreground">Email Body</Label>
        <Textarea
          rows={8}
          value={variant.body}
          onChange={(e) => onChange("body", e.target.value)}
          className="text-sm leading-relaxed"
        />
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground pt-1 border-t">
        <span>Send: {variant.sendTime}</span>
        <span>Reach: {variant.reach.toLocaleString()}</span>
      </div>
    </div>
  </div>
);

const SummaryRow = ({ label, value }: { label: string; value: string }) => (
  <div>
    <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
    <dd className="text-sm text-foreground mt-0.5">{value}</dd>
  </div>
);

export default CampaignApproval;
