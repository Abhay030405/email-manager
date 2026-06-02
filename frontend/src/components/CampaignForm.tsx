import { Fragment, useRef, useState } from "react";
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

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

interface AudienceGroup {
  min_age: number | null;
  max_age: number | null;
  Marital_Status: string | null;
  Family_Size: number | null;
  Dependent_count: number | null;
  Occupation: string | null;
  Occupation_type: string | null;
  Monthly_Income: number | null;
  KYC_status: string | null;
  City: string | null;
  Kids_in_Household: number | null;
  App_Installed: string | null;
  Existing_Customer: string | null;
  Credit_score: number | null;
  Social_Media_Active: string | null;
}

interface ParsedBriefSections {
  product_details: { product_name: string; product_description: string; cta_link: string };
  target_audience: Record<string, AudienceGroup>;
  campaign_goal: { objective: string };
  campaign_preferences: { email_tone: string; campaign_name: string; content_hints: string };
}

const GROUP_LABELS: Record<keyof AudienceGroup, string> = {
  min_age: "Min Age",
  max_age: "Max Age",
  Marital_Status: "Marital Status",
  Family_Size: "Family Size",
  Dependent_count: "Dependents",
  Occupation: "Occupation",
  Occupation_type: "Occupation Type",
  Monthly_Income: "Monthly Income",
  KYC_status: "KYC",
  City: "City",
  Kids_in_Household: "Kids",
  App_Installed: "App Installed",
  Existing_Customer: "Existing Customer",
  Credit_score: "Credit Score",
  Social_Media_Active: "Social Media Active",
};

const AudienceGroupCard = ({ name, group }: { name: string; group: AudienceGroup }) => {
  const fields = (Object.keys(GROUP_LABELS) as (keyof AudienceGroup)[]).filter(
    (k) => group[k] !== null && group[k] !== undefined
  );
  return (
    <div className="rounded-md border bg-muted/20 p-3 space-y-2">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{name}</p>
      {fields.length === 0 ? (
        <p className="text-xs text-muted-foreground italic">No specific criteria extracted</p>
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

const stepCircleClass = (i: number, currentStep: number) => {
  if (i < currentStep) return "bg-primary border-primary text-primary-foreground";
  if (i === currentStep) return "border-primary text-primary bg-background";
  return "border-muted text-muted-foreground bg-background";
};

const stepLabelClass = (i: number, currentStep: number) => {
  if (i === currentStep) return "text-primary font-medium";
  if (i < currentStep) return "text-foreground";
  return "text-muted-foreground";
};

const Stepper = ({ currentStep }: { currentStep: number }) => (
  <div className="px-4 sm:px-6 pt-6 pb-4 border-b">
    <div className="flex items-start">
      {STEPS.map((label, i) => (
        <Fragment key={label}>
          <div className="flex flex-col items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold border-2 shrink-0 ${stepCircleClass(i, currentStep)}`}
            >
              {i < currentStep ? "✓" : i + 1}
            </div>
            <span className={`mt-2 text-xs text-center leading-tight w-20 ${stepLabelClass(i, currentStep)}`}>
              {label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`flex-1 h-0.5 mt-4 mx-1 ${i < currentStep ? "bg-primary" : "bg-muted"}`} />
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
    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground border-b pb-1">{title}</h3>
    <div className="space-y-3">{children}</div>
  </div>
);

const CampaignForm = () => {
  const [phase, setPhase] = useState<"brief" | "wizard" | "review">("brief");
  const [step, setStep] = useState(0);
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

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

  // Step 2 — Campaign Goal
  const [campaignGoal, setCampaignGoal] = useState("");

  // Step 3 — Campaign Preferences (all optional)
  const [emailTone, setEmailTone] = useState("");
  const [campaignName, setCampaignName] = useState("");
  const [contentHints, setContentHints] = useState("");

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
      case 1: return Object.keys(audienceGroups).length > 0;
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

      // 2. Trigger AI workflow
      const workflowRes = await fetch(`${API_BASE}/api/v1/campaigns/${campaignId}/run-workflow`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!workflowRes.ok) {
        const err = await workflowRes.json().catch(() => ({}));
        throw new Error(err.detail ?? `Workflow failed (${workflowRes.status})`);
      }

      toast({ title: "Campaign created!", description: `Campaign ID: ${campaignId} — strategy is being generated.` });
      // Reset form back to brief phase
      setPhase("brief");
      setStep(0);
      setBrief("");
      setUploadedFileName(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      toast({ title: "Generation failed", description: message, variant: "destructive" });
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Phase 3: Review ──────────────────────────────────────────────────────
  if (phase === "review") {
    return (
      <div className="bg-card border rounded-lg">
        <div className="px-4 sm:px-6 py-5 border-b">
          <h2 className="text-base font-semibold text-foreground">Review Campaign Details</h2>
          <p className="text-xs text-muted-foreground mt-1">Check everything before generating the strategy.</p>
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
                <AudienceGroupCard key={name} name={name} group={group} />
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
  // ── Phase 1: Campaign Brief ──────────────────────────────────────────────
  if (phase === "brief") {
    return (
      <div className="bg-card border rounded-lg">
        <div className="px-4 sm:px-6 py-5 border-b">
          <h2 className="text-base font-semibold text-foreground mb-4">Campaign Brief</h2>
          <div className="space-y-4">
            <div className="rounded-md border border-muted/50 bg-muted/20 px-4 py-3 text-xs text-muted-foreground/70 space-y-3">
              <p className="font-medium text-muted-foreground">What a good Campaign Brief should include:</p>
              <ol className="list-decimal list-outside pl-4 space-y-2">
                <li>
                  <span className="font-medium text-muted-foreground/90">Product Details</span>
                  <ul className="list-disc list-outside pl-4 mt-1 space-y-0.5">
                    <li>Product Name — e.g. <span className="italic">XDeposit</span></li>
                    <li>Product Description — e.g. <span className="italic">"A term deposit offering 1% higher returns than market rate"</span></li>
                    <li>CTA Link — the link you want customers to click, e.g. <span className="italic">https://superbfsi.com/xdeposit/explore/</span></li>
                  </ul>
                </li>
                <li>
                  <span className="font-medium text-muted-foreground/90">Target Audience</span>
                  <ul className="list-disc list-outside pl-4 mt-1 space-y-0.5">
                    <li>Who to target — e.g. <span className="italic">"Working professionals aged 25–45"</span></li>
                    <li>Location preference — e.g. <span className="italic">"Metro cities"</span> or <span className="italic">"Delhi, Mumbai, Bangalore"</span></li>
                    <li>Any other filters — e.g. <span className="italic">"High income", "App installed users", "Existing customers only"</span></li>
                  </ul>
                </li>
                <li>
                  <span className="font-medium text-muted-foreground/90">Campaign Goal</span>
                  <ul className="list-disc list-outside pl-4 mt-1 space-y-0.5">
                    <li>What's the objective? — e.g. <span className="italic">"Maximize click-throughs"</span> or <span className="italic">"Increase awareness"</span> or <span className="italic">"Drive sign-ups"</span></li>
                  </ul>
                </li>
                <li>
                  <span className="font-medium text-muted-foreground/90">Campaign Preferences</span>{" "}
                  <span className="text-muted-foreground/50">(optional but helpful)</span>
                  <ul className="list-disc list-outside pl-4 mt-1 space-y-0.5">
                    <li>Tone of email — <span className="italic">Formal / Friendly / Urgent</span></li>
                    <li>Campaign name — just a label for your reference</li>
                    <li>Any content hints — e.g. <span className="italic">"Mention the limited time offer"</span></li>
                  </ul>
                </li>
              </ol>
            </div>

            <div className="space-y-1.5">
              <Label className="text-sm font-medium text-foreground">Campaign Brief</Label>
              <Textarea
                rows={8}
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
                  className="w-full rounded-md border border-dashed border-muted-foreground/40 px-4 py-3 text-sm text-muted-foreground hover:border-muted-foreground/70 hover:text-foreground transition-colors text-center"
                >
                  Upload the Campaign brief
                </button>
                <p className="text-xs text-muted-foreground text-center">*.txt files are only allowed</p>
              </div>
            )}
          </div>
        </div>

        <div className="px-4 sm:px-6 py-4">
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
    );
  }

  // ── Phase 2: Step wizard ─────────────────────────────────────────────────
  return (
    <form className="bg-card border rounded-lg">
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
            <div className="space-y-1.5">
              <Label className="text-sm font-medium text-foreground">Target Audience</Label>
              <p className="text-xs text-muted-foreground">
                Extracted from your campaign brief. Go back to edit the brief if adjustments are needed.
              </p>
            </div>
            {Object.keys(audienceGroups).length === 0 ? (
              <p className="text-sm text-muted-foreground italic">No audience groups extracted.</p>
            ) : (
              Object.entries(audienceGroups).map(([name, group]) => (
                <AudienceGroupCard key={name} name={name} group={group} />
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
