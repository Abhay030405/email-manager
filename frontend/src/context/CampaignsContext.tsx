import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from "react";
import { Campaign, CampaignStatus } from "@/data/campaignsData";
import { ApiCampaign, listCampaigns, patchCampaignStatus } from "@/lib/api";

// ── Status mapping: backend → frontend ────────────────────────────────────

const STATUS_MAP: Record<string, CampaignStatus> = {
  draft: "draft",
  pending_approval: "pending",
  approved: "active",
  executing: "active",
  optimizing: "active",
  completed: "completed",
  rejected: "rejected",
};

// Reverse mapping for PATCH calls
const STATUS_REVERSE: Record<CampaignStatus, string> = {
  draft: "draft",
  pending: "pending_approval",
  active: "approved",
  completed: "completed",
  rejected: "rejected",
};

// ── Helpers ────────────────────────────────────────────────────────────────

function splitTags(raw: string): string[] {
  // Split on ", " or "; " — not bare "," so commas inside numbers (₹35,000) are preserved
  return raw
    .split(/,\s+|;\s*/)
    .map((t) => t.trim())
    .filter(Boolean);
}

function buildContentHints(pd: Partial<ApiCampaign["parsed_data"]>): string[] {
  const hints: string[] = [...(pd.key_messages ?? [])];
  if (pd.constraints?.trim()) hints.push(...splitTags(pd.constraints));
  return hints.filter(Boolean);
}

function buildAudienceTags(pd: Partial<ApiCampaign["parsed_data"]>): string[] {
  const tags: string[] = [];
  if (pd.audience_who) tags.push(pd.audience_who.trim());
  if (pd.audience_location) tags.push(...splitTags(pd.audience_location));
  if (pd.audience_filters) tags.push(...splitTags(pd.audience_filters));
  return tags;
}

// ── Adapter ────────────────────────────────────────────────────────────────

function adaptCampaign(api: ApiCampaign): Campaign {
  const pd = api.parsed_data ?? {};
  const name =
    pd.campaign_name?.trim() ||
    pd.product_name?.trim() ||
    `Campaign ${api.campaign_id.slice(0, 8)}`;

  const budget =
    pd.budget == null
      ? "Not set"
      : `₹${Number(pd.budget).toLocaleString("en-IN")}`;

  const createdAt = api.created_at
    ? new Date(api.created_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "—";

  const scheduledSend = api.scheduled_time
    ? new Date(api.scheduled_time).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "—";

  return {
    id: api.campaign_id,
    name,
    product: pd.product_name ?? "",
    productDescription: pd.product_description ?? "",
    ctaLink: pd.cta_link ?? "",
    audienceTags: buildAudienceTags(pd),
    contentHints: buildContentHints(pd),
    brief: api.campaign_brief,
    goal: pd.campaign_objective || pd.campaign_goal || "—",
    budget,
    scheduledSend,
    status: STATUS_MAP[api.status] ?? "draft",
    createdAt,
    segments: [],
    variants: [],
    metrics: {
      openRate: 0,
      clickRate: 0,
      conversions: 0,
      roi: "N/A",
      performance: [],
      segmentPerformance: [],
      variantComparison: [],
    },
  };
}

// ── Context ────────────────────────────────────────────────────────────────

interface CampaignsContextValue {
  campaigns: Campaign[];
  isLoading: boolean;
  error: string | null;
  getCampaign: (id: string) => Campaign | undefined;
  setStatus: (id: string, status: CampaignStatus, note?: string) => void;
  refresh: () => void;
}

const CampaignsContext = createContext<CampaignsContextValue | undefined>(undefined);

export const CampaignsProvider = ({ children }: { children: ReactNode }) => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    listCampaigns()
      .then((data) => {
        if (!cancelled) setCampaigns(data.items.map(adaptCampaign));
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load campaigns");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [tick]);

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  const getCampaign = useCallback(
    (id: string) => campaigns.find((c) => c.id === id),
    [campaigns],
  );

  const setStatus = useCallback(
    (id: string, status: CampaignStatus, note?: string) => {
      // Optimistic update
      setCampaigns((prev) =>
        prev.map((c) =>
          c.id === id ? { ...c, status, revisionNotes: note ?? c.revisionNotes } : c,
        ),
      );
      // Persist to backend
      patchCampaignStatus(id, STATUS_REVERSE[status]).catch(() => {
        // Roll back on failure
        setTick((t) => t + 1);
      });
    },
    [],
  );

  const contextValue = useMemo(
    () => ({ campaigns, isLoading, error, getCampaign, setStatus, refresh }),
    [campaigns, isLoading, error, getCampaign, setStatus, refresh],
  );

  return (
    <CampaignsContext.Provider value={contextValue}>
      {children}
    </CampaignsContext.Provider>
  );
};

export const useCampaigns = () => {
  const ctx = useContext(CampaignsContext);
  if (!ctx) throw new Error("useCampaigns must be used within CampaignsProvider");
  return ctx;
};
