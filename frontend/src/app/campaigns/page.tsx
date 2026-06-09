'use client';

import { useState, useMemo } from "react";
import Link from "next/link";
import { Search, Plus, Megaphone, ArrowRight } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useCampaigns } from "@/context/CampaignsContext";
import { CampaignStatus } from "@/data/campaignsData";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

const statusConfig: Record<CampaignStatus, { label: string; className: string }> = {
  draft:     { label: "Draft",     className: "text-muted-foreground/70 border-border/50" },
  pending:   { label: "Pending",   className: "text-stat-amber border-stat-amber/30 bg-stat-amber/5" },
  active:    { label: "Approved",  className: "text-primary border-primary/30 bg-primary/5" },
  completed: { label: "Done",      className: "text-stat-green border-stat-green/30 bg-stat-green/5" },
  rejected:  { label: "Rejected",  className: "text-destructive border-destructive/30 bg-destructive/5" },
};

/** Strip raw formatting chars (====, ----, newlines) that leak from brief text. */
function cleanPreview(raw: string): string {
  return raw
    .replace(/={3,}/g, "")
    .replace(/-{3,}/g, "")
    .replace(/\*{2,}/g, "")
    .replace(/#+\s/g, "")
    .replace(/\n+/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim()
    .slice(0, 160);
}

export default function Campaigns() {
  const { campaigns, isLoading, error } = useCampaigns();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = useMemo(() => campaigns.filter((c) => {
    if (search) {
      const q = search.toLowerCase();
      if (!c.name.toLowerCase().includes(q) && !c.brief.toLowerCase().includes(q)) return false;
    }
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    return true;
  }), [campaigns, search, statusFilter]);

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      {/* ── Page header band ─────────────────────────────────────────────── */}
      <div className="relative border-b border-border/40 bg-[hsl(222,30%,3%)]">
        <div className="absolute inset-0 bg-grid opacity-40 pointer-events-none" />
        <div className="relative max-w-screen-2xl mx-auto px-4 sm:px-6 py-8">

          {/* Breadcrumb */}
          <nav className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground/50 mb-5">
            <Link href="/" className="hover:text-foreground/80 transition-colors">home</Link>
            <span className="text-border">/</span>
            <span className="text-foreground/70">campaigns</span>
          </nav>

          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
                All Campaigns
              </h1>
              <p className="font-mono text-[12px] text-muted-foreground/60 mt-1.5">
                {isLoading ? "Loading…" : `${campaigns.length} campaign${campaigns.length !== 1 ? "s" : ""} in workspace`}
              </p>
            </div>

            {/* CTA — matches header Launch button style */}
            <div className="relative group/cta shrink-0">
              <div className="absolute inset-0 rounded-md bg-primary/0 group-hover/cta:bg-primary/20 blur-md transition-all duration-300 pointer-events-none" />
              <div className="relative p-px rounded-md bg-gradient-to-r from-primary/70 via-primary/40 to-primary/20">
                <Link
                  href="/campaigns/create"
                  className="flex items-center gap-1.5 px-4 py-2 rounded-[5px] font-mono text-[13px] text-primary hover:text-primary/80 transition-colors"
                  style={{ backgroundColor: "hsl(222 30% 4%)" }}
                >
                  <Plus className="h-3.5 w-3.5" />
                  New Campaign
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-8">

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-2.5 mb-7">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50" />
            <Input
              placeholder="Search campaigns..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-[hsl(222,28%,5%)] border-border/50 font-mono text-[13px] h-9 placeholder:text-muted-foreground/40 focus-visible:border-primary/40"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-[160px] bg-[hsl(222,28%,5%)] border-border/50 font-mono text-[13px] h-9">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="active">Approved</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* ── States ──────────────────────────────────────────────────────── */}
        {isLoading ? (
          <div className="flex items-center justify-center py-28 border border-border/40 rounded-lg">
            <div className="text-center space-y-2">
              <div className="flex gap-1 justify-center">
                {["SEG", "STR", "EML", "APR"].map((a, i) => (
                  <span key={a} className="font-mono text-[9px] text-muted-foreground/40 bg-secondary border border-border/30 px-1.5 py-0.5 rounded animate-pulse" style={{ animationDelay: `${i * 0.15}s` }}>{a}</span>
                ))}
              </div>
              <p className="font-mono text-xs text-muted-foreground/50">Loading campaigns…</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-24 border border-destructive/20 rounded-lg text-center px-4">
            <p className="font-mono text-sm text-destructive">{error}</p>
            <p className="font-mono text-[11px] text-muted-foreground/50 mt-1">Backend at {API_URL}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-28 border border-border/40 rounded-lg text-center">
            <div className="h-10 w-10 rounded-lg bg-secondary border border-border/50 flex items-center justify-center mb-4">
              <Megaphone className="h-5 w-5 text-muted-foreground/40" />
            </div>
            <h2 className="font-display font-bold text-foreground mb-1">No campaigns yet</h2>
            <p className="font-mono text-[12px] text-muted-foreground/60 mb-6">Get started by creating your first campaign.</p>
            <div className="relative group/cta">
              <div className="absolute inset-0 rounded-md bg-primary/0 group-hover/cta:bg-primary/20 blur-md transition-all duration-300 pointer-events-none" />
              <div className="relative p-px rounded-md bg-gradient-to-r from-primary/70 via-primary/40 to-primary/20">
                <Link
                  href="/campaigns/create"
                  className="flex items-center gap-1.5 px-4 py-2 rounded-[5px] font-mono text-[13px] text-primary hover:text-primary/80 transition-colors"
                  style={{ backgroundColor: "hsl(222 30% 4%)" }}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Create first campaign
                </Link>
              </div>
            </div>
          </div>
        ) : (
          /* ── Campaign cards ── */
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filtered.map((campaign) => {
              const status = statusConfig[campaign.status];
              const preview = cleanPreview(campaign.productDescription || campaign.brief);

              return (
                <Link
                  key={campaign.id}
                  href={`/campaigns/${campaign.id}`}
                  className="group block"
                >
                  <div className="relative h-full border border-border/50 rounded-lg overflow-hidden transition-all duration-200 hover:border-primary/30 hover:shadow-[0_0_0_1px_hsl(34_72%_52%/0.12),0_4px_20px_-4px_hsl(0_0%_0%/0.5)]"
                       style={{ backgroundColor: "hsl(222 26% 6%)" }}>

                    {/* Amber left accent bar */}
                    <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-primary/20 group-hover:bg-primary/50 transition-colors duration-200" />

                    <div className="p-5 pl-5">
                      {/* Top row: name + status */}
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <h3 className="font-display font-semibold text-foreground/90 group-hover:text-primary transition-colors line-clamp-1 text-[15px] leading-snug">
                          {campaign.name}
                        </h3>
                        <span className={cn(
                          "shrink-0 font-mono text-[10px] border px-1.5 py-0.5 rounded leading-none mt-0.5",
                          status.className
                        )}>
                          {status.label}
                        </span>
                      </div>

                      {/* Description (cleaned) */}
                      <p className="font-mono text-[12px] text-muted-foreground/55 line-clamp-2 leading-relaxed mb-5">
                        {preview || <span className="italic">No description</span>}
                      </p>

                      {/* Footer */}
                      <div className="flex items-center justify-between pt-3 border-t border-border/30">
                        <div className="flex items-center gap-4">
                          <span className="font-mono text-[11px] text-muted-foreground/50">
                            open <span className="text-foreground/70 font-medium">{campaign.metrics.openRate.toFixed(1)}%</span>
                          </span>
                          <span className="font-mono text-[11px] text-muted-foreground/50">
                            click <span className="text-foreground/70 font-medium">{campaign.metrics.clickRate.toFixed(1)}%</span>
                          </span>
                        </div>
                        <ArrowRight className="h-3.5 w-3.5 text-primary/0 group-hover:text-primary/70 transition-colors duration-200" />
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
