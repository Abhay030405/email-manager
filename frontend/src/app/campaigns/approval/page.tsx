'use client';

import { useState } from "react";
import Link from "next/link";
import { ChevronRight, ChevronDown, ChevronUp, CheckCircle2, RotateCcw, XCircle, ClipboardCheck, Mail } from "lucide-react";
import AppHeader from "@/components/AppHeader";
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

export default function CampaignApproval() {
  const [variants, setVariants] = useState(initialVariants);
  const [comment, setComment] = useState("");
  const [summaryOpen, setSummaryOpen] = useState(false);

  const updateVariant = (index: number, field: keyof VariantData, value: string) => {
    setVariants((prev) => prev.map((v, i) => (i === index ? { ...v, [field]: value } : v)));
  };

  const handleAction = (action: string) => {
    toast({
      title: `Campaign ${action}`,
      description:
        action === "Approved"
          ? "The campaign has been approved and is ready for execution."
          : action === "Revisions Requested"
          ? "Feedback has been sent to the campaign creator."
          : "The campaign has been rejected.",
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />
      <main className="max-w-screen-2xl mx-auto w-full px-4 sm:px-6 py-10">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground/60 mb-6">
          <Link href="/" className="hover:text-foreground transition-colors">home</Link>
          <span className="text-border">/</span>
          <Link href="/campaigns" className="hover:text-foreground transition-colors">campaigns</Link>
          <span className="text-border">/</span>
          <span className="text-foreground/80">approval</span>
        </nav>

        {/* Page header */}
        <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-stat-amber/80 bg-stat-amber/8 border border-stat-amber/20 px-2.5 py-1 rounded mb-3">
              <span className="w-1.5 h-1.5 rounded-full bg-stat-amber animate-pulse-dot" />
              Pending Approval
            </div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              Campaign Approval
            </h1>
            <p className="text-sm text-muted-foreground mt-1.5">
              Spring Product Launch · Review side-by-side variants before approving.
            </p>
          </div>
        </div>

        {/* Variant comparison grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-border/40 rounded-lg overflow-hidden border border-border/40 mb-6">
          {variants.map((v, i) => (
            <VariantCard key={v.label} variant={v} onChange={(field, value) => updateVariant(i, field, value)} />
          ))}
        </div>

        {/* Review decision */}
        <div className="border border-border/60 bg-card rounded-lg p-5 sm:p-6 mb-6">
          <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-primary/80 bg-primary/8 border border-primary/15 px-2.5 py-1 rounded mb-4">
            <ClipboardCheck className="h-3 w-3" />
            Review Decision
          </div>
          <div className="mb-4">
            <Label className="text-xs font-mono text-muted-foreground uppercase tracking-widest mb-1.5 block">
              Comments / Feedback
            </Label>
            <Textarea
              rows={4}
              className="bg-background border-border/60 font-mono text-sm"
              placeholder="Add any feedback or revision notes for the campaign team..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              className="bg-stat-green hover:bg-stat-green/90 text-primary-foreground font-mono text-sm"
              onClick={() => handleAction("Approved")}
            >
              <CheckCircle2 className="h-4 w-4 mr-1.5" />
              Approve
            </Button>
            <Button
              className="bg-stat-amber hover:bg-stat-amber/90 text-primary-foreground font-mono text-sm"
              onClick={() => handleAction("Revisions Requested")}
            >
              <RotateCcw className="h-4 w-4 mr-1.5" />
              Request Revisions
            </Button>
            <Button
              variant="outline"
              className="border-destructive/40 text-destructive hover:bg-destructive/10 font-mono text-sm"
              onClick={() => handleAction("Rejected")}
            >
              <XCircle className="h-4 w-4 mr-1.5" />
              Reject
            </Button>
          </div>
        </div>

        {/* Campaign summary */}
        <Collapsible open={summaryOpen} onOpenChange={setSummaryOpen}>
          <CollapsibleTrigger asChild>
            <button className="flex items-center gap-2 font-mono text-xs text-muted-foreground hover:text-foreground mb-3 transition-colors">
              {summaryOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              Campaign Summary
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-border/40 rounded-lg overflow-hidden border border-border/40">
              {[
                ["Product",               "Spring Collection 2026"],
                ["Goal",                  "Sales Conversion"],
                ["Target Segments",       "Urban Professionals, Young Trendsetters, Value Seekers"],
                ["Budget",                "$12,500"],
                ["Scheduled Send",        "Tue, Apr 15 · 10:00 AM"],
                ["Expected Total Reach",  "21,150 contacts"],
              ].map(([label, value]) => (
                <div key={label} className="bg-card p-4">
                  <dt className="font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest mb-1">{label}</dt>
                  <dd className="text-sm text-foreground">{value}</dd>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>

      </main>
    </div>
  );
}

const VariantCard = ({
  variant,
  onChange,
}: {
  variant: VariantData;
  onChange: (field: keyof VariantData, value: string) => void;
}) => (
  <div className="bg-card overflow-hidden">
    {/* Card header */}
    <div className="flex items-center justify-between px-5 py-3 border-b border-border/40 bg-secondary/20">
      <div className="flex items-center gap-2">
        <Mail className="h-3.5 w-3.5 text-muted-foreground/60" />
        <span className="font-display font-semibold text-sm text-foreground">{variant.label}</span>
      </div>
      <span className="font-mono text-[10px] text-muted-foreground/70 bg-secondary px-2 py-0.5 rounded border border-border/40">
        {variant.segment}
      </span>
    </div>

    {/* Card body */}
    <div className="p-5 space-y-4">
      <div className="space-y-1.5">
        <Label className="font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest">Subject Line</Label>
        <Input
          value={variant.subject}
          onChange={(e) => onChange("subject", e.target.value)}
          className="bg-background border-border/60 text-sm font-mono"
        />
      </div>
      <div className="space-y-1.5">
        <Label className="font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest">Email Body</Label>
        <Textarea
          rows={8}
          value={variant.body}
          onChange={(e) => onChange("body", e.target.value)}
          className="bg-background border-border/60 text-sm leading-relaxed font-mono"
        />
      </div>
      <div className="flex items-center justify-between pt-2 border-t border-border/40">
        <span className="font-mono text-[11px] text-muted-foreground">Send: <span className="text-foreground">{variant.sendTime}</span></span>
        <span className="font-mono text-[11px] text-muted-foreground">Reach: <span className="text-foreground">{variant.reach.toLocaleString()}</span></span>
      </div>
    </div>
  </div>
);
