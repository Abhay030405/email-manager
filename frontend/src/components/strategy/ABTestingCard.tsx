import { FlaskConical } from "lucide-react";
import type { ApiABTestPlan } from "@/lib/api";

const DEFAULT_ITEMS = [
  { label: "Subject Line", description: "Test emotional vs. rational subject lines" },
  { label: "CTA Button", description: "Compare 'Shop Now' vs. 'Explore Collection'" },
  { label: "Send Time", description: "Morning (10 AM) vs. afternoon (2 PM) delivery" },
];

interface Props {
  abTestPlan?: ApiABTestPlan | null;
}

const ABTestingCard = ({ abTestPlan }: Props) => {
  const items =
    abTestPlan
      ? Array.from({ length: abTestPlan.num_variants }, (_, i) => {
          const pct = abTestPlan.variant_distribution[i] ?? 1 / abTestPlan.num_variants;
          return {
            label: `Variant ${String.fromCharCode(65 + i)}`,
            description: `${abTestPlan.test_dimension} — ${Math.round(pct * 100)}% of audience`,
          };
        })
      : DEFAULT_ITEMS;

  return (
    <div className="bg-card border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <FlaskConical className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">A/B Testing Plan</h3>
      </div>
      <ul className="space-y-3">
        {items.map((v) => (
          <li key={v.label} className="flex items-start gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
            <div>
              <p className="text-sm font-medium text-foreground">{v.label}</p>
              <p className="text-xs text-muted-foreground">{v.description}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ABTestingCard;
