import { Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface Props {
  selectedSegments?: string[];
  reasoning?: Record<string, string>;
}

const TargetingStrategyCard = ({ selectedSegments, reasoning }: Props) => {
  const segments = selectedSegments ?? [];
  const primaryCount = Math.ceil(segments.length / 2);

  const summary =
    reasoning && Object.keys(reasoning).length > 0
      ? Object.values(reasoning)[0]
      : "Prioritize high-engagement segments first, then expand reach to broader audiences in phase two.";

  return (
    <div className="bg-card border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Target className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">Targeting Strategy</h3>
      </div>
      <p className="text-sm text-muted-foreground mb-3 line-clamp-3">{summary}</p>
      {segments.length > 0 && (
        <div className="space-y-2">
          {segments.map((seg, i) => (
            <div key={seg} className="flex items-center justify-between text-sm">
              <span className="text-foreground">{seg.replace(/_/g, " ")}</span>
              <Badge
                variant="secondary"
                className={i < primaryCount ? "text-xs bg-primary/10 text-primary border-0" : "text-xs"}
              >
                {i < primaryCount ? "Primary" : "Secondary"}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TargetingStrategyCard;
