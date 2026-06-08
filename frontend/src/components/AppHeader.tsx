'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "Home", to: "/" },
  { label: "Campaigns", to: "/campaigns" },
];

const agents = [
  { id: "SEG", label: "Segmentation" },
  { id: "STR", label: "Strategy" },
  { id: "EML", label: "Email" },
  { id: "APR", label: "Approval" },
];

const AppHeader = () => {
  const pathname = usePathname();

  const isActive = (to: string) => {
    if (to === "/") return pathname === "/";
    return pathname === to || pathname.startsWith(to + "/");
  };

  return (
    <header className="sticky top-0 z-40">
      <div
        className="relative h-[68px] backdrop-blur-3xl"
        style={{ backgroundColor: "hsl(222 30% 3% / 0.92)" }}
      >
        {/* Diagonal colour-wash: gold ← → blue */}
        <div className="absolute inset-0 bg-gradient-to-r from-primary/[0.07] via-transparent to-stat-blue/[0.04] pointer-events-none" />

        {/* Top accent line */}
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />

        <div className="relative h-full max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-4">

          {/* ── Logo ────────────────────────────────────────────────────── */}
          <Link href="/" className="flex items-center gap-3 group shrink-0">
            {/* Spinning-ring icon */}
            <div className="relative h-8 w-8">
              {/* Blur glow — expands on hover */}
              <div className="absolute inset-0 scale-150 rounded-lg bg-primary/0 group-hover:bg-primary/25 blur-[8px] transition-all duration-500 pointer-events-none" />
              {/* Rotating conic-gradient ring */}
              <div className="absolute inset-[-2px] rounded-[10px] logo-ring opacity-35 group-hover:opacity-75 transition-opacity duration-300" />
              {/* Icon container */}
              <div
                className="absolute inset-0 rounded-lg border border-primary/25 flex items-center justify-center z-10"
                style={{ backgroundColor: "hsl(222 30% 4%)" }}
              >
                <Bot className="h-3.5 w-3.5 text-primary" />
              </div>
            </div>

            <div className="leading-none">
              <div className="font-display font-bold text-[17px] text-foreground tracking-tight">
                NEXUS
              </div>
              <div className="font-mono text-[10px] text-primary/50 uppercase tracking-[0.18em] mt-[3px]">
                AUTONOMOUS CAMPAIGN ENGINE
              </div>
            </div>
          </Link>

          {/* ── Centre: per-agent live indicators (desktop only) ─────────── */}
          <div className="hidden lg:flex items-center gap-1 absolute left-1/2 -translate-x-1/2">
            {agents.map((agent, i) => (
              <div
                key={agent.id}
                title={agent.label}
                className="flex items-center gap-1.5 px-2 py-[5px] rounded border border-border/25 bg-secondary/20
                           hover:border-stat-green/25 hover:bg-stat-green/5 transition-colors cursor-default group/agent"
              >
                <span className="relative flex h-1.5 w-1.5 shrink-0">
                  <span
                    className="animate-ping absolute inline-flex h-full w-full rounded-full bg-stat-green opacity-50"
                    style={{ animationDelay: `${i * 0.35}s` }}
                  />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-stat-green/80" />
                </span>
                <span className="font-mono text-[11px] tracking-widest text-muted-foreground/70 group-hover/agent:text-stat-green/80 transition-colors">
                  {agent.id}
                </span>
              </div>
            ))}
          </div>

          {/* ── Right: nav + CTA ─────────────────────────────────────────── */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Nav links */}
            <nav className="hidden md:flex items-center">
              {navItems.map((item) => (
                <Link
                  key={item.to}
                  href={item.to}
                  className={cn(
                    "relative px-3 py-2 text-[14px] font-mono transition-colors",
                    isActive(item.to)
                      ? "text-foreground"
                      : "text-muted-foreground/70 hover:text-foreground/80"
                  )}
                >
                  {item.label.toLowerCase()}

                  {/* Glowing underline for active route */}
                  {isActive(item.to) && (
                    <span
                      className="absolute bottom-0 left-3 right-3 h-px bg-primary"
                      style={{
                        boxShadow:
                          "0 0 6px hsl(34 72% 52% / 0.9), 0 0 18px hsl(34 72% 52% / 0.45)",
                      }}
                    />
                  )}
                </Link>
              ))}
            </nav>

            {/* CTA — gradient border wrapper */}
            <div className="hidden sm:block relative group/cta">
              {/* Blurred glow behind button */}
              <div className="absolute inset-0 rounded-md bg-primary/0 group-hover/cta:bg-primary/20 blur-md transition-all duration-300 pointer-events-none" />
              {/* 1 px gradient border */}
              <div className="relative p-px rounded-md bg-gradient-to-r from-primary/70 via-primary/40 to-primary/20">
                <Link
                  href="/campaigns/create"
                  className="flex items-center gap-1.5 px-3 py-[6px] rounded-[5px] text-[13px] font-mono text-primary
                             hover:text-primary/80 transition-colors"
                  style={{ backgroundColor: "hsl(222 30% 5%)" }}
                >
                  <span aria-hidden>→</span>
                  <span>Launch</span>
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* ── Bottom: animated scan-line ──────────────────────────────────── */}
        <div className="absolute bottom-0 inset-x-0 h-px overflow-hidden">
          <div className="absolute inset-0 bg-border/20" />
          <div className="absolute h-full w-[22%] bg-gradient-to-r from-transparent via-primary/70 to-transparent animate-header-scan" />
        </div>
      </div>

      {/* ── Mobile nav ─────────────────────────────────────────────────────── */}
      <div
        className="md:hidden border-b border-border/20 backdrop-blur-xl"
        style={{ backgroundColor: "hsl(222 30% 3% / 0.95)" }}
      >
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between py-2">
          <div className="flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.to}
                href={item.to}
                className={cn(
                  "px-3 py-1 rounded text-[13px] font-mono transition-colors",
                  isActive(item.to)
                    ? "text-foreground bg-accent/40"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {item.label.toLowerCase()}
              </Link>
            ))}
          </div>

          {/* Mobile: compact status */}
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-stat-green opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-stat-green" />
            </span>
            <span className="font-mono text-[11px] text-muted-foreground/60 tracking-widest">4/4 LIVE</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default AppHeader;
