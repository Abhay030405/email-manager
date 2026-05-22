import { useState } from "react";
import { TrendingUp, TrendingDown, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import AppHeader from "@/components/AppHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent } from "@/components/ui/chart";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, BarChart, Bar, ResponsiveContainer } from "recharts";

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
  { name: "Working Parents", recipients: 8700, openRate: 51.4, clickRate: 18.7, conversions: 198 },
  { name: "Students", recipients: 15200, openRate: 45.8, clickRate: 14.3, conversions: 245 },
  { name: "Senior Executives", recipients: 4300, openRate: 62.1, clickRate: 25.4, conversions: 156 },
];

const variantData = [
  { name: "Open Rate", variantA: 54.2, variantB: 48.7 },
  { name: "Click Rate", variantA: 21.3, variantB: 17.8 },
  { name: "Conversions", variantA: 8.4, variantB: 6.1 },
];

const lineChartConfig = {
  openRate: { label: "Open Rate", color: "hsl(217, 91%, 60%)" },
  clickRate: { label: "Click Rate", color: "hsl(142, 71%, 45%)" },
};

const barChartConfig = {
  variantA: { label: "Variant A", color: "hsl(217, 91%, 60%)" },
  variantB: { label: "Variant B", color: "hsl(215, 16%, 47%)" },
};

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  positive: boolean;
}

const MetricCard = ({ title, value, change, positive }: MetricCardProps) => (
  <Card>
    <CardContent className="p-5">
      <p className="text-sm font-medium text-muted-foreground">{title}</p>
      <div className="flex items-end justify-between mt-2">
        <span className="text-3xl font-semibold text-foreground">{value}</span>
        <span className={`flex items-center gap-1 text-xs font-medium ${positive ? "text-stat-green" : "text-destructive"}`}>
          {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
          {change}
        </span>
      </div>
    </CardContent>
  </Card>
);

type SortKey = "name" | "recipients" | "openRate" | "clickRate" | "conversions";

const CampaignMetrics = () => {
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

  const sortIndicator = (key: SortKey) =>
    sortKey === key ? (sortAsc ? " ↑" : " ↓") : "";

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-10">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
            <Link to="/" className="hover:text-foreground">Home</Link>
            <span>/</span>
            <Link to="/campaigns" className="hover:text-foreground">Campaigns</Link>
            <span>/</span>
            <span className="text-foreground">Campaign Metrics</span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
            <h1 className="text-2xl font-semibold text-foreground">Campaign Metrics</h1>
            <Select defaultValue="summer">
              <SelectTrigger className="w-full sm:w-[220px]">
                <SelectValue placeholder="Select campaign" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="summer">Summer Sale 2025</SelectItem>
                <SelectItem value="product">Product Launch</SelectItem>
                <SelectItem value="retention">Retention Campaign</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <MetricCard title="Open Rate" value="54.2%" change="+3.1% vs last" positive />
            <MetricCard title="Click Rate" value="21.3%" change="+2.4% vs last" positive />
            <MetricCard title="Conversions" value="911" change="+12% vs last" positive />
            <MetricCard title="ROI" value="$4,280" change="-1.2% vs last" positive={false} />
          </div>

          {/* Performance Chart */}
          <Card className="mb-6">
            <CardHeader className="flex-row items-center justify-between pb-2">
              <CardTitle className="text-base font-medium">Performance Over Time</CardTitle>
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-[150px] h-8 text-xs">
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
                  <XAxis dataKey="date" className="text-xs" tick={{ fill: "hsl(215, 16%, 47%)" }} />
                  <YAxis className="text-xs" tick={{ fill: "hsl(215, 16%, 47%)" }} unit="%" />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <ChartLegend content={<ChartLegendContent />} />
                  <Line type="monotone" dataKey="openRate" stroke="var(--color-openRate)" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="clickRate" stroke="var(--color-clickRate)" strokeWidth={2} dot={false} />
                </LineChart>
              </ChartContainer>
            </CardContent>
          </Card>

          {/* Segment Performance Table */}
          <Card className="mb-6">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-medium">Segment Performance</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {([["name", "Segment Name"], ["recipients", "Recipients"], ["openRate", "Open Rate"], ["clickRate", "Click Rate"], ["conversions", "Conversions"]] as [SortKey, string][]).map(([key, label]) => (
                      <TableHead
                        key={key}
                        className="cursor-pointer select-none hover:text-foreground"
                        onClick={() => handleSort(key)}
                      >
                        {label}{sortIndicator(key)}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedSegments.map((seg, i) => (
                    <TableRow key={seg.name} className={i % 2 === 1 ? "bg-secondary/50" : ""}>
                      <TableCell className="font-medium">{seg.name}</TableCell>
                      <TableCell>{seg.recipients.toLocaleString()}</TableCell>
                      <TableCell>{seg.openRate}%</TableCell>
                      <TableCell>{seg.clickRate}%</TableCell>
                      <TableCell>{seg.conversions}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Variant Comparison */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-medium">Variant Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer config={barChartConfig} className="h-[280px] w-full">
                <BarChart data={variantData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="name" tick={{ fill: "hsl(215, 16%, 47%)" }} />
                  <YAxis tick={{ fill: "hsl(215, 16%, 47%)" }} unit="%" />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <ChartLegend content={<ChartLegendContent />} />
                  <Bar dataKey="variantA" fill="var(--color-variantA)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="variantB" fill="var(--color-variantB)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default CampaignMetrics;
