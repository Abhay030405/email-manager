import Link from "next/link";
import { Sparkles } from "lucide-react";
import CampaignForm from "@/components/CampaignForm";
import AppHeader from "@/components/AppHeader";

export default function CreateCampaign() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />
      <main className="max-w-screen-2xl mx-auto w-full px-4 sm:px-8 py-10">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground/60 mb-6">
          <Link href="/" className="hover:text-foreground transition-colors">home</Link>
          <span className="text-border">/</span>
          <Link href="/campaigns" className="hover:text-foreground transition-colors">campaigns</Link>
          <span className="text-border">/</span>
          <span className="text-foreground/80">create</span>
        </nav>

        {/* Page header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-primary/80 bg-primary/8 border border-primary/15 px-2.5 py-1 rounded mb-4">
            <Sparkles className="h-3 w-3" />
            AI-powered
          </div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Create New Campaign
          </h1>
          <p className="text-sm text-muted-foreground mt-2">
            Describe your product and goals. Four AI agents will build your campaign strategy in seconds.
          </p>
        </div>

        <CampaignForm />
      </main>
    </div>
  );
}
