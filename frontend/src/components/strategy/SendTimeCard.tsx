import { useState } from "react";
import { format, parseISO } from "date-fns";
import { CalendarIcon, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Props {
  sendSchedule?: Record<string, string> | null;
}

const SendTimeCard = ({ sendSchedule }: Props) => {
  const [date, setDate] = useState<Date | undefined>(new Date());
  const [time, setTime] = useState("10:00");

  if (sendSchedule && Object.keys(sendSchedule).length > 0) {
    return (
      <div className="bg-card border rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Send Time Optimization</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-3">
          AI-optimized send times per segment for highest open rates.
        </p>
        <div className="space-y-2">
          {Object.entries(sendSchedule).map(([seg, iso]) => {
            let display = iso;
            try {
              display = format(parseISO(iso), "MMM d, h:mm a");
            } catch {
              // keep raw string
            }
            return (
              <div key={seg} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{seg.replace(/_/g, " ")}</span>
                <span className="text-foreground font-medium">{display}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Clock className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">Send Time Optimization</h3>
      </div>
      <p className="text-sm text-muted-foreground mb-3">
        AI recommends sending on weekday mornings for highest open rates.
      </p>
      <div className="space-y-3">
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn("w-full justify-start text-left font-normal text-sm", !date && "text-muted-foreground")}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {date ? format(date, "PPP") : "Pick a date"}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={date}
              onSelect={setDate}
              initialFocus
              className={cn("p-3 pointer-events-auto")}
            />
          </PopoverContent>
        </Popover>
        <Select value={time} onValueChange={setTime}>
          <SelectTrigger className="text-sm">
            <SelectValue placeholder="Select time" />
          </SelectTrigger>
          <SelectContent>
            {["08:00", "09:00", "10:00", "11:00", "12:00", "14:00", "16:00"].map((t) => (
              <SelectItem key={t} value={t}>{t} AM/PM</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
};

export default SendTimeCard;
