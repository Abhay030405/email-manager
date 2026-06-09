'use client';

import { Fragment, useRef, useState } from "react";
import { BookOpen, Crosshair, FileSearch, Package, Pencil, Plus, SlidersHorizontal, Trash2, Users, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { CampaignProgressTracker } from "@/components/campaign/CampaignProgressTracker";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface AudienceGroup {
  min_age: number | null;
  max_age: number | null;
  gender: string | null;
  min_income: number | null;
  max_income: number | null;
  KYC_status: string | null;
  App_Installed: string | null;
  Existing_Customer: string | null;
  Credit_score: number | null;
  Social_Media_Active: string | null;
}

const EMPTY_GROUP: AudienceGroup = {
  min_age: null, max_age: null, gender: null,
  min_income: null, max_income: null, KYC_status: null,
  App_Installed: null, Existing_Customer: null,
  Credit_score: null, Social_Media_Active: null,
};

interface ParsedBriefSections {
  product_details: { product_name: string; product_description: string; cta_link: string };
  target_audience: Record<string, AudienceGroup>;
  campaign_goal: { objective: string };
  campaign_preferences: { email_tone: string; campaign_name: string; content_hints: string };
}

const GROUP_LABELS: Record<keyof AudienceGroup, string> = {
  min_age: "Min Age",
  max_age: "Max Age",
  gender: "Gender",
  min_income: "Min Income",
  max_income: "Max Income",
  KYC_status: "KYC",
  App_Installed: "App Installed",
  Existing_Customer: "Existing Customer",
  Credit_score: "Credit Score",
  Social_Media_Active: "Social Media Active",
};

const AudienceGroupCard = ({
  name,
  group,
  onEdit,
  onDelete,
}: {
  name: string;
  group: AudienceGroup;
  onEdit: () => void;
  onDelete: () => void;
}) => {
  const fields = (Object.keys(GROUP_LABELS) as (keyof AudienceGroup)[]).filter(
    (k) => group[k] !== null && group[k] !== undefined
  );
  return (
    <div className="rounded-md border border-border/40 bg-secondary/20 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[10px] text-muted-foreground/60 uppercase tracking-widest">{name}</p>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onEdit}
            className="h-6 w-6 rounded flex items-center justify-center text-muted-foreground/50 hover:text-primary hover:bg-primary/10 transition-colors"
            title="Edit group"
          >
            <Pencil className="h-3 w-3" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="h-6 w-6 rounded flex items-center justify-center text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-colors"
            title="Delete group"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>
      {fields.length === 0 ? (
        <p className="text-xs text-muted-foreground italic">No specific criteria set</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {fields.map((k) => (
            <span
              key={k}
              className="inline-flex items-center gap-1 rounded-full border bg-background px-2 py-0.5 text-xs"
            >
              <span className="text-muted-foreground">{GROUP_LABELS[k]}:</span>
              <span className="font-medium">{String(group[k])}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

const STEPS = ["Product Details", "Target Audience", "Campaign Goal", "Campaign Preferences"];

const Stepper = ({ currentStep }: { currentStep: number }) => (
  <div className="px-4 sm:px-6 pt-5 pb-4 border-b border-border/40">
    <div className="flex items-center">
      {STEPS.map((label, i) => (
        <Fragment key={label}>
          <div className="flex flex-col items-center shrink-0">
            {/* Step number / check */}
            <div
              className={cn(
                "w-7 h-7 rounded-md flex items-center justify-center font-mono text-xs font-medium border transition-colors",
                i < currentStep
                  ? "bg-primary border-primary text-white"
                  : i === currentStep
                  ? "border-primary/60 text-primary bg-primary/8"
                  : "border-border/50 text-muted-foreground/50 bg-background"
              )}
            >
              {i < currentStep ? "✓" : String(i + 1).padStart(2, "0")}
            </div>
            {/* Label */}
            <span
              className={cn(
                "mt-1.5 font-mono text-[9px] text-center leading-tight w-16 uppercase tracking-wider",
                i === currentStep ? "text-primary" : i < currentStep ? "text-foreground/70" : "text-muted-foreground/40"
              )}
            >
              {label}
            </span>
          </div>
          {/* Connector */}
          {i < STEPS.length - 1 && (
            <div className={cn("flex-1 h-px mx-1.5 mb-4", i < currentStep ? "bg-primary/60" : "bg-border/40")} />
          )}
        </Fragment>
      ))}
    </div>
  </div>
);

const Field = ({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) => (
  <div className="space-y-1.5">
    <Label className="text-sm font-medium text-foreground">{label}</Label>
    {children}
    {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
  </div>
);

const ReviewRow = ({ label, value }: { label: string; value: string }) =>
  value ? (
    <div className="space-y-0.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground break-words">{value}</p>
    </div>
  ) : null;

const ReviewSection = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="space-y-3">
    <h3 className="font-mono text-[10px] font-medium uppercase tracking-widest text-muted-foreground/60 border-b border-border/40 pb-1.5">{title}</h3>
    <div className="space-y-3">{children}</div>
  </div>
);

const CampaignForm = () => {
  const [phase, setPhase] = useState<"brief" | "wizard" | "review">("brief");
  const [step, setStep] = useState(0);
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [trackerCampaignId, setTrackerCampaignId] = useState<string | null>(null);

  // Brief
  const [brief, setBrief] = useState("");
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step 0 — Product Details
  const [productName, setProductName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [ctaLink, setCtaLink] = useState("");

  // Step 1 — Target Audience
  const [audienceGroups, setAudienceGroups] = useState<Record<string, AudienceGroup>>({});

  // Group add/edit form
  const [groupFormOpen, setGroupFormOpen] = useState(false);
  const [editingGroupKey, setEditingGroupKey] = useState<string | null>(null); // null = add mode
  const [groupFormName, setGroupFormName] = useState("");
  const [groupFormData, setGroupFormData] = useState<AudienceGroup>({ ...EMPTY_GROUP });

  // Step 2 — Campaign Goal
  const [campaignGoal, setCampaignGoal] = useState("");

  // Step 3 — Campaign Preferences (all optional)
  const [emailTone, setEmailTone] = useState("");
  const [campaignName, setCampaignName] = useState("");
  const [contentHints, setContentHints] = useState("");

  const openAddGroup = () => {
    const next = `Group ${Object.keys(audienceGroups).length + 1}`;
    setGroupFormName(next);
    setGroupFormData({ ...EMPTY_GROUP });
    setEditingGroupKey(null);
    setGroupFormOpen(true);
  };

  const openEditGroup = (key: string) => {
    setGroupFormName(key);
    setGroupFormData({ ...audienceGroups[key] });
    setEditingGroupKey(key);
    setGroupFormOpen(true);
  };

  const closeGroupForm = () => {
    setGroupFormOpen(false);
    setEditingGroupKey(null);
  };

  const saveGroup = () => {
    const name = groupFormName.trim() || `Group ${Object.keys(audienceGroups).length + 1}`;
    if (editingGroupKey !== null) {
      // Edit: replace old key (may have been renamed)
      const entries = Object.entries(audienceGroups).map(([k, v]) =>
        k === editingGroupKey ? [name, groupFormData] : [k, v]
      );
      setAudienceGroups(Object.fromEntries(entries));
    } else {
      setAudienceGroups((prev) => ({ ...prev, [name]: groupFormData }));
    }
    closeGroupForm();
  };

  const deleteGroup = (key: string) => {
    setAudienceGroups((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const setGroupField = <K extends keyof AudienceGroup>(field: K, raw: string) => {
    const numFields: (keyof AudienceGroup)[] = ["min_age", "max_age", "min_income", "max_income", "Credit_score"];
    const value = raw === "" ? null : numFields.includes(field) ? (Number(raw) || null) : raw;
    setGroupFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleTxtUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith(".txt")) {
      toast({ title: "Invalid file type", description: "Please upload a .txt file.", variant: "destructive" });
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = (ev.target?.result as string) ?? "";
      setBrief(text.slice(0, 5000));
      setUploadedFileName(file.name);
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const clearUploadedFile = () => {
    setBrief("");
    setUploadedFileName(null);
  };

  const briefHasContent = brief.trim().length > 0 || !!uploadedFileName;

  const handleAnalyse = async () => {
    const briefText = brief.trim();
    if (!briefText) return;
    setIsAnalysing(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/campaigns/parse-brief`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief_text: briefText }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Server error ${res.status}`);
      }
      const data: ParsedBriefSections = await res.json();

      setProductName(data.product_details.product_name);
      setProductDescription(data.product_details.product_description);
      setCtaLink(data.product_details.cta_link);

      setAudienceGroups(data.target_audience);

      setCampaignGoal(data.campaign_goal.objective);

      setEmailTone(data.campaign_preferences.email_tone);
      setCampaignName(data.campaign_preferences.campaign_name);
      setContentHints(data.campaign_preferences.content_hints);

      setStep(0);
      setPhase("wizard");
      toast({ title: "Brief analysed", description: "Review and adjust the pre-filled fields." });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      toast({ title: "Analysis failed", description: message, variant: "destructive" });
    } finally {
      setIsAnalysing(false);
    }
  };

  const isCurrentStepValid = (): boolean => {
    switch (step) {
      case 0: return !!(productName.trim() && productDescription.trim() && ctaLink.trim());
      case 1: return Object.keys(audienceGroups).length > 0 && !groupFormOpen;
      case 2: return !!campaignGoal.trim();
      case 3: return true;
      default: return false;
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      // 1. Create campaign in DB with confirmed parsed data
      const createRes = await fetch(`${API_BASE}/api/v1/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          campaign_brief: brief.trim(),
          parsed_data: {
            product_details: {
              product_name: productName.trim(),
              product_description: productDescription.trim(),
              cta_link: ctaLink.trim(),
            },
            target_audience: audienceGroups,
            campaign_goal: {
              objective: campaignGoal.trim(),
            },
            campaign_preferences: {
              email_tone: emailTone,
              campaign_name: campaignName.trim(),
              content_hints: contentHints.trim(),
            },
          },
        }),
      });
      if (!createRes.ok) {
        const err = await createRes.json().catch(() => ({}));
        throw new Error(err.detail ?? `Failed to create campaign (${createRes.status})`);
      }
      const campaign = await createRes.json();
      const campaignId: string = campaign.campaign_id;

      // 2. Start async AI workflow (returns immediately; poll /status for progress)
      const startRes = await fetch(`${API_BASE}/api/v1/campaigns/${campaignId}/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!startRes.ok) {
        const err = await startRes.json().catch(() => ({}));
        throw new Error(err.detail ?? `Workflow failed (${startRes.status})`);
      }

      // Show progress tracker — it replaces the form until the pipeline finishes
      setTrackerCampaignId(campaignId);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      toast({ title: "Generation failed", description: message, variant: "destructive" });
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Progress tracker (replaces form while pipeline runs) ────────────────
  if (trackerCampaignId) {
    return (
      <CampaignProgressTracker
        campaignId={trackerCampaignId}
        onFinished={() => {
          setTrackerCampaignId(null);
          setPhase("brief");
          setStep(0);
          setBrief("");
          setUploadedFileName(null);
        }}
      />
    );
  }

  // ── Phase 3: Review ──────────────────────────────────────────────────────
  if (phase === "review") {
    return (
      <div className="bg-card border border-border/60 rounded-lg overflow-hidden">
        <div className="px-4 sm:px-6 py-4 border-b border-border/40 bg-secondary/20">
          <h2 className="font-display font-semibold text-foreground">Review Campaign Details</h2>
          <p className="font-mono text-[11px] text-muted-foreground/60 mt-0.5">Check everything before generating the strategy.</p>
        </div>

        <div className="px-4 sm:px-6 py-6 space-y-6">
          <ReviewSection title="Product Details">
            <ReviewRow label="Product Name" value={productName} />
            <ReviewRow label="Product Description" value={productDescription} />
            <ReviewRow label="CTA Link" value={ctaLink} />
          </ReviewSection>

          <ReviewSection title="Target Audience">
            {Object.keys(audienceGroups).length === 0 ? (
              <p className="text-sm text-muted-foreground italic">No audience groups.</p>
            ) : (
              Object.entries(audienceGroups).map(([name, group]) => (
                <AudienceGroupCard key={name} name={name} group={group} onEdit={() => {}} onDelete={() => {}} />
              ))
            )}
          </ReviewSection>

          <ReviewSection title="Campaign Goal">
            <ReviewRow label="Objective" value={campaignGoal} />
          </ReviewSection>

          <ReviewSection title="Campaign Preferences">
            <ReviewRow label="Tone of email" value={emailTone} />
            <ReviewRow label="Campaign name" value={campaignName} />
            <ReviewRow label="Content hints" value={contentHints} />
          </ReviewSection>
        </div>

        <div className="px-4 sm:px-6 py-4 border-t flex gap-3">
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            disabled={isGenerating}
            onClick={() => { setStep(STEPS.length - 1); setPhase("wizard"); }}
          >
            Back
          </Button>
          <Button
            type="button"
            className="flex-1"
            disabled={isGenerating}
            onClick={handleGenerate}
          >
            {isGenerating ? "Generating…" : "Generate Campaign Strategy"}
          </Button>
        </div>
      </div>
    );
  }
  // ── Analysing overlay ────────────────────────────────────────────────────
  if (isAnalysing) {
    const extractions = [
      { icon: Package,           title: "Product Details",     bars: [90, 70, 55],       delay: "0s"   },
      { icon: Users,             title: "Target Audience",     bars: [80, 95, 60],       delay: "0.7s" },
      { icon: Crosshair,         title: "Campaign Goal",       bars: [85, 65],           delay: "1.4s" },
      { icon: SlidersHorizontal, title: "Campaign Preferences",bars: [75, 90, 50, 70],   delay: "2.1s" },
    ];
    return (
      <div className="bg-card border border-border/60 rounded-lg overflow-hidden">
        {/* Top accent */}
        <div className="h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />

        {/* Header bar */}
        <div className="px-5 py-3 border-b border-border/40 bg-secondary/20 flex items-center gap-3">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
          <span className="font-mono text-[11px] text-primary/80 uppercase tracking-widest">Processing</span>
          <div className="flex-1 h-px bg-border/30" />
          <FileSearch className="h-3.5 w-3.5 text-muted-foreground/40" />
          <span className="font-mono text-[10px] text-muted-foreground/40">Analysing campaign brief…</span>
        </div>

        <div className="flex divide-x divide-border/30" style={{ height: "420px" }}>

          {/* ── Left: brief text with scanner beam ─────────────────────────── */}
          <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
            <div className="px-4 py-2.5 border-b border-border/20 bg-secondary/10 flex items-center gap-2">
              <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/40">Input Brief</span>
              <div className="flex-1 h-px bg-border/20" />
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-1 w-1 rounded-full bg-primary/50 animate-pulse" style={{ animationDelay: `${i * 0.25}s` }} />
                ))}
              </div>
            </div>

            {/* Text + scanner */}
            <div className="relative flex-1 overflow-hidden px-5 py-4">
              {/* Scanner beam */}
              <div
                className="absolute inset-x-0 h-10 pointer-events-none z-10 animate-scan-beam"
                style={{
                  background: "linear-gradient(to bottom, transparent, hsl(34 72% 52% / 0.08) 40%, hsl(214 80% 58% / 0.06) 60%, transparent)",
                }}
              />
              {/* Scanner hairline */}
              <div
                className="absolute inset-x-4 h-px pointer-events-none z-10 animate-scan-beam"
                style={{
                  background: "linear-gradient(to right, transparent, hsl(34 72% 52% / 0.6), hsl(214 80% 58% / 0.4), transparent)",
                  marginTop: "20px",
                }}
              />
              {/* Top fade */}
              <div className="absolute top-0 inset-x-0 h-8 bg-gradient-to-b from-card to-transparent z-20 pointer-events-none" />
              {/* Bottom fade */}
              <div className="absolute bottom-0 inset-x-0 h-24 bg-gradient-to-t from-card via-card/80 to-transparent z-20 pointer-events-none" />

              <pre className="font-mono text-[11px] text-muted-foreground/45 whitespace-pre-wrap leading-relaxed break-words">
                {brief
                  .replace(/\r\n/g, "\n")   // normalise Windows endings
                  .trim()
                  .replace(/\n{2,}/g, "\x00") // protect paragraph breaks
                  .replace(/\n/g, " ")         // collapse soft line-wraps → space
                  .replace(/\x00/g, "\n\n")   // restore paragraph breaks
                || "No brief content…"}
              </pre>
            </div>
          </div>

          {/* ── Right: extraction cards ─────────────────────────────────────── */}
          <div className="w-72 shrink-0 flex flex-col divide-y divide-border/20 h-full">
            {extractions.map(({ icon: Icon, title, bars, delay }) => (
              <div key={title} className="relative flex-1 px-4 py-4 space-y-3 overflow-hidden">
                {/* Glowing top edge per card */}
                <div
                  className="absolute top-0 inset-x-0 h-px animate-pulse"
                  style={{
                    background: "linear-gradient(to right, transparent, hsl(34 72% 52% / 0.6), transparent)",
                    animationDelay: delay,
                    animationDuration: "2s",
                  }}
                />

                {/* Card header */}
                <div className="flex items-center gap-2">
                  <div
                    className="h-6 w-6 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center animate-pulse"
                    style={{ animationDelay: delay, animationDuration: "2s" }}
                  >
                    <Icon className="h-3 w-3 text-primary" />
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-foreground/60">{title}</span>
                  <div className="ml-auto flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="h-1 w-1 rounded-full bg-primary/50 animate-bounce"
                        style={{ animationDelay: `calc(${delay} + ${i * 0.18}s)` }}
                      />
                    ))}
                  </div>
                </div>

                {/* Flowing data bars */}
                <div className="space-y-2 pl-1">
                  {bars.map((w, i) => (
                    <div
                      key={i}
                      className="h-1.5 rounded-full overflow-hidden bg-secondary/40"
                      style={{ width: `${w}%`, animationDelay: delay }}
                    >
                      <div className="h-full w-full shimmer-bar" style={{ animationDelay: `calc(${delay} + ${i * 0.3}s)` }} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

        </div>
      </div>
    );
  }

  // ── Phase 1: Campaign Brief ──────────────────────────────────────────────
  if (phase === "brief") {
    return (
      <div className="flex gap-4 items-stretch">

        {/* ── Left card: form ─────────────────────────────────────────────── */}
        <div className="flex-1 min-w-0 bg-card border border-border/60 rounded-lg overflow-hidden flex flex-col">
          <div className="px-4 sm:px-6 py-4 border-b border-border/40 bg-secondary/20">
            <h2 className="font-display font-semibold text-foreground">Campaign Brief</h2>
            <p className="font-mono text-[11px] text-muted-foreground/60 mt-0.5">Describe your campaign and let AI do the rest.</p>
          </div>

          <div className="px-4 sm:px-6 py-6 space-y-4 flex-1 flex flex-col">
            <div className="space-y-1.5 flex-1 flex flex-col">
              <Label className="text-sm font-medium text-foreground">Campaign Brief</Label>
              <Textarea
                className="flex-1 resize-none"
                placeholder="Describe your campaign objectives, tone, key messages..."
                value={brief}
                onChange={(e) => {
                  setBrief(e.target.value);
                  if (uploadedFileName) setUploadedFileName(null);
                }}
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="flex-1 border-t border-muted" />
              <span className="text-xs text-muted-foreground">or</span>
              <div className="flex-1 border-t border-muted" />
            </div>

            <input ref={fileInputRef} type="file" accept=".txt" className="hidden" onChange={handleTxtUpload} />
            {uploadedFileName ? (
              <div className="flex items-center gap-2 rounded-md border border-muted bg-muted/40 px-3 py-2 text-sm">
                <span className="flex-1 truncate text-foreground">{uploadedFileName}</span>
                <button
                  type="button"
                  onClick={clearUploadedFile}
                  className="text-destructive hover:text-destructive/80 text-xs font-medium shrink-0"
                >
                  Remove
                </button>
              </div>
            ) : (
              <div className="space-y-1">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full rounded-md border border-dashed border-border/50 px-4 py-3 font-mono text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors text-center"
                >
                  Upload the Campaign brief
                </button>
                <p className="text-xs text-muted-foreground text-center">*.txt files are only allowed</p>
              </div>
            )}
          </div>

          <div className="px-4 sm:px-6 py-4 border-t border-border/40">
            <Button
              type="button"
              className="w-full"
              disabled={!briefHasContent || isAnalysing}
              onClick={handleAnalyse}
            >
              {isAnalysing ? "Analysing…" : "Analyse the Campaign"}
            </Button>
          </div>
        </div>

        {/* ── Right card: guide ───────────────────────────────────────────── */}
        <div className="w-72 shrink-0 bg-card border border-border/60 rounded-lg overflow-hidden">

          {/* Top accent line */}
          <div className="h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />

          {/* Header */}
          <div className="px-4 py-4 border-b border-border/40 bg-secondary/20 flex items-center gap-3">
            <div className="h-7 w-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
              <BookOpen className="h-3.5 w-3.5 text-primary" />
            </div>
            <div className="leading-none">
              <p className="font-display font-semibold text-sm text-foreground">Brief Guide</p>
              <p className="font-mono text-[10px] text-muted-foreground/50 mt-1">What to include</p>
            </div>
          </div>

          {/* Sections */}
          <div className="divide-y divide-border/20">

            {/* 01 — Product Details */}
            <div className="px-4 py-4 space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] font-semibold text-primary/60 w-5 shrink-0">01</span>
                <Package className="h-3 w-3 text-muted-foreground/40 shrink-0" />
                <span className="text-xs font-medium text-foreground/80">Product Details</span>
              </div>
              <ul className="pl-7 space-y-2">
                <li className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                  <span className="shrink-0 mt-px">·</span>
                  <span>Product Name <code className="ml-1 font-mono text-[10px] bg-secondary/70 border border-border/40 text-muted-foreground/50 px-1.5 py-0.5 rounded">XDeposit</code></span>
                </li>
                <li className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                  <span className="shrink-0 mt-px">·</span>
                  <span>Description <code className="ml-1 font-mono text-[10px] bg-secondary/70 border border-border/40 text-muted-foreground/50 px-1.5 py-0.5 rounded">"1% above market rate"</code></span>
                </li>
                <li className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                  <span className="shrink-0 mt-px">·</span>
                  <span>CTA Link <code className="ml-1 font-mono text-[10px] bg-secondary/70 border border-border/40 text-muted-foreground/50 px-1.5 py-0.5 rounded">superbfsi.com/…</code></span>
                </li>
              </ul>
            </div>

            {/* 02 — Target Audience */}
            <div className="px-4 py-4 space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] font-semibold text-primary/60 w-5 shrink-0">02</span>
                <Users className="h-3 w-3 text-muted-foreground/40 shrink-0" />
                <span className="text-xs font-medium text-foreground/80">Target Audience</span>
              </div>
              <ul className="pl-7 space-y-2">
                <li className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                  <span className="shrink-0 mt-px">·</span>
                  <span>Who to target <code className="ml-1 font-mono text-[10px] bg-secondary/70 border border-border/40 text-muted-foreground/50 px-1.5 py-0.5 rounded">age 25–45</code></span>
                </li>
                <li className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                  <span className="shrink-0 mt-px">·</span>
                  <span>Location <code className="ml-1 font-mono text-[10px] bg-secondary/70 border border-border/40 text-muted-foreground/50 px-1.5 py-0.5 rounded">Metro cities</code></span>
                </li>
                <li className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                  <span className="shrink-0 mt-px">·</span>
                  <span>Filters <code className="ml-1 font-mono text-[10px] bg-secondary/70 border border-border/40 text-muted-foreground/50 px-1.5 py-0.5 rounded">High income</code></span>
                </li>
              </ul>
            </div>

            {/* 03 — Campaign Goal */}
            <div className="px-4 py-4 space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] font-semibold text-primary/60 w-5 shrink-0">03</span>
                <Crosshair className="h-3 w-3 text-muted-foreground/40 shrink-0" />
                <span className="text-xs font-medium text-foreground/80">Campaign Goal</span>
              </div>
              <ul className="pl-7 space-y-2">
                {["Maximize click-throughs", "Drive sign-ups", "Increase awareness"].map((eg) => (
                  <li key={eg} className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                    <span className="shrink-0 mt-px">·</span>
                    <code className="font-mono text-[10px] bg-secondary/70 border border-border/40 text-muted-foreground/50 px-1.5 py-0.5 rounded">{eg}</code>
                  </li>
                ))}
              </ul>
            </div>

            {/* 04 — Preferences */}
            <div className="px-4 py-4 space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] font-semibold text-primary/60 w-5 shrink-0">04</span>
                <SlidersHorizontal className="h-3 w-3 text-muted-foreground/40 shrink-0" />
                <span className="text-xs font-medium text-foreground/80">Preferences</span>
                <span className="font-mono text-[9px] text-muted-foreground/35 bg-secondary/50 border border-border/25 px-1.5 py-0.5 rounded-full leading-none">optional</span>
              </div>
              <ul className="pl-7 space-y-2">
                <li className="text-[11px] text-muted-foreground/60 space-y-1">
                  <span className="flex items-center gap-1.5">
                    <span className="shrink-0">·</span> Tone
                  </span>
                  <div className="flex gap-1 flex-wrap pl-3">
                    {["Formal", "Friendly", "Urgent"].map((t) => (
                      <code key={t} className="font-mono text-[10px] bg-secondary/70 border border-border/40 text-muted-foreground/50 px-1.5 py-0.5 rounded">{t}</code>
                    ))}
                  </div>
                </li>
                <li className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                  <span className="shrink-0 mt-px">·</span> Campaign name
                </li>
                <li className="flex items-start gap-2 text-[11px] text-muted-foreground/60">
                  <span className="shrink-0 mt-px">·</span> Content hints
                </li>
              </ul>
            </div>

          </div>
        </div>

      </div>
    );
  }

  // ── Phase 2: Step wizard ─────────────────────────────────────────────────
  return (
    <form className="bg-card border border-border/60 rounded-lg overflow-hidden">
      <Stepper currentStep={step} />

      <div className="px-4 sm:px-6 py-6 space-y-5">
        {step === 0 && (
          <>
            <Field label="Product Name" hint="e.g. XDeposit">
              <Input
                placeholder="Enter product name"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
              />
            </Field>
            <Field label="Product Description" hint='e.g. "A term deposit offering 1% higher returns than market rate"'>
              <Textarea
                rows={4}
                placeholder="Describe your product or service"
                value={productDescription}
                onChange={(e) => setProductDescription(e.target.value)}
              />
            </Field>
            <Field label="CTA Link" hint="e.g. https://superbfsi.com/xdeposit/explore/">
              <Input
                type="url"
                placeholder="https://example.com/landing"
                value={ctaLink}
                onChange={(e) => setCtaLink(e.target.value)}
              />
            </Field>
          </>
        )}

        {step === 1 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-sm font-medium text-foreground">Target Audience</Label>
                <p className="text-xs text-muted-foreground">
                  Add, edit or remove audience groups.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5 font-mono text-xs h-8"
                onClick={openAddGroup}
                disabled={groupFormOpen}
              >
                <Plus className="h-3.5 w-3.5" />
                Add Group
              </Button>
            </div>

            {/* Inline add/edit form */}
            {groupFormOpen && (
              <div className="rounded-md border border-primary/30 bg-primary/5 p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-primary/70">
                    {editingGroupKey !== null ? `Edit — ${editingGroupKey}` : "New Group"}
                  </p>
                  <button
                    type="button"
                    onClick={closeGroupForm}
                    className="h-5 w-5 rounded flex items-center justify-center text-muted-foreground/50 hover:text-foreground transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Group Name */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-medium">Group Name</Label>
                  <Input
                    className="h-8 text-sm"
                    placeholder="e.g. Group 1"
                    value={groupFormName}
                    onChange={(e) => setGroupFormName(e.target.value)}
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {/* Min Age */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Min Age</Label>
                    <Input
                      type="number"
                      className="h-8 text-sm"
                      placeholder="e.g. 25"
                      value={groupFormData.min_age ?? ""}
                      onChange={(e) => setGroupField("min_age", e.target.value)}
                    />
                  </div>
                  {/* Max Age */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Max Age</Label>
                    <Input
                      type="number"
                      className="h-8 text-sm"
                      placeholder="e.g. 45"
                      value={groupFormData.max_age ?? ""}
                      onChange={(e) => setGroupField("max_age", e.target.value)}
                    />
                  </div>
                  {/* Gender */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Gender</Label>
                    <Select
                      value={groupFormData.gender ?? ""}
                      onValueChange={(v) => setGroupField("gender", v === "Any" ? "" : v)}
                    >
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="Any" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Any">Any</SelectItem>
                        <SelectItem value="Male">Male</SelectItem>
                        <SelectItem value="Female">Female</SelectItem>
                        <SelectItem value="Other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {/* Min Income */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Min Monthly Income</Label>
                    <Input
                      type="number"
                      className="h-8 text-sm"
                      placeholder="e.g. 30000"
                      value={groupFormData.min_income ?? ""}
                      onChange={(e) => setGroupField("min_income", e.target.value)}
                    />
                  </div>
                  {/* Max Income */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Max Monthly Income</Label>
                    <Input
                      type="number"
                      className="h-8 text-sm"
                      placeholder="e.g. 100000"
                      value={groupFormData.max_income ?? ""}
                      onChange={(e) => setGroupField("max_income", e.target.value)}
                    />
                  </div>
                  {/* Credit Score */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Min Credit Score</Label>
                    <Input
                      type="number"
                      className="h-8 text-sm"
                      placeholder="e.g. 700"
                      value={groupFormData.Credit_score ?? ""}
                      onChange={(e) => setGroupField("Credit_score", e.target.value)}
                    />
                  </div>
                  {/* KYC Status */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">KYC Status</Label>
                    <Select
                      value={groupFormData.KYC_status ?? ""}
                      onValueChange={(v) => setGroupField("KYC_status", v === "Any" ? "" : v)}
                    >
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="Any" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Any">Any</SelectItem>
                        <SelectItem value="Y">Y — Verified</SelectItem>
                        <SelectItem value="N">N — Not verified</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {/* App Installed */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">App Installed</Label>
                    <Select
                      value={groupFormData.App_Installed ?? ""}
                      onValueChange={(v) => setGroupField("App_Installed", v === "Any" ? "" : v)}
                    >
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="Any" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Any">Any</SelectItem>
                        <SelectItem value="Y">Y — Installed</SelectItem>
                        <SelectItem value="N">N — Not installed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {/* Existing Customer */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Existing Customer</Label>
                    <Select
                      value={groupFormData.Existing_Customer ?? ""}
                      onValueChange={(v) => setGroupField("Existing_Customer", v === "Any" ? "" : v)}
                    >
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="Any" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Any">Any</SelectItem>
                        <SelectItem value="Y">Y — Existing</SelectItem>
                        <SelectItem value="N">N — New prospect</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {/* Social Media Active */}
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Social Media Active</Label>
                    <Select
                      value={groupFormData.Social_Media_Active ?? ""}
                      onValueChange={(v) => setGroupField("Social_Media_Active", v === "Any" ? "" : v)}
                    >
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="Any" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Any">Any</SelectItem>
                        <SelectItem value="Y">Y — Active</SelectItem>
                        <SelectItem value="N">N — Not active</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex gap-2 pt-1">
                  <Button type="button" size="sm" className="flex-1" onClick={saveGroup}>
                    {editingGroupKey !== null ? "Save Changes" : "Add Group"}
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={closeGroupForm}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {/* Group cards */}
            {Object.keys(audienceGroups).length === 0 && !groupFormOpen ? (
              <p className="text-sm text-muted-foreground italic">No audience groups yet. Click "Add Group" to create one.</p>
            ) : (
              Object.entries(audienceGroups).map(([name, group]) => (
                <AudienceGroupCard
                  key={name}
                  name={name}
                  group={group}
                  onEdit={() => openEditGroup(name)}
                  onDelete={() => deleteGroup(name)}
                />
              ))
            )}
          </div>
        )}

        {step === 2 && (
          <Field label="What's the objective?" hint='"Maximize click-throughs" or "Increase awareness" or "Drive sign-ups"'>
            <Textarea
              rows={4}
              placeholder="Describe your campaign goal"
              value={campaignGoal}
              onChange={(e) => setCampaignGoal(e.target.value)}
            />
          </Field>
        )}

        {step === 3 && (
          <>
            <Field label="Tone of email">
              <Select value={emailTone} onValueChange={setEmailTone}>
                <SelectTrigger>
                  <SelectValue placeholder="Select tone" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Formal">Formal</SelectItem>
                  <SelectItem value="Friendly">Friendly</SelectItem>
                  <SelectItem value="Urgent">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Campaign name" hint="Just a label for your reference">
              <Input
                placeholder="e.g. Q2 XDeposit Launch"
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
              />
            </Field>
            <Field label="Any content hints" hint='"Mention the limited time offer"'>
              <Textarea
                rows={3}
                placeholder="e.g. Mention the limited time offer"
                value={contentHints}
                onChange={(e) => setContentHints(e.target.value)}
              />
            </Field>
          </>
        )}
      </div>

      <div className="px-4 sm:px-6 py-4 border-t flex gap-3">
        <Button
          type="button"
          variant="outline"
          className="flex-1"
          onClick={() => {
            if (step === 0) setPhase("brief");
            else setStep((s) => s - 1);
          }}
        >
          Back
        </Button>
        <Button
          type="button"
          className="flex-1"
          disabled={!isCurrentStepValid()}
          onClick={() => {
            if (step < STEPS.length - 1) setStep((s) => s + 1);
            else setPhase("review");
          }}
        >
          Confirm
        </Button>
      </div>
    </form>
  );
};

export default CampaignForm;
