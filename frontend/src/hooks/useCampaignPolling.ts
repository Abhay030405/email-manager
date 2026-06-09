'use client';

import { useEffect, useRef, useState } from 'react';
import { PIPELINE_STEPS } from '@/lib/campaignSteps';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';
const POLL_INTERVAL_MS = 4000;
const MAX_CONSECUTIVE_ERRORS = 3;

const TERMINAL_STATUSES = new Set(['completed', 'rejected', 'pending_approval', 'failed']);

interface StatusResponse {
  job_id: string;
  status: string;
  current_step: string | null;
  current_step_label: string | null;
  is_complete: boolean;
  updated_at: string;
}

export interface PollingState {
  status: string;
  currentStep: string | null;
  currentStepLabel: string | null;
  isComplete: boolean;
  isLoading: boolean;
  completedSteps: string[];
  elapsedSeconds: number;
  error: string | null;
}

export function useCampaignPolling(campaignId: string | null): PollingState {
  const [pollingState, setPollingState] = useState<Omit<PollingState, 'elapsedSeconds'>>({
    status: 'running',
    currentStep: null,
    currentStepLabel: null,
    isComplete: false,
    isLoading: true,
    completedSteps: [],
    error: null,
  });
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const shouldStopRef = useRef(false);
  const consecutiveErrorsRef = useRef(0);
  const startTimeRef = useRef<number | null>(null);

  // Main polling effect
  useEffect(() => {
    if (!campaignId) return;

    shouldStopRef.current = false;
    consecutiveErrorsRef.current = 0;
    startTimeRef.current = Date.now();
    setElapsedSeconds(0);
    setPollingState({
      status: 'running',
      currentStep: null,
      currentStepLabel: null,
      isComplete: false,
      isLoading: true,
      completedSteps: [],
      error: null,
    });

    const doPoll = async () => {
      if (shouldStopRef.current) return;
      try {
        const res = await fetch(`${API_BASE}/api/v1/campaigns/${campaignId}/status`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: StatusResponse = await res.json();

        consecutiveErrorsRef.current = 0;

        // Derive completed steps from backend state
        let completedSteps: string[] = [];
        if (data.status === 'completed') {
          completedSteps = PIPELINE_STEPS.map((s) => s.key);
        } else if (data.status === 'pending_approval') {
          const idx = PIPELINE_STEPS.findIndex((s) => s.key === 'approval');
          completedSteps = idx >= 0 ? PIPELINE_STEPS.slice(0, idx + 1).map((s) => s.key) : [];
        } else if (data.current_step) {
          const idx = PIPELINE_STEPS.findIndex((s) => s.key === data.current_step);
          completedSteps = idx > 0 ? PIPELINE_STEPS.slice(0, idx).map((s) => s.key) : [];
        }

        setPollingState({
          status: data.status,
          currentStep: data.current_step,
          currentStepLabel: data.current_step_label,
          isComplete: data.is_complete,
          isLoading: false,
          completedSteps,
          error: null,
        });

        if (data.is_complete || TERMINAL_STATUSES.has(data.status)) {
          shouldStopRef.current = true;
        }
      } catch {
        consecutiveErrorsRef.current += 1;
        if (consecutiveErrorsRef.current >= MAX_CONSECUTIVE_ERRORS) {
          shouldStopRef.current = true;
          setPollingState((prev) => ({
            ...prev,
            isLoading: false,
            error: 'Unable to reach the server. Please check your connection.',
          }));
        }
      }
    };

    doPoll();
    const pollInterval = setInterval(() => {
      if (shouldStopRef.current) {
        clearInterval(pollInterval);
        return;
      }
      doPoll();
    }, POLL_INTERVAL_MS);

    return () => {
      clearInterval(pollInterval);
      shouldStopRef.current = true;
    };
  }, [campaignId]);

  // Elapsed timer — ticks every second
  useEffect(() => {
    if (!campaignId) return;

    const timerInterval = setInterval(() => {
      if (startTimeRef.current !== null) {
        if (!shouldStopRef.current) {
          setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
        }
      }
    }, 1000);

    return () => clearInterval(timerInterval);
  }, [campaignId]);

  return { ...pollingState, elapsedSeconds };
}
