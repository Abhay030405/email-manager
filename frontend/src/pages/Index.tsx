import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Sparkles, Star, Zap } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { productHighlights, flowSteps } from "@/data/campaignsData";

const stats = [
  { value: "128+", label: "Campaigns launched" },
  { value: "42.8%", label: "Avg open rate" },
  { value: "6.3%", label: "Avg click rate" },
  { value: "24/7", label: "Always-on AI" },
];

const testimonials = [
  {
    quote:
      "CampaignX cut our briefing-to-launch time from a week to an afternoon. The AI-generated segments are uncannily accurate.",
    author: "Priya Shah",
    role: "Head of Growth, NorthBeam",
  },
  {
    quote:
      "The approval workflow alone saved us countless meetings. Side-by-side variants make decisions effortless.",
    author: "Daniel Reyes",
    role: "VP Marketing, Vellum Co.",
  },
  {
    quote:
      "Finally, a marketing tool that feels as polished as the campaigns we ship. Our team adopted it in a single week.",
    author: "Aisha Bello",
    role: "CMO, Lumen Studio",
  },
];

const Index = () => {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <AppHeader />

      {/* Hero */}
      <section className="relative bg-hero overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-14 pb-16 sm:pt-20 sm:pb-24 lg:pt-28 lg:pb-32">
          <div className="max-w-3xl mx-auto text-center">
            <Badge variant="secondary" className="mb-5 bg-primary/10 text-primary border-0 gap-1.5">
              <Sparkles className="h-3 w-3" />
              AI-powered marketing platform
            </Badge>
            <h1 className="text-[2rem] sm:text-5xl lg:text-6xl font-semibold text-foreground tracking-tight text-balance leading-[1.1] sm:leading-[1.05]">
              Launch beautiful campaigns,{" "}
              <span className="text-primary">in a single afternoon.</span>
            </h1>
            <p className="mt-5 sm:mt-6 text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto text-balance">
              CampaignX turns a one-paragraph brief into segmented audiences, ready-to-send email
              variants, and a built-in approval flow — all wrapped in a beautiful, professional
              experience your team will love using.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Button asChild size="lg" className="shadow-glow">
                <Link to="/campaigns/create">
                  Create your first campaign
                  <ArrowRight className="ml-1.5 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/campaigns">Browse campaigns</Link>
              </Button>
            </div>

            <div className="mt-10 flex items-center justify-center gap-1 text-xs text-muted-foreground">
              <Star className="h-3.5 w-3.5 fill-stat-amber text-stat-amber" />
              <Star className="h-3.5 w-3.5 fill-stat-amber text-stat-amber" />
              <Star className="h-3.5 w-3.5 fill-stat-amber text-stat-amber" />
              <Star className="h-3.5 w-3.5 fill-stat-amber text-stat-amber" />
              <Star className="h-3.5 w-3.5 fill-stat-amber text-stat-amber" />
              <span className="ml-2">Rated 4.9 / 5 by 200+ marketing teams</span>
            </div>
          </div>

          {/* Hero preview card */}
          <div className="mt-12 sm:mt-16 max-w-5xl mx-auto">
            <div className="rounded-2xl border bg-card shadow-soft p-2 sm:p-3">
              <div className="rounded-xl bg-gradient-to-br from-secondary to-card border p-5 sm:p-10">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
                  {stats.map((s) => (
                    <div key={s.label} className="text-center md:text-left">
                      <div className="text-2xl sm:text-3xl font-semibold text-foreground">{s.value}</div>
                      <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="max-w-2xl mb-12">
            <Badge variant="secondary" className="mb-3">Features</Badge>
            <h2 className="text-3xl lg:text-4xl font-semibold text-foreground tracking-tight">
              Everything you need to ship better campaigns.
            </h2>
            <p className="mt-3 text-muted-foreground">
              From the first idea to the final metric, CampaignX gives your team a single, polished
              workspace built around modern marketing workflows.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {productHighlights.map((f) => (
              <div
                key={f.title}
                className="group rounded-xl border bg-card p-6 hover:shadow-soft transition-shadow"
              >
                <div className="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  <f.icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold text-foreground mb-1.5">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 lg:py-24 bg-secondary/40 border-y">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <Badge variant="secondary" className="mb-3">How it works</Badge>
            <h2 className="text-3xl lg:text-4xl font-semibold text-foreground tracking-tight">
              From brief to live campaign in four steps.
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {flowSteps.map((s) => (
              <div key={s.step} className="rounded-xl bg-card border p-6 relative">
                <div className="text-xs font-mono text-primary mb-3">{s.step}</div>
                <h3 className="font-semibold text-foreground mb-1.5">{s.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <Badge variant="secondary" className="mb-3">Loved by teams</Badge>
            <h2 className="text-3xl lg:text-4xl font-semibold text-foreground tracking-tight">
              Trusted by modern marketing teams.
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {testimonials.map((t) => (
              <figure key={t.author} className="rounded-xl border bg-card p-6">
                <div className="flex gap-0.5 mb-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star key={i} className="h-3.5 w-3.5 fill-stat-amber text-stat-amber" />
                  ))}
                </div>
                <blockquote className="text-sm text-foreground leading-relaxed">"{t.quote}"</blockquote>
                <figcaption className="mt-4 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">{t.author}</span> · {t.role}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="rounded-2xl bg-primary text-primary-foreground p-6 sm:p-10 lg:p-14 shadow-glow">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
              <div className="lg:col-span-2">
                <h2 className="text-2xl sm:text-3xl lg:text-4xl font-semibold tracking-tight text-balance">
                  Ready to ship your next campaign?
                </h2>
                <p className="mt-3 text-primary-foreground/80 max-w-xl">
                  Start free — no credit card required. See how CampaignX transforms your workflow
                  in minutes.
                </p>
                <ul className="mt-5 space-y-1.5 text-sm text-primary-foreground/90">
                  {["AI-generated segments and variants", "Built-in approval workflow", "Beautiful, real-time metrics"].map((i) => (
                    <li key={i} className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4" /> {i}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex lg:justify-end">
                <Button asChild size="lg" variant="secondary" className="text-foreground">
                  <Link to="/campaigns/create">
                    Get started free
                    <ArrowRight className="ml-1.5 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            <span className="font-medium text-foreground">CampaignX</span>
            <span>· © {new Date().getFullYear()}</span>
          </div>
          <div className="flex items-center gap-5">
            <Link to="/" className="hover:text-foreground">Home</Link>
            <Link to="/campaigns" className="hover:text-foreground">Campaigns</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
