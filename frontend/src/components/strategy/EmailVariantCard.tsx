import { Mail } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface EmailVariantCardProps {
  variant: string;
  subject: string;
  body: string;
  segment: string;
}

const EmailVariantCard = ({ variant, subject, body, segment }: EmailVariantCardProps) => (
  <div className="bg-card border rounded-lg overflow-hidden">
    <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/50">
      <div className="flex items-center gap-2">
        <Mail className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-semibold text-foreground">Variant {variant}</span>
      </div>
      <Badge variant="secondary" className="text-xs">{segment}</Badge>
    </div>
    <div className="p-4 space-y-2">
      <p className="text-sm font-medium text-foreground">{subject}</p>
      <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4">{body}</p>
    </div>
  </div>
);

export default EmailVariantCard;
