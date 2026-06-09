'use client';

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Menu,
  Pencil, Inbox, Star, Clock, Send, FileText,
  ShoppingBag, ChevronDown, Plus,
  ArrowLeft, Archive, AlertOctagon, Trash2,
  Mail, AlarmClock, MoreVertical,
  Reply, Forward, Smile,
  ChevronLeft, ChevronRight, LayoutGrid,
} from "lucide-react";
import { getCampaignVariants, ApiVariant } from "@/lib/api";
import { fillPlaceholders } from "@/lib/emailUtils";

const LABELS = ["A", "B", "C", "D", "E", "F"];

function SidebarItem({
  icon,
  label,
  count,
  active,
}: {
  icon: React.ReactNode;
  label: string;
  count?: number;
  active?: boolean;
}) {
  return (
    <button
      className={`flex items-center gap-4 w-full pl-6 pr-3 py-[5px] rounded-r-full text-sm transition-colors select-none ${
        active
          ? "bg-gmail-active-bg font-bold text-foreground"
          : "hover:bg-gmail-hover/60 text-gmail-primary"
      }`}
    >
      <span className={active ? "text-gmail-active-icon" : "text-gmail-secondary"}>{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      {count != null && (
        <span className={`text-xs ${active ? "font-bold text-foreground" : "text-gmail-secondary"}`}>
          {count.toLocaleString()}
        </span>
      )}
    </button>
  );
}

export default function EmailVariantPage() {
  const params = useParams();
  const id = params.id as string;
  const variantId = params.variantId as string;
  const router = useRouter();

  const [allVariants, setAllVariants] = useState<ApiVariant[]>([]);
  const [variant, setVariant] = useState<ApiVariant | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    getCampaignVariants(id).then(({ variants }) => {
      setAllVariants(variants);
      setVariant(variants.find((v) => v.variant_id === variantId) ?? null);
      setIsLoading(false);
    });
  }, [id, variantId]);

  const currentIndex = allVariants.findIndex((v) => v.variant_id === variantId);
  const label = currentIndex >= 0 ? (LABELS[currentIndex] ?? String(currentIndex + 1)) : "—";
  const prevVariant = currentIndex > 0 ? allVariants[currentIndex - 1] : null;
  const nextVariant = currentIndex < allVariants.length - 1 ? allVariants[currentIndex + 1] : null;

  const sentDate = variant?.send_time
    ? new Date(variant.send_time).toLocaleString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      }) +
      " (" +
      (() => {
        const diff = Date.now() - new Date(variant.send_time).getTime();
        const h = Math.round(diff / 36e5);
        return h < 24 ? `${h} hour${h !== 1 ? "s" : ""} ago` : new Date(variant.send_time).toLocaleDateString();
      })() +
      ")"
    : "Scheduled";

  return (
    <div className="flex flex-col h-screen bg-gmail-bg font-gmail overflow-hidden">

      {/* ── Top header ──────────────────────────────────────────────────────── */}
      <header className="flex items-center gap-2 px-4 h-16 bg-gmail-bg shrink-0">
        {/* Left: hamburger + logo */}
        <div className="flex items-center gap-1 w-[256px] shrink-0">
          <button className="p-2.5 rounded-full hover:bg-black/8 text-gmail-secondary">
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-0.5 ml-1 cursor-pointer" onClick={() => router.push(`/campaigns/${id}`)}>
            <svg className="h-8 w-8" viewBox="0 0 48 48">
              <path fill="#4285F4" d="M45 16.2l-5 2.75-5 4.75V40h7a3 3 0 003-3V16.2z"/>
              <path fill="#34A853" d="M3 16.2l5 2.75 5 4.75V40H6a3 3 0 01-3-3V16.2z"/>
              <path fill="#EA4335" d="M35 11.2L24 19.75 13 11.2 12 8l12-5 12 5-1 3.2z"/>
              <path fill="#FBBC05" d="M3 12.298V16.2l10 7.5V11.2L9.885 8.984C8.249 8.116 6.197 8.698 5.2 10.26L3 12.298z"/>
              <path fill="#EA4335" d="M45 12.298V16.2l-10 7.5V11.2l3.115-2.216c1.636-.868 3.688-.286 4.685 1.276L45 12.298z"/>
            </svg>
            <span className="text-[22px] text-gmail-logo font-normal tracking-tight ml-0.5">Gmail</span>
          </div>
        </div>

        {/* Center: search bar */}
        <div className="flex-1 max-w-[720px] mx-auto">
          <div className="flex items-center bg-gmail-search-bg hover:shadow-[var(--gmail-search-shadow)] rounded-full px-4 h-12 gap-2 transition-shadow cursor-text">
            <svg className="h-5 w-5 text-gmail-secondary shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
            </svg>
            <input
              readOnly
              className="flex-1 bg-transparent text-gmail-primary text-base outline-none cursor-text"
              defaultValue={variant ? fillPlaceholders(variant.subject_line) : "Autonomail — Email Variant Preview"}
              placeholder="Search in mail"
            />
            <button className="p-1.5 rounded-full hover:bg-gmail-search-hover/50 shrink-0">
              <svg className="h-5 w-5 text-gmail-secondary" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Right: icons + avatar */}
        <div className="flex items-center gap-0.5 ml-auto">
          <button className="p-2.5 rounded-full hover:bg-gmail-hover/80">
            <svg className="h-5 w-5 text-gmail-secondary" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
            </svg>
          </button>
          <button className="p-2.5 rounded-full hover:bg-gmail-hover/80">
            <svg className="h-5 w-5 text-gmail-secondary" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.56-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
            </svg>
          </button>
          <button className="p-2.5 rounded-full hover:bg-gmail-hover/80">
            <svg className="h-5 w-5 text-gmail-secondary" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM6 14c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM6 20c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm6 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/>
            </svg>
          </button>
          <div className="w-8 h-8 rounded-full bg-gmail-blue flex items-center justify-center ml-1.5 cursor-pointer select-none">
            <span className="text-white text-sm font-medium">A</span>
          </div>
        </div>
      </header>

      {/* ── Body row (sidebar + content) ─────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">

        {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
        <aside className="w-[256px] shrink-0 overflow-y-auto py-2">
          <div className="px-3 mb-2">
            <button className="flex items-center gap-3 bg-gmail-compose-bg hover:bg-gmail-compose-hover text-gmail-compose-text rounded-2xl pl-4 pr-6 py-[18px] text-sm font-medium shadow-sm transition-colors w-full">
              <Pencil className="h-5 w-5" />
              <span>Compose</span>
            </button>
          </div>

          <div className="space-y-0.5 mt-1">
            <SidebarItem icon={<Inbox className="h-5 w-5" />} label="Inbox" count={2352} active />
            <SidebarItem icon={<Star className="h-5 w-5" />} label="Starred" />
            <SidebarItem icon={<Clock className="h-5 w-5" />} label="Snoozed" />
            <SidebarItem icon={<Send className="h-5 w-5" />} label="Sent" />
            <SidebarItem icon={<FileText className="h-5 w-5" />} label="Drafts" count={1} />
            <SidebarItem icon={<ShoppingBag className="h-5 w-5" />} label="Purchases" count={4} />
            <SidebarItem icon={<ChevronDown className="h-5 w-5" />} label="More" />
          </div>

          <div className="mt-4 px-6">
            <div className="flex items-center justify-between text-xs font-medium text-gmail-secondary py-1">
              <span>Labels</span>
              <button className="p-1 rounded-full hover:bg-gmail-hover/60">
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>
        </aside>

        {/* ── Main email area ──────────────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 overflow-y-auto bg-white rounded-tl-2xl mr-4 mb-4 shadow-sm">
          {isLoading ? (
            <div className="flex items-center justify-center py-32 text-sm text-gmail-secondary">Loading…</div>
          ) : !variant ? (
            <div className="flex flex-col items-center justify-center py-32 gap-3">
              <p className="text-sm text-gmail-secondary">Email variant not found.</p>
              <button
                onClick={() => router.push(`/campaigns/${id}`)}
                className="text-sm text-gmail-blue hover:underline"
              >
                Back to campaign
              </button>
            </div>
          ) : (
            <>
              {/* Gmail toolbar */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-gmail-border sticky top-0 bg-white z-10">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => router.push(`/campaigns/${id}`)}
                    className="p-2 rounded-full hover:bg-gmail-hover/60 text-gmail-secondary"
                    title="Back"
                  >
                    <ArrowLeft className="h-5 w-5" />
                  </button>
                  <button className="p-2 rounded-full hover:bg-gmail-hover/60 text-gmail-secondary" title="Archive">
                    <Archive className="h-5 w-5" />
                  </button>
                  <button className="p-2 rounded-full hover:bg-gmail-hover/60 text-gmail-secondary" title="Report spam">
                    <AlertOctagon className="h-5 w-5" />
                  </button>
                  <button className="p-2 rounded-full hover:bg-gmail-hover/60 text-gmail-secondary" title="Delete">
                    <Trash2 className="h-5 w-5" />
                  </button>
                  <button className="p-2 rounded-full hover:bg-gmail-hover/60 text-gmail-secondary" title="Mark as unread">
                    <Mail className="h-5 w-5" />
                  </button>
                  <button className="p-2 rounded-full hover:bg-gmail-hover/60 text-gmail-secondary" title="Snooze">
                    <AlarmClock className="h-5 w-5" />
                  </button>
                  <button className="p-2 rounded-full hover:bg-gmail-hover/60 text-gmail-secondary" title="More">
                    <MoreVertical className="h-5 w-5" />
                  </button>
                </div>

                {/* Variant pagination */}
                <div className="flex items-center gap-1 text-xs text-gmail-secondary">
                  <span>
                    {currentIndex + 1} of {allVariants.length}
                  </span>
                  <button
                    disabled={!prevVariant}
                    onClick={() => prevVariant && router.push(`/campaigns/${id}/${prevVariant.variant_id}`)}
                    className="p-2 rounded-full hover:bg-gmail-hover/60 disabled:opacity-30 disabled:cursor-default"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    disabled={!nextVariant}
                    onClick={() => nextVariant && router.push(`/campaigns/${id}/${nextVariant.variant_id}`)}
                    className="p-2 rounded-full hover:bg-gmail-hover/60 disabled:opacity-30 disabled:cursor-default"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                  <button className="p-2 rounded-full hover:bg-gmail-hover/60 ml-1">
                    <LayoutGrid className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Subject row */}
              <div className="flex items-center gap-3 px-6 pt-5 pb-3">
                <h1 className="text-[22px] font-normal text-gmail-primary flex-1 leading-snug">
                  {fillPlaceholders(variant.subject_line)}
                </h1>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="inline-flex items-center gap-1 rounded-sm bg-gmail-blue-light text-gmail-blue text-xs font-medium px-2 py-0.5">
                    Inbox
                    <button className="ml-0.5 hover:text-gmail-blue-dark">×</button>
                  </span>
                </div>
              </div>

              {/* Sender block */}
              <div className="flex items-start gap-3 px-6 pb-4">
                <div className="h-10 w-10 rounded-full bg-gmail-blue flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-white text-sm font-medium">CX</span>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-medium text-gmail-primary">Autonomail AI</span>
                        <svg className="h-4 w-4 text-gmail-blue" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/>
                        </svg>
                        <span className="text-xs text-gmail-secondary">&lt;ai@autonomail.engine&gt;</span>
                      </div>
                      <button className="flex items-center gap-0.5 text-xs text-gmail-secondary hover:text-gmail-primary mt-0.5">
                        to{" "}
                        <span className="font-medium text-gmail-primary ml-1">
                          {variant.segment_name.replace(/_/g, " ")}
                        </span>
                        <ChevronDown className="h-3 w-3 ml-0.5" />
                      </button>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-xs text-gmail-secondary">{sentDate}</span>
                      <button className="p-1.5 rounded-full hover:bg-gmail-hover/60">
                        <Star className="h-4 w-4 text-gmail-secondary" />
                      </button>
                      <button className="p-1.5 rounded-full hover:bg-gmail-hover/60">
                        <Reply className="h-4 w-4 text-gmail-secondary" />
                      </button>
                      <button className="p-1.5 rounded-full hover:bg-gmail-hover/60">
                        <MoreVertical className="h-4 w-4 text-gmail-secondary" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Email body */}
              <div
                className="px-16 py-4 pb-10 text-sm text-gmail-primary leading-relaxed"
                style={{ minHeight: 300 }}
                dangerouslySetInnerHTML={{ __html: fillPlaceholders(variant.email_body) }}
              />

              {/* Reply / Forward buttons */}
              <div className="px-16 pb-10 pt-2 flex gap-3">
                <button className="flex items-center gap-2 border border-gmail-reply-border hover:bg-gmail-bg text-gmail-secondary text-sm rounded-full px-5 py-2 transition-colors">
                  <Reply className="h-4 w-4" />
                  Reply
                </button>
                <button className="flex items-center gap-2 border border-gmail-reply-border hover:bg-gmail-bg text-gmail-secondary text-sm rounded-full px-5 py-2 transition-colors">
                  <Forward className="h-4 w-4" />
                  Forward
                </button>
                <button className="flex items-center gap-2 border border-gmail-reply-border hover:bg-gmail-bg text-gmail-secondary text-sm rounded-full px-5 py-2 transition-colors">
                  <Smile className="h-4 w-4" />
                </button>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
