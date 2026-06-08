import Link from "next/link";
import {
  ArrowRight,
  Bot,
  ChevronRight,
  Zap,
  Mail,
  Users,
  Target,
  Shield,
  Megaphone,
  BarChart3,
  MessageSquare,
  Database,
  Network,
  GitBranch,
  Brain,
  Eye,
  Globe,
  RefreshCw,
  Cpu,
  Layers,
  TrendingUp,
} from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Button } from "@/components/ui/button";

// ── Data ───────────────────────────────────────────────────────────────────
const stats = [
  { value: "8", label: "Specialized agents" },
  { value: "LangGraph", label: "Orchestration" },
  { value: "MongoDB", label: "State persistence" },
  { value: "FastAPI", label: "Backend" },
];

const agentLog = [
  { name: "brief-parser-agent",  status: "done",    output: "Product: Winter Collection · Goal: Sales Conversion · CTA extracted",               color: "text-stat-green",        bg: "bg-stat-green/10 text-stat-green",   icon: "✓" },
  { name: "segmentation-agent",  status: "done",    output: "RFM scored · k=4 clusters · silhouette=0.61 · 4 segments validated",                color: "text-stat-green",        bg: "bg-stat-green/10 text-stat-green",   icon: "✓" },
  { name: "strategy-agent",      status: "done",    output: "Quality gate passed · Send: Tue 10AM · Budget allocated",                            color: "text-stat-green",        bg: "bg-stat-green/10 text-stat-green",   icon: "✓" },
  { name: "content-gen-agent",   status: "running", output: "Parallel fan-out · 4 segments · spam score: 0.8 · CTR pred: 3.1%",                   color: "text-primary",           bg: "bg-primary/10 text-primary",         icon: "◉" },
  { name: "approval-agent",      status: "queued",  output: "interrupt() · awaiting human review",                                                color: "text-muted-foreground",  bg: "bg-muted text-muted-foreground",     icon: "○" },
  { name: "execution-agent",     status: "queued",  output: "Pending approval",                                                                    color: "text-muted-foreground",  bg: "bg-muted text-muted-foreground",     icon: "○" },
  { name: "monitoring-agent",    status: "queued",  output: "Event-driven · Redis Streams subscriber",                                             color: "text-muted-foreground",  bg: "bg-muted text-muted-foreground",     icon: "○" },
  { name: "optimization-agent",  status: "queued",  output: "Chi-square test · feature delta · memory retrieval",                                  color: "text-muted-foreground",  bg: "bg-muted text-muted-foreground",     icon: "○" },
];

const agents = [
  { id: "01", name: "Brief Parser",   color: "text-stat-blue",   border: "border-stat-blue/30",   bg: "bg-stat-blue/8",   icon: MessageSquare, tagline: "Extracts product, audience, goals and CTA from natural language. GPT-4 with schema validation." },
  { id: "02", name: "Segmentation",   color: "text-stat-purple", border: "border-stat-purple/30", bg: "bg-stat-purple/8", icon: Users,         tagline: "Real RFM scoring + sklearn KMeans on actual customer data. Validates segment sizes for A/B significance." },
  { id: "03", name: "Strategy",       color: "text-stat-amber",  border: "border-stat-amber/30",  bg: "bg-stat-amber/8",  icon: Target,        tagline: "Plans send timing, budget allocation, A/B test design. Routes back through the Quality Gate on failure." },
  { id: "04", name: "Quality Gate",   color: "text-stat-green",  border: "border-stat-green/30",  bg: "bg-stat-green/8",  icon: Shield,        tagline: "Pure deterministic checks — no LLM. Validates sizes, budget math, spacing. Routes to Strategy on failure." },
  { id: "05", name: "Content Gen",    color: "text-primary",     border: "border-primary/30",     bg: "bg-primary/8",     icon: Mail,          tagline: "Fan-out via LangGraph Send API. Parallel variants per segment, grounded in spam scores and CTR predictions." },
  { id: "06", name: "Approval",       color: "text-stat-blue",   border: "border-stat-blue/30",   bg: "bg-stat-blue/8",   icon: Megaphone,     tagline: "LangGraph interrupt() pauses the graph, serializes state to MongoDB, resumes from checkpoint on approval." },
  { id: "07", name: "Execution",      color: "text-stat-green",  border: "border-stat-green/30",  bg: "bg-stat-green/8",  icon: Zap,           tagline: "Interfaces with Campaign & Email APIs. Logs recipient counts, timestamps, and delivery status into shared state." },
  { id: "08", name: "Monitoring & Opt", color: "text-stat-purple", border: "border-stat-purple/30", bg: "bg-stat-purple/8", icon: BarChart3,   tagline: "Event-driven via Redis Streams. Chi-square significance tests before routing underperformers to Content Gen." },
];

const pipeline = [
  { id: "01", label: "Brief Parser",   type: "node",      color: "border-stat-blue/50 text-stat-blue",   bg: "bg-stat-blue/8" },
  { id: "02", label: "Segmentation",   type: "node",      color: "border-stat-purple/50 text-stat-purple", bg: "bg-stat-purple/8" },
  { id: "03", label: "Strategy",       type: "node",      color: "border-stat-amber/50 text-stat-amber",  bg: "bg-stat-amber/8" },
  { id: "04", label: "Quality Gate",   type: "gate",      color: "border-stat-green/50 text-stat-green",  bg: "bg-stat-green/8" },
  { id: "05", label: "Content Gen ×N", type: "parallel",  color: "border-primary/50 text-primary",        bg: "bg-primary/8" },
  { id: "06", label: "Approval ⏸",    type: "interrupt", color: "border-stat-amber/50 text-stat-amber",  bg: "bg-stat-amber/8" },
  { id: "07", label: "Execution",      type: "node",      color: "border-stat-green/50 text-stat-green",  bg: "bg-stat-green/8" },
  { id: "08", label: "Monitoring",     type: "node",      color: "border-stat-blue/50 text-stat-blue",    bg: "bg-stat-blue/8" },
  { id: "09", label: "Perf Gate",      type: "gate",      color: "border-stat-green/50 text-stat-green",  bg: "bg-stat-green/8" },
  { id: "10", label: "Optimization",   type: "node",      color: "border-stat-purple/50 text-stat-purple", bg: "bg-stat-purple/8" },
];

const capabilities = [
  {
    icon: Network,
    color: "text-stat-blue",
    bg: "bg-stat-blue/8",
    border: "border-stat-blue/20",
    title: "Parallel Fan-Out / Fan-In",
    subtitle: "LangGraph Send API",
    desc: "Instead of generating content for each segment sequentially, NEXUS uses LangGraph's Send API to fan out one Content Gen task per segment concurrently. Four segments in 15 seconds instead of 60. Architecturally correct — segments are independent.",
    lines: [
      { text: "Fan-out: Strategy → Send([seg-A, seg-B, seg-C, seg-D])", color: "text-stat-blue" },
      { text: "  ├─ seg-A: Content Gen ✓  spam: 0.8  CTR: 3.2%", color: "text-stat-green" },
      { text: "  ├─ seg-B: Content Gen ✓  spam: 1.1  CTR: 2.9%", color: "text-stat-green" },
      { text: "  ├─ seg-C: Content Gen ✓  spam: 0.6  CTR: 3.5%", color: "text-stat-green" },
      { text: "  └─ seg-D: Content Gen ✓  spam: 0.9  CTR: 3.1%", color: "text-stat-green" },
      { text: "Fan-in: merge_variants → Human Approval", color: "text-primary" },
    ],
  },
  {
    icon: Brain,
    color: "text-stat-purple",
    bg: "bg-stat-purple/8",
    border: "border-stat-purple/20",
    title: "Two-Layer Persistent Memory",
    subtitle: "MongoDB + pgvector",
    desc: "Run-level state is checkpointed to MongoDB after every node — the graph survives server restarts. Cross-campaign pgvector store captures what worked and why, queried by semantic similarity when new campaigns start.",
    lines: [
      { text: "# Layer 1 — run-level (MongoDB checkpoint)", color: "text-muted-foreground/50" },
      { text: "state.checkpoint(node='strategy', data={...})", color: "text-stat-blue" },
      { text: "# survives server restart at any point", color: "text-muted-foreground/50" },
      { text: "", color: "" },
      { text: "# Layer 2 — cross-campaign (pgvector)", color: "text-muted-foreground/50" },
      { text: "memory.query(brief, top_k=5)  # semantic similarity", color: "text-stat-purple" },
      { text: "# → learnings from 50 past campaigns", color: "text-muted-foreground/50" },
    ],
  },
  {
    icon: GitBranch,
    color: "text-stat-green",
    bg: "bg-stat-green/8",
    border: "border-stat-green/20",
    title: "Conditional Graph with Cycles",
    subtitle: "Quality Gate + interrupt()",
    desc: "Every edge has a condition. Quality Gate checks segment sizes, budget math, send-time spacing — all deterministic, no LLM. Failure routes back to Strategy (max 3 retries). Human rejection routes back to Content Gen with the feedback injected into state.",
    lines: [
      { text: "Quality Gate → Strategy  # fail: segment too small", color: "text-destructive/70" },
      { text: "Strategy → Quality Gate  # retry with merged seg", color: "text-stat-amber" },
      { text: "Quality Gate → Content Gen  # pass: all checks ✓", color: "text-stat-green" },
      { text: "", color: "" },
      { text: "Content Gen → interrupt()  # pause graph, save state", color: "text-stat-amber" },
      { text: "Human Approval → Execution   # approved", color: "text-stat-green" },
      { text: "Human Approval → Content Gen # rejected + feedback", color: "text-destructive/70" },
    ],
  },
  {
    icon: Eye,
    color: "text-stat-amber",
    bg: "bg-stat-amber/8",
    border: "border-stat-amber/20",
    title: "LangSmith Observability",
    subtitle: "Full pipeline tracing",
    desc: "Every node, every LLM call, every tool call traced with latencies and token counts. Detects prompt injection, measures per-tenant costs, and surfaces pipeline bottlenecks. Makes \"how do you know it's working?\" answerable with data.",
    lines: [
      { text: "run: campaign-47 · duration: 94s · $0.38", color: "text-stat-amber" },
      { text: "  ├─ segmentation-agent  12s  ✓ silhouette=0.61", color: "text-stat-green" },
      { text: "  ├─ strategy-agent      8s   ✓ quality gate pass", color: "text-stat-green" },
      { text: "  ├─ content-gen ×4     18s   ✓ parallel fan-out", color: "text-stat-green" },
      { text: "  ├─ approval            14h  ⏸ human pending", color: "text-stat-amber" },
      { text: "  └─ hallucination check  0 unverified claims", color: "text-stat-green" },
      { text: "cost breakdown: content-gen 61% · strategy 18%", color: "text-muted-foreground/40" },
    ],
  },
];

const phase2Features = [
  {
    icon: Globe,
    color: "text-stat-blue",
    bg: "bg-stat-blue/8",
    border: "border-stat-blue/20",
    title: "Multi-Tenancy + Federated Memory",
    desc: "Complete data isolation per tenant. Abstracted patterns — normalized metrics, structural content patterns, anonymized audience tier signals — are aggregated nightly into a shared knowledge base. New tenants benefit from platform-wide learnings without accessing any existing customer's data.",
  },
  {
    icon: RefreshCw,
    color: "text-stat-green",
    bg: "bg-stat-green/8",
    border: "border-stat-green/20",
    title: "Event-Driven Autonomous Monitoring",
    desc: "Continuous Redis Streams subscriber — not a polling job. Reacts to unsubscribe spikes, out-of-stock events, competitor campaign detections, and viral moments in real time. Each signal type has a response playbook with ordered actions by urgency and reversibility.",
  },
  {
    icon: Cpu,
    color: "text-primary",
    bg: "bg-primary/8",
    border: "border-primary/20",
    title: "Outcome-Based Fine-Tuning (CCIM)",
    desc: "Llama 3.1 8B fine-tuned with LoRA adapters on actual campaign open rates and CTRs — not human preference labels. Deployed after 20+ campaigns, versioned in MLflow. Training labels are real behavioral outcomes, not a human rater's opinion on what sounds good.",
  },
  {
    icon: Brain,
    color: "text-stat-purple",
    bg: "bg-stat-purple/8",
    border: "border-stat-purple/20",
    title: "Multi-Agent Debate Protocol",
    desc: "High-stakes campaigns (large budget, large audience, new category) route through a four-phase deliberation: Strategist proposes → Devil's Advocate critiques with evidence → Strategist revises → Risk Assessment Agent scores across brand safety, audience risk, financial risk, and compliance.",
  },
  {
    icon: MessageSquare,
    color: "text-stat-amber",
    bg: "bg-stat-amber/8",
    border: "border-stat-amber/20",
    title: "Natural Language Supervisor Agent",
    desc: "Top-level agent that accepts plain-language instructions and orchestrates any combination of agents, database operations, and scheduled tasks. Uses confidence thresholds for ambiguity resolution — proceeds autonomously above 0.85, asks one clarifying question below 0.60.",
  },
  {
    icon: TrendingUp,
    color: "text-stat-green",
    bg: "bg-stat-green/8",
    border: "border-stat-green/20",
    title: "AgentEval Framework",
    desc: "Continuously measures four dimensions: task completion rate, decision accuracy (predicted vs actual CTR), hallucination rate (unverified factual claims from memory), and cost efficiency per node. Generates weekly reports. Answers \"how do you know it's working?\" with data.",
  },
];

// ── Page ───────────────────────────────────────────────────────────────────
export default function Index() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />

      {/* ── HERO — full viewport, split layout ──────────────────────────── */}
      <section className="relative overflow-hidden" style={{ minHeight: "calc(100vh - 68px)" }}>
        {/* Background */}
        <div className="absolute inset-0 bg-grid opacity-50 pointer-events-none" />
        <div className="absolute -top-48 -left-48 w-[800px] h-[800px] rounded-full bg-primary/5 blur-3xl pointer-events-none" />
        <div className="absolute top-1/3 right-0 w-[500px] h-[700px] rounded-full bg-stat-blue/4 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 w-[400px] h-[400px] rounded-full bg-stat-purple/3 blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 h-full flex items-center py-16 lg:py-0" style={{ minHeight: "calc(100vh - 68px)" }}>
          <div className="w-full grid grid-cols-1 lg:grid-cols-[55%_45%] gap-12 lg:gap-8 items-center">

            {/* ── LEFT: Copy ── */}
            <div>
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-7 rounded-full border border-primary/20 bg-primary/5 text-primary font-mono tracking-wide" style={{ fontSize: "11px" }}>
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-dot" />
                8 AI Agents · LangGraph · FastAPI · MongoDB
                <ChevronRight className="h-3 w-3 opacity-60" />
              </div>

              {/* Headline */}
              <h1 className="font-display font-bold leading-[1.02] tracking-tight mb-6">
                <span className="block text-foreground" style={{ fontSize: "clamp(2.5rem, 5vw, 4.5rem)" }}>
                  Not a pipeline.
                </span>
                <span className="block gradient-text" style={{ fontSize: "clamp(2.5rem, 5vw, 4.5rem)" }}>
                  A graph of
                </span>
                <span className="block text-foreground" style={{ fontSize: "clamp(2.5rem, 5vw, 4.5rem)" }}>
                  autonomous agents.
                </span>
              </h1>

              {/* Subtitle */}
              <p className="text-base sm:text-lg text-muted-foreground leading-relaxed mb-8 max-w-lg">
                NEXUS deploys eight specialized agents equipped with real tools — RFM clustering, spam scoring, chi-square tests — that cycle on failure, run in parallel, and accumulate cross-campaign memory.
              </p>

              {/* CTAs */}
              <div className="flex flex-wrap items-center gap-3 mb-10">
                <Button asChild size="lg" className="bg-primary hover:bg-primary/90 text-white font-semibold h-11 px-6 rounded-md shadow-[0_0_20px_hsl(34_72%_52%/0.35)]">
                  <Link href="/campaigns/create">
                    Launch a campaign
                    <ArrowRight className="ml-1.5 h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg" className="border-border/60 hover:bg-accent/50 text-foreground h-11 px-6 rounded-md">
                  <Link href="/campaigns">View campaigns</Link>
                </Button>
              </div>

              {/* Stats — horizontal */}
              <div className="flex flex-wrap items-center gap-0">
                {stats.map((s, i) => (
                  <div key={s.label} className="flex items-center">
                    {i > 0 && <div className="w-px h-8 bg-border/40 mx-5" />}
                    <div>
                      <div className="font-display text-xl font-bold text-foreground">{s.value}</div>
                      <div className="font-mono text-muted-foreground" style={{ fontSize: "10px" }}>{s.label}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Author */}
              <p className="font-mono text-muted-foreground/40 mt-8" style={{ fontSize: "11px" }}>
                Built by <span className="text-primary/60">Abhay Agarwal</span> · MNNIT Allahabad · FrostHack
              </p>
            </div>

            {/* ── RIGHT: Terminal ── */}
            <div className="w-full">
              <div className="rounded-xl border border-border/60 overflow-hidden shadow-[0_0_0_1px_hsl(var(--border)/0.4),0_8px_40px_-8px_hsl(0_0%_0%/0.6)]" style={{ backgroundColor: "hsl(222 26% 5%)" }}>
                {/* Terminal header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border/40" style={{ backgroundColor: "hsl(222 26% 6%)" }}>
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
                  </div>
                  <span className="font-mono text-muted-foreground" style={{ fontSize: "11px" }}>campaign-graph · nexus</span>
                  <div className="w-16" />
                </div>

                {/* Terminal body */}
                <div className="p-5 space-y-3">
                  <p className="font-mono text-primary/50 mb-5" style={{ fontSize: "11px" }}>
                    <span className="text-muted-foreground/40">$ </span>
                    langgraph run --brief &quot;Winter sale · urban shoppers · ₹1500+ AOV&quot;
                  </p>
                  {agentLog.map((agent) => (
                    <div
                      key={agent.name}
                      className={`flex items-start gap-3 font-mono ${agent.status === "queued" ? "opacity-20" : ""}`}
                      style={{ fontSize: "12px" }}
                    >
                      <span className={`shrink-0 w-4 mt-0.5 ${agent.color} ${agent.status === "running" ? "animate-pulse" : ""}`}>
                        {agent.icon}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                          <span className="text-foreground/80 shrink-0">{agent.name}</span>
                          <span className={`shrink-0 px-1.5 py-px rounded font-mono ${agent.bg} ${agent.status === "running" ? "animate-pulse" : ""}`} style={{ fontSize: "10px" }}>
                            {agent.status}
                          </span>
                        </div>
                        <span className="text-muted-foreground/40 truncate block" style={{ fontSize: "11px" }}>{agent.output}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── PIPELINE — graph topology ────────────────────────────────────── */}
      <section className="py-20 lg:py-24 border-t border-border/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">

          <div className="max-w-2xl mb-12">
            <div className="inline-flex items-center gap-1.5 font-mono bg-primary/8 border border-primary/15 px-2.5 py-1 rounded mb-4 text-primary/80" style={{ fontSize: "11px" }}>
              <GitBranch className="h-3 w-3" />
              Conditional Graph Topology
            </div>
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-foreground tracking-tight">
              Every edge has a condition.<br />Every failure has a cycle.
            </h2>
            <p className="mt-3 text-sm text-muted-foreground max-w-lg leading-relaxed">
              LangGraph routes based on what agents compute — not a fixed sequence. The Quality Gate cycles back to Strategy on failure. Human rejection routes back to Content Gen with feedback injected into state.
            </p>
          </div>

          {/* Pipeline chips — horizontal scroll */}
          <div className="overflow-x-auto pb-3 mb-5">
            <div className="flex items-center gap-0 min-w-max">
              {pipeline.map((node, i) => (
                <div key={node.id} className="flex items-center">
                  <div className={`flex flex-col items-center gap-1 px-3 py-2 rounded-lg border ${node.color} ${node.bg} min-w-[90px]`}>
                    <span className="font-mono text-[9px] opacity-50">{node.id}</span>
                    <span className="font-mono text-[11px] font-medium text-center leading-tight whitespace-nowrap">{node.label}</span>
                    {node.type === "interrupt" && (
                      <span className="font-mono text-[9px] text-stat-amber/70">interrupt()</span>
                    )}
                    {node.type === "parallel" && (
                      <span className="font-mono text-[9px] text-primary/70">Send API ×N</span>
                    )}
                    {node.type === "gate" && (
                      <span className="font-mono text-[9px] text-stat-green/70">deterministic</span>
                    )}
                  </div>
                  {i < pipeline.length - 1 && (
                    <span className="text-muted-foreground/40 px-1.5 font-mono text-sm">→</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Cycle annotations */}
          <div className="flex flex-wrap gap-x-8 gap-y-2">
            {[
              { label: "↺  Quality Gate → Strategy", desc: "retry on failure (max 3)", color: "text-destructive/60" },
              { label: "↺  Approval → Content Gen",   desc: "rejected/edits with feedback injected", color: "text-stat-amber/60" },
              { label: "↺  Optimization → Content Gen", desc: "evidence-backed brief from memory", color: "text-stat-purple/60" },
            ].map((c) => (
              <div key={c.label} className="flex items-center gap-2 font-mono" style={{ fontSize: "11px" }}>
                <span className={c.color}>{c.label}</span>
                <span className="text-muted-foreground/40">·</span>
                <span className="text-muted-foreground/50">{c.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── AGENTS — compact roster ──────────────────────────────────────── */}
      <section className="py-20 lg:py-24 border-t border-border/40" style={{ backgroundColor: "hsl(222 28% 3.5%)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6">

          <div className="text-center max-w-2xl mx-auto mb-12">
            <div className="inline-flex items-center gap-1.5 font-mono bg-primary/8 border border-primary/15 px-2.5 py-1 rounded mb-4 text-primary/80" style={{ fontSize: "11px" }}>
              <Bot className="h-3 w-3" />
              Agent Roster
            </div>
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-foreground tracking-tight">
              Eight agents. Each with a real tool belt.
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Tools are deterministic Python functions — not LLM calls. The LLM decides which tool to invoke; Python executes it and returns real data.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className="group relative border border-border/50 rounded-lg p-5 transition-all duration-200 hover:border-border/80"
                style={{ backgroundColor: "hsl(222 26% 6%)" }}
              >
                {/* Colored left accent */}
                <div className={`absolute left-0 top-0 bottom-0 w-[2px] rounded-l-lg ${agent.bg} opacity-60 group-hover:opacity-100 transition-opacity`} />

                <div className="flex items-start justify-between mb-4">
                  <div className={`h-8 w-8 rounded-md ${agent.bg} border ${agent.border} flex items-center justify-center`}>
                    <agent.icon className={`h-4 w-4 ${agent.color}`} />
                  </div>
                  <span className={`font-mono ${agent.color} opacity-40 group-hover:opacity-70 transition-opacity`} style={{ fontSize: "11px" }}>{agent.id}</span>
                </div>

                <h3 className="font-display font-semibold text-foreground/90 mb-2" style={{ fontSize: "14px" }}>
                  {agent.name} Agent
                </h3>
                <p className="text-muted-foreground/60 leading-relaxed" style={{ fontSize: "12px" }}>
                  {agent.tagline}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CAPABILITIES — 3 key architecture highlights ─────────────────── */}
      <section className="py-20 lg:py-24 border-t border-border/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">

          <div className="max-w-2xl mb-16">
            <div className="inline-flex items-center gap-1.5 font-mono bg-primary/8 border border-primary/15 px-2.5 py-1 rounded mb-4 text-primary/80" style={{ fontSize: "11px" }}>
              Architecture Highlights
            </div>
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-foreground tracking-tight">
              What makes it genuinely agentic.
            </h2>
            <p className="mt-3 text-sm text-muted-foreground max-w-lg leading-relaxed">
              Three architectural patterns that separate NEXUS from a sequential LLM pipeline — implemented with real code, not described in a prompt.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {capabilities.map((cap) => (
              <div
                key={cap.title}
                className="group border border-border/50 rounded-lg overflow-hidden hover:border-border/80 transition-colors"
                style={{ backgroundColor: "hsl(222 26% 5.5%)" }}
              >
                {/* Card header */}
                <div className="px-5 pt-5 pb-4 border-b border-border/30">
                  <div className={`h-9 w-9 rounded-md ${cap.bg} border ${cap.border} flex items-center justify-center mb-4`}>
                    <cap.icon className={`h-4 w-4 ${cap.color}`} />
                  </div>
                  <div className={`font-mono mb-1 ${cap.color} opacity-60`} style={{ fontSize: "10px" }}>{cap.subtitle}</div>
                  <h3 className="font-display font-bold text-foreground mb-2" style={{ fontSize: "15px" }}>{cap.title}</h3>
                  <p className="text-muted-foreground/60 leading-relaxed" style={{ fontSize: "12px" }}>{cap.desc}</p>
                </div>

                {/* Code block */}
                <div className="px-5 py-4" style={{ backgroundColor: "hsl(222 28% 4%)" }}>
                  <div className="space-y-0.5">
                    {cap.lines.map((line, i) => (
                      <div key={i} className={`font-mono leading-relaxed ${line.color || "text-muted-foreground/30"}`} style={{ fontSize: "11px" }}>
                        {line.text || " "}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PHASE 2 — Platform Extensions ───────────────────────────────── */}
      <section className="py-20 lg:py-24 border-t border-border/40" style={{ backgroundColor: "hsl(222 28% 3.5%)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6">

          <div className="max-w-2xl mb-12">
            <div className="inline-flex items-center gap-1.5 font-mono bg-stat-purple/8 border border-stat-purple/15 px-2.5 py-1 rounded mb-4 text-stat-purple/80" style={{ fontSize: "11px" }}>
              <Layers className="h-3 w-3" />
              Phase 2 — Enterprise Platform
            </div>
            <h2 className="font-display text-2xl lg:text-3xl font-bold text-foreground tracking-tight">
              Six additions that make it a platform.
            </h2>
            <p className="mt-3 text-sm text-muted-foreground max-w-lg leading-relaxed">
              Multi-tenancy, federated learning, fine-tuned models, adversarial debate, autonomous monitoring — problems that only exist at scale. Each one a genuine architectural addition, not a feature flag.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {phase2Features.map((f) => (
              <div
                key={f.title}
                className="group border border-border/50 rounded-lg p-5 hover:border-border/80 transition-colors"
                style={{ backgroundColor: "hsl(222 26% 6%)" }}
              >
                <div className={`h-9 w-9 rounded-md ${f.bg} border ${f.border} flex items-center justify-center mb-4 group-hover:opacity-80 transition-opacity`}>
                  <f.icon className={`h-4 w-4 ${f.color}`} />
                </div>
                <h3 className="font-display font-semibold text-foreground mb-2" style={{ fontSize: "14px" }}>
                  {f.title}
                </h3>
                <p className="text-muted-foreground/60 leading-relaxed" style={{ fontSize: "12px" }}>
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="py-24 border-t border-border/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="relative rounded-xl border border-border/50 overflow-hidden" style={{ backgroundColor: "hsl(222 28% 4%)" }}>
            <div className="absolute inset-0 bg-grid opacity-50 pointer-events-none" />
            <div className="absolute -bottom-20 -right-20 w-64 h-64 rounded-full bg-primary/8 blur-3xl pointer-events-none" />

            <div className="relative z-10 p-10 sm:p-16">
              <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-10 items-center">
                <div>
                  <div className="inline-flex items-center gap-1.5 font-mono bg-stat-green/8 border border-stat-green/20 px-2.5 py-1 rounded mb-5 text-stat-green/80" style={{ fontSize: "11px" }}>
                    <span className="w-1 h-1 rounded-full bg-stat-green animate-pulse-dot" />
                    System is live
                  </div>
                  <h2 className="font-display text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground tracking-tight mb-4">
                    Submit a brief.<br />
                    <span className="gradient-text">Watch eight agents work.</span>
                  </h2>
                  <p className="text-sm text-muted-foreground max-w-lg leading-relaxed mb-6">
                    The full pipeline — RFM clustering, quality gates, parallel content generation, human approval, statistical optimization — runs end to end from a plain-language brief.
                  </p>
                  <div className="flex flex-wrap gap-x-8 gap-y-2">
                    {[
                      "Real sklearn clustering — not GPT guessing segments",
                      "Conditional graph with cycles and retry loops",
                      "LangGraph interrupt() for stateful human approval",
                      "Chi-square significance tests before any optimization",
                    ].map((item) => (
                      <div key={item} className="flex items-center gap-2 font-mono text-muted-foreground/60" style={{ fontSize: "11px" }}>
                        <span className="text-stat-green">✓</span>
                        {item}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col items-start lg:items-end gap-3">
                  <Button asChild size="lg" className="bg-primary hover:bg-primary/90 text-white font-semibold h-11 px-8 rounded-md shadow-[0_0_20px_hsl(34_72%_52%/0.35)] w-full lg:w-auto">
                    <Link href="/campaigns/create">
                      Start a campaign
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                  <Button asChild variant="outline" size="lg" className="border-border/60 hover:bg-accent/50 h-11 px-8 rounded-md w-full lg:w-auto">
                    <Link href="/campaigns">Browse campaigns</Link>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-border/40 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Bot className="h-3.5 w-3.5 text-primary/60" />
            <span className="font-display text-sm font-semibold text-foreground/70">NEXUS</span>
            <span className="font-mono text-xs text-muted-foreground">
              · Abhay Agarwal · MNNIT Allahabad · © {new Date().getFullYear()}
            </span>
          </div>
          <div className="flex items-center gap-5 text-xs text-muted-foreground font-mono">
            <Link href="/" className="hover:text-foreground transition-colors">home</Link>
            <Link href="/campaigns" className="hover:text-foreground transition-colors">campaigns</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
