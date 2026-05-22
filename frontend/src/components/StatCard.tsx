import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string;
  change: string;
  changePositive: boolean;
  icon: LucideIcon;
  iconColorClass: string;
}

const StatCard = ({ title, value, change, changePositive, icon: Icon, iconColorClass }: StatCardProps) => {
  return (
    <div className="bg-card rounded-lg border p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        <div className={`p-2 rounded-md bg-accent ${iconColorClass}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="text-2xl font-semibold text-foreground">{value}</div>
      <p className={`text-xs mt-1 ${changePositive ? "text-stat-green" : "text-destructive"}`}>
        {change}
      </p>
    </div>
  );
};

export default StatCard;
