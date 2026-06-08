'use client';

import { useState } from "react";
import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import Link from "next/link";
import AppHeader from "@/components/AppHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent } from "@/components/ui/chart";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, BarChart, Bar } from "recharts";
import { cn } from "@/lib/utils";

const performanceData = [
  { date: "Jan 1", openRate: 42, clickRate: 12 },
  { date: "Jan 3", openRate: 45, clickRate: 14 },
  { date: "Jan 5", openRate: 41, clickRate: 11 },
  { date: "Jan 7", openRate: 48, clickRate: 16 },
  { date: "Jan 9", openRate: 52, clickRate: 18 },
  { date: "Jan 11", openRate: 49, clickRate: 15 },
  { date: "Jan 13", openRate: 55, clickRate: 20 },
  { date: "Jan 15", openRate: 53, clickRate: 19 },
  { date: "Jan 17", openRate: 58, clickRate: 22 },
  { date: "Jan 19", openRate: 56, clickRate: 21 },
];

const segmentData = [
  { name: "Young Professionals", recipients: 12500, openRate: 58.2, clickRate: 22.1, conversions: 312 },
  { name: "Working Parents",      recipients: 8700,  openRate: 51.4, clickRate: 18.7, conversions: 198 },
  { name: "Students",             recipients: 15200, openRate: 45.8, clickRate: 14.3, conversions: 245 },
  { name: "Senior Executives",    recipients: 4300,  openRate: 62.1, clickRate: 25.4, conversions: 156 },
];

const variantData = [
  { name: "Open Rate",   variantA: 54.2, variantB: 48.7 },
  { name: "Click Rate",  variantA: 21.3, variantB: 17.8 },
  { name: "Conversions", variantA: 8.4,  variantB: 6.1  },
];

const lineChartConfig = {
  openRate:  { label: "Open Rate",  color: "hsl(var(--chart-color-1))" },
  clickRate: { label: "Click Rate", color: "hsl(var(--chart-color-2))" },
};

const barChartConfig = {
  variantA: { label: "Variant A", color: "hsl(var(--chart-color-1))" },
  variantB: { label: "Variant B", color: "hsl(var(--chart-color-3))" },
};

interface MetricCardProps { title: string; value: string; change: string; positive: boolean; }

const MetricCard = ({ title, value, change, positive }: MetricCardProps) => (
  <div className="bg-card p-5">
    <p className="font-mono text-[11px] text-muted-foreground uppercase tracking-widest">{title}</p>
    <div className="flex items-end justify-between mt-2">
      <span className="font-display text-3xl font-bold text-foreground">{value}</span>
      <span className={cn("flex items-center gap-1 font-mono text-[11px] font-medium", positive ? "text-stat-green" : "text-destructive")}>
        {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
        {change}
      </span>
    </div>
  </div>
);

type SortKey = "name" | "recipients" | "openRate" | "clickRate" | "conversions";

export default function CampaignMetrics() {
  const [timeRange, setTimeRange] = useState("7d");
  const [sortKey, setSortKey] = useState<SortKey>("openRate");
  const [sortAsc, setSortAsc] = useState(false);

  const sortedSegments = [...segmentData].sort((a, b) =>
    sortAsc ? (a[sortKey] > b[sortKey] ? 1 : -1) : (a[sortKey] < b[sortKey] ? 1 : -1)
  );

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const sortIndicator = (key: SortKey) => sortKey === key ? (sortAsc ? " ↑" : " ↓") : "";

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-10">

        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground/60 mb-6">
          <Link href="/" className="hover:text-foreground transition-colors">home</Link>
          <span className="text-border">/</span>
          <Link href="/campaigns" className="hover:text-foreground transition-colors">campaigns</Link>
          <span className="text-border">/</span>
          <span className="text-foreground/80">metrics</span>
        </nav>

        {/* Page header */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-primary/80 bg-primary/8 border border-primary/15 px-2.5 py-1 rounded mb-3">
              <BarChart3 className="h-3 w-3" />
              Analytics
            </div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              Campaign Metrics
            </h1>
          </div>
          <Select defaultValue="summer">
            <SelectTrigger className="w-full sm:w-[220px] bg-card border-border/60 font-mono text-sm h-9">
              <SelectValue placeholder="Select campaign" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="summer">Summer Sale 2025</SelectItem>
              <SelectItem value="product">Product Launch</SelectItem>
              <SelectItem value="retention">Retention Campaign</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* KPI grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border/40 rounded-lg overflow-hidden border border-border/40 mb-6">
          <MetricCard title="Open Rate"   value="54.2%" change="+3.1% vs last" positive />
          <MetricCard title="Click Rate"  value="21.3%" change="+2.4% vs last" positive />
          <MetricCard title="Conversions" value="911"   change="+12% vs last"  positive />
          <MetricCard title="ROI"         value="$4,280" change="-1.2% vs last" positive={false} />
        </div>

        {/* Performance chart */}
        <Card className="mb-6 bg-card border-border/60">
          <CardHeader className="flex-row items-center justify-between pb-2">
            <CardTitle className="font-display text-base font-semibold">Performance Over Time</CardTitle>
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-[140px] h-8 font-mono text-xs bg-card border-border/60">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="all">All time</SelectItem>
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent>
            <ChartContainer config={lineChartConfig} className="h-[300px] w-full">
              <LineChart data={performanceData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" className="text-xs" tick={{ fill: "hsl(var(--chart-axis))" }} />
                <YAxis className="text-xs" tick={{ fill: "hsl(var(--chart-axis))" }} unit="%" />
                <ChartTooltip content={<ChartTooltipContent />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Line type="monotone" dataKey="openRate"  stroke="var(--color-openRate)"  strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="clickRate" stroke="var(--color-clickRate)" strokeWidth={2} dot={false} />
              </LineChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Segment table */}
        <Card className="mb-6 bg-card border-border/60">
          <CardHeader className="pb-2">
            <CardTitle className="font-display text-base font-semibold">Segment Performance</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border/40">
                  {([
                    ["name", "Segment Name"], ["recipients", "Recipients"],
                    ["openRate", "Open Rate"], ["clickRate", "Click Rate"], ["conversions", "Conversions"],
                  ] as [SortKey, string][]).map(([key, label]) => (
                    <TableHead
                      key={key}
                      onClick={() => handleSort(key)}
                      className="cursor-pointer select-none hover:text-foreground font-mono text-[11px] uppercase tracking-wider"
                    >
                      {label}{sortIndicator(key)}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedSegments.map((seg, i) => (
                  <TableRow key={seg.name} className={cn("border-border/30", i % 2 === 1 && "bg-secondary/30")}>
                    <TableCell className="font-medium text-sm">{seg.name}</TableCell>
                    <TableCell className="font-mono text-sm">{seg.recipients.toLocaleString()}</TableCell>
                    <TableCell className="font-mono text-sm">{seg.openRate}%</TableCell>
                    <TableCell className="font-mono text-sm">{seg.clickRate}%</TableCell>
                    <TableCell className="font-mono text-sm">{seg.conversions}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Variant comparison chart */}
        <Card className="bg-card border-border/60">
          <CardHeader className="pb-2">
            <CardTitle className="font-display text-base font-semibold">Variant Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={barChartConfig} className="h-[280px] w-full">
              <BarChart data={variantData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="name" tick={{ fill: "hsl(var(--chart-axis))" }} />
                <YAxis tick={{ fill: "hsl(var(--chart-axis))" }} unit="%" />
                <ChartTooltip content={<ChartTooltipContent />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Bar dataKey="variantA" fill="var(--color-variantA)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="variantB" fill="var(--color-variantB)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

      </main>
    </div>
  );
}
