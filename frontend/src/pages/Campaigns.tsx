import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { Search, Plus, Megaphone, ArrowRight } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useCampaigns } from "@/context/CampaignsContext";
import { CampaignStatus } from "@/data/campaignsData";

const statusConfig: Record<CampaignStatus, { label: string; className: string }> = {
  draft: { label: "Draft", className: "bg-muted text-muted-foreground" },
  pending: { label: "Pending Approval", className: "bg-stat-amber/15 text-stat-amber" },
  active: { label: "Approved", className: "bg-primary/10 text-primary" },
  completed: { label: "Completed", className: "bg-stat-green/15 text-stat-green" },
  rejected: { label: "Rejected", className: "bg-destructive/10 text-destructive" },
};

const Campaigns = () => {
  const { campaigns } = useCampaigns();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = useMemo(() => {
    return campaigns.filter((c) => {
      if (search && !c.name.toLowerCase().includes(search.toLowerCase())) return false;
      if (statusFilter !== "all" && c.status !== statusFilter) return false;
      return true;
    });
  }, [campaigns, search, statusFilter]);

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
          <Link to="/" className="hover:text-foreground">Home</Link>
          <span>/</span>
          <span className="text-foreground">Campaigns</span>
        </div>

        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">All Campaigns</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Browse, search, and review every campaign in your workspace.
          </p>
        </div>

          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search campaigns..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 bg-card"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[200px] bg-card">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="pending">Pending Approval</SelectItem>
                <SelectItem value="active">Approved</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center border rounded-xl bg-card">
              <div className="p-4 rounded-full bg-muted mb-4">
                <Megaphone className="h-8 w-8 text-muted-foreground" />
              </div>
              <h2 className="text-lg font-medium text-foreground mb-1">No campaigns yet</h2>
              <p className="text-sm text-muted-foreground mb-4">Get started by creating your first campaign.</p>
              <Button asChild>
                <Link to="/campaigns/create">
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Campaign
                </Link>
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filtered.map((campaign) => {
                const status = statusConfig[campaign.status];
                return (
                  <Link key={campaign.id} to={`/campaigns/${campaign.id}`} className="group">
                    <Card className="h-full transition-all hover:shadow-soft hover:border-primary/30">
                      <CardContent className="p-5 flex flex-col h-full">
                        <div className="flex items-start justify-between mb-3 gap-2">
                          <h3 className="font-semibold text-foreground line-clamp-2 group-hover:text-primary transition-colors">
                            {campaign.name}
                          </h3>
                          <Badge className={cn("text-xs font-medium border-0 shrink-0", status.className)}>
                            {status.label}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2 mb-4">{campaign.brief}</p>
                        <div className="text-xs text-muted-foreground mb-4">Created {campaign.createdAt}</div>
                        <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground pt-3 border-t">
                          <span>
                            Open <span className="font-medium text-foreground">{campaign.metrics.openRate.toFixed(1)}%</span>
                          </span>
                          <span>
                            Click <span className="font-medium text-foreground">{campaign.metrics.clickRate.toFixed(1)}%</span>
                          </span>
                          <span className="flex items-center gap-1 text-primary font-medium">
                            View <ArrowRight className="h-3 w-3" />
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })}
            </div>
          )}
      </main>
    </div>
  );
};

export default Campaigns;
