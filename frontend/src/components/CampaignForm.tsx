import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
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

const campaignSchema = z.object({
  campaignName: z.string().trim().min(1, "Campaign name is required").max(100),
  productName: z.string().trim().min(1, "Product name is required").max(100),
  productDescription: z.string().trim().min(1, "Product description is required").max(2000),
  targetDemographics: z.string().trim().min(1, "Target demographics is required").max(500),
  campaignGoal: z.string().min(1, "Campaign goal is required"),
  ctaLink: z.string().trim().url("Please enter a valid URL").max(2000),
  budget: z.string().min(1, "Budget is required").refine((v) => !isNaN(Number(v)) && Number(v) > 0, "Budget must be a positive number"),
  brief: z.string().trim().max(5000).optional(),
});

type FormData = z.infer<typeof campaignSchema>;
type FormErrors = Partial<Record<keyof FormData, string>>;

const goals = [
  "Brand Awareness",
  "Lead Generation",
  "Sales Conversion",
  "Customer Retention",
];

const CampaignForm = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormData>({
    campaignName: "",
    productName: "",
    productDescription: "",
    targetDemographics: "",
    campaignGoal: "",
    ctaLink: "",
    budget: "",
    brief: "",
  });
  const [errors, setErrors] = useState<FormErrors>({});

  const update = (field: keyof FormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const result = campaignSchema.safeParse(form);
    if (!result.success) {
      const fieldErrors: FormErrors = {};
      result.error.issues.forEach((issue) => {
        const key = issue.path[0] as keyof FormData;
        if (!fieldErrors[key]) fieldErrors[key] = issue.message;
      });
      setErrors(fieldErrors);
      return;
    }
    toast({ title: "Campaign strategy generated", description: "Your campaign has been created successfully." });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-card border rounded-lg">
      {/* Campaign Details */}
      <FormSection title="Campaign Details">
        <Field label="Campaign Name" error={errors.campaignName}>
          <Input
            placeholder="Enter campaign name"
            value={form.campaignName}
            onChange={(e) => update("campaignName", e.target.value)}
          />
        </Field>
        <Field label="Product / Service Name" error={errors.productName}>
          <Input
            placeholder="Enter product or service name"
            value={form.productName}
            onChange={(e) => update("productName", e.target.value)}
          />
        </Field>
        <Field label="Product Description" error={errors.productDescription}>
          <Textarea
            rows={4}
            placeholder="Describe your product or service"
            value={form.productDescription}
            onChange={(e) => update("productDescription", e.target.value)}
          />
        </Field>
      </FormSection>

      {/* Target Audience */}
      <FormSection title="Target Audience">
        <Field label="Target Demographics" error={errors.targetDemographics}>
          <Input
            placeholder="e.g., women aged 25-40 in urban areas"
            value={form.targetDemographics}
            onChange={(e) => update("targetDemographics", e.target.value)}
          />
        </Field>
        <Field label="Campaign Goal" error={errors.campaignGoal}>
          <Select value={form.campaignGoal} onValueChange={(v) => update("campaignGoal", v)}>
            <SelectTrigger>
              <SelectValue placeholder="Select a goal" />
            </SelectTrigger>
            <SelectContent>
              {goals.map((g) => (
                <SelectItem key={g} value={g}>{g}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      </FormSection>

      {/* Campaign Assets */}
      <FormSection title="Campaign Assets">
        <Field label="CTA Link" error={errors.ctaLink}>
          <Input
            type="url"
            placeholder="https://example.com/landing"
            value={form.ctaLink}
            onChange={(e) => update("ctaLink", e.target.value)}
          />
        </Field>
        <Field label="Budget" error={errors.budget}>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
            <Input
              type="number"
              min={0}
              className="pl-7"
              placeholder="0.00"
              value={form.budget}
              onChange={(e) => update("budget", e.target.value)}
            />
          </div>
        </Field>
      </FormSection>

      {/* Campaign Brief */}
      <FormSection title="Campaign Brief" last>
        <Field label="Campaign Brief" error={errors.brief}>
          <Textarea
            rows={8}
            placeholder="Describe your campaign objectives, tone, key messages..."
            value={form.brief}
            onChange={(e) => update("brief", e.target.value)}
          />
        </Field>
      </FormSection>

      {/* Actions */}
      <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-3 px-4 sm:px-6 py-4 border-t">
        <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={() => navigate("/")}>
          Cancel
        </Button>
        <Button type="submit" className="w-full sm:w-auto">Generate Campaign Strategy</Button>
      </div>
    </form>
  );
};

const FormSection = ({ title, children, last }: { title: string; children: React.ReactNode; last?: boolean }) => (
  <div className={`px-4 sm:px-6 py-5 ${last ? "" : "border-b"}`}>
    <h2 className="text-base font-semibold text-foreground mb-4">{title}</h2>
    <div className="space-y-4">{children}</div>
  </div>
);

const Field = ({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) => (
  <div className="space-y-1.5">
    <Label className="text-sm font-medium text-foreground">{label}</Label>
    {children}
    {error && <p className="text-xs text-destructive">{error}</p>}
  </div>
);

export default CampaignForm;
