'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Clock,
  Loader2,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { PIPELINE_STEPS } from '@/lib/campaignSteps';
import { useCampaignPolling } from '@/hooks/useCampaignPolling';

interface Props {
  campaignId: string;
  onFinished: () => void;
}

interface StatusConfig {
  Icon: React.ComponentType<{ className?: string }>;
  iconClass: string;
  title: string;
  subtitle: string;
}

const STATUS_CONFIG: Record<string, StatusConfig> = {
  running: {
    Icon: Loader2,
    iconClass: 'text-primary animate-spin',
    title: 'Running AI Pipeline',
    subtitle: 'Processing your campaign through the agent network…',
  },
  completed: {
    Icon: CheckCircle2,
    iconClass: 'text-stat-green',
    title: 'Campaign Ready',
    subtitle: 'All agents completed successfully.',
  },
  pending_approval: {
    Icon: Clock,
    iconClass: 'text-stat-amber',
    title: 'Awaiting Approval',
    subtitle: 'Campaign strategy is ready for your review.',
  },
  rejected: {
    Icon: XCircle,
    iconClass: 'text-destructive',
    title: 'Campaign Rejected',
    subtitle: 'This campaign was rejected during review.',
  },
  failed: {
    Icon: AlertCircle,
    iconClass: 'text-destructive',
    title: 'Pipeline Failed',
    subtitle: 'An unexpected error occurred in the pipeline.',
  },
};

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s.toString().padStart(2, '0')}s`;
}

type StepState = 'completed' | 'active' | 'pending';

export function CampaignProgressTracker({ campaignId, onFinished }: Props) {
  const router = useRouter();
  const {
    status,
    currentStep,
    isComplete,
    isLoading,
    completedSteps,
    elapsedSeconds,
    error,
  } = useCampaignPolling(campaignId);

  if (isLoading) {
    return (
      <div className="bg-card border border-border/60 rounded-lg overflow-hidden">
        <div className="h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
        <div className="px-5 py-4 border-b border-border/40 bg-secondary/20 flex items-center gap-3">
          <Skeleton className="h-8 w-8 rounded-md" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-36" />
            <Skeleton className="h-2.5 w-56" />
          </div>
        </div>
        <div className="px-5 py-3 border-b border-border/40">
          <Skeleton className="h-1.5 w-full rounded-full" />
        </div>
        <div className="px-5 py-4 space-y-1.5">
          {PIPELINE_STEPS.map((s) => (
            <Skeleton key={s.key} className="h-7 w-full rounded-md" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card border border-border/60 rounded-lg overflow-hidden">
        <div className="h-px bg-gradient-to-r from-transparent via-destructive/50 to-transparent" />
        <div className="px-5 py-8 flex flex-col items-center gap-3 text-center">
          <AlertCircle className="h-8 w-8 text-destructive" />
          <div>
            <p className="font-display font-semibold text-sm text-foreground">Connection Error</p>
            <p className="font-mono text-[11px] text-muted-foreground/60 mt-1">{error}</p>
          </div>
          <Button variant="outline" size="sm" onClick={onFinished}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const cfg: StatusConfig = STATUS_CONFIG[status] ?? STATUS_CONFIG.running;
  const progressValue = (completedSteps.length / PIPELINE_STEPS.length) * 100;

  const getStepState = (key: string): StepState => {
    if (completedSteps.includes(key)) return 'completed';
    if (key === currentStep) return 'active';
    return 'pending';
  };

  return (
    <div className="bg-card border border-border/60 rounded-lg overflow-hidden">
      {/* Top accent line */}
      <div className="h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />

      {/* Header */}
      <div className="px-5 py-4 border-b border-border/40 bg-secondary/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-md border border-border/40 bg-background flex items-center justify-center shrink-0">
              <cfg.Icon className={cn('h-4 w-4', cfg.iconClass)} />
            </div>
            <div>
              <p className="font-display font-semibold text-foreground text-sm">{cfg.title}</p>
              <p className="font-mono text-[10px] text-muted-foreground/60 mt-0.5">{cfg.subtitle}</p>
            </div>
          </div>
          <span className="font-mono text-[11px] text-muted-foreground/50 shrink-0 ml-4">
            {formatElapsed(elapsedSeconds)}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-5 py-3 border-b border-border/40">
        <div className="flex items-center justify-between mb-1.5">
          <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/40">
            Pipeline Progress
          </span>
          <span className="font-mono text-[10px] text-muted-foreground/60">
            {completedSteps.length} / {PIPELINE_STEPS.length}
          </span>
        </div>
        <Progress value={progressValue} className="h-1.5" />
      </div>

      {/* Step list */}
      <div className="px-5 py-4 space-y-0.5">
        {PIPELINE_STEPS.map((step) => {
          const state = getStepState(step.key);
          return (
            <div
              key={step.key}
              className={cn(
                'flex items-center gap-2.5 px-3 py-1.5 rounded-md transition-colors',
                state === 'active' && 'bg-primary/8 border border-primary/20',
                state === 'completed' && 'opacity-60',
              )}
            >
              {/* State indicator */}
              <div
                className={cn(
                  'h-4 w-4 rounded flex items-center justify-center shrink-0 border',
                  state === 'completed' && 'bg-stat-green/15 border-stat-green/30',
                  state === 'active' && 'bg-primary/10 border-primary/40',
                  state === 'pending' && 'bg-transparent border-border/40',
                )}
              >
                {state === 'completed' && (
                  <Check className="h-2.5 w-2.5 text-stat-green" />
                )}
                {state === 'active' && (
                  <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse block" />
                )}
              </div>

              {/* Label */}
              <span
                className={cn(
                  'font-mono text-[11px] flex-1',
                  state === 'active' && 'text-foreground font-medium',
                  state === 'completed' && 'text-muted-foreground/50',
                  state === 'pending' && 'text-muted-foreground/35',
                )}
              >
                {step.label}
              </span>

              {/* Active node spinner */}
              {state === 'active' && (
                <Loader2 className="h-3 w-3 text-primary/50 animate-spin" />
              )}
            </div>
          );
        })}
      </div>

      <Separator />

      {/* Action buttons */}
      <div className="px-5 py-4 flex gap-3">
        {isComplete ? (
          <>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={onFinished}
            >
              Create Another
            </Button>
            <Button
              size="sm"
              className="flex-1"
              onClick={() => router.push(`/campaigns/${campaignId}`)}
            >
              View Campaign
            </Button>
          </>
        ) : (
          <p className="font-mono text-[10px] text-muted-foreground/40 text-center w-full py-0.5">
            Processing — please keep this page open.
          </p>
        )}
      </div>
    </div>
  );
}
