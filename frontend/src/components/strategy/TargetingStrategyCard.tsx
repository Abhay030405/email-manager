import { Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const TargetingStrategyCard = () => (
  <div className="bg-card border rounded-lg p-4">
    <div className="flex items-center gap-2 mb-3">
      <Target className="h-4 w-4 text-primary" />
      <h3 className="text-sm font-semibold text-foreground">Targeting Strategy</h3>
    </div>
    <p className="text-sm text-muted-foreground mb-3">
      Prioritize high-engagement segments first, then expand reach to broader audiences in phase two.
    </p>
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-foreground">Urban Professionals</span>
        <Badge variant="secondary" className="text-xs bg-primary/10 text-primary border-0">Primary</Badge>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-foreground">Young Trendsetters</span>
        <Badge variant="secondary" className="text-xs bg-primary/10 text-primary border-0">Primary</Badge>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-foreground">Value Seekers</span>
        <Badge variant="secondary" className="text-xs">Secondary</Badge>
      </div>
    </div>
  </div>
);

export default TargetingStrategyCard;
