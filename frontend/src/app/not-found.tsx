import Link from "next/link";
import { Bot, ArrowRight } from "lucide-react";

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background overflow-hidden">
      {/* Grid background */}
      <div className="absolute inset-0 bg-grid opacity-60" />
      {/* Glow orb */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] rounded-full bg-primary/5 blur-3xl pointer-events-none" />

      <div className="relative z-10 text-center px-4">
        <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-primary/80 bg-primary/8 border border-primary/15 px-2.5 py-1 rounded mb-8">
          <Bot className="h-3 w-3" />
          404 · Page Not Found
        </div>

        <h1 className="font-display font-bold gradient-text" style={{ fontSize: "clamp(6rem, 20vw, 12rem)", lineHeight: 1 }}>
          404
        </h1>

        <p className="mt-4 font-mono text-sm text-muted-foreground/70 max-w-sm mx-auto">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>

        <div className="mt-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-primary/10 border border-primary/25 text-sm font-mono text-primary hover:bg-primary/15 hover:border-primary/40 transition-colors"
          >
            <ArrowRight className="h-4 w-4 rotate-180" />
            Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
