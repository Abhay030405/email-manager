import { Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface SegmentCardProps {
  name: string;
  count: number;
  age: string;
  gender: string;
  location: string;
  description: string;
}

const SegmentCard = ({ name, count, age, gender, location, description }: SegmentCardProps) => (
  <div className="bg-card border rounded-lg p-4">
    <div className="flex items-start justify-between mb-2">
      <h3 className="text-sm font-semibold text-foreground">{name}</h3>
      <Badge variant="secondary" className="text-xs gap-1">
        <Users className="h-3 w-3" />
        {count.toLocaleString()}
      </Badge>
    </div>
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground mb-2">
      <span>Age: {age}</span>
      <span>Gender: {gender}</span>
      <span>Location: {location}</span>
    </div>
    <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
  </div>
);

export default SegmentCard;
