const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ── Backend shapes ─────────────────────────────────────────────────────────

export interface ApiParsedData {
  product_name: string;
  product_description: string;
  target_audience: string;
  audience_who: string;
  audience_location: string;
  audience_filters: string;
  campaign_goal: string;
  campaign_objective: string;
  campaign_name: string;
  cta_link: string;
  budget: number | null;
  preferred_tone: string;
  key_messages: string[];
  constraints: string | null;
}

export interface ApiCampaign {
  campaign_id: string;
  mock_campaign_id: string | null;
  campaign_brief: string;
  parsed_data: ApiParsedData;
  status: string;
  segments: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
  scheduled_time: string | null;
}

export interface ApiVariant {
  variant_id: string;
  campaign_id: string;
  segment_name: string;
  subject_line: string;
  email_body: string;
  send_time: string;
  variant_type: string;
  personalization_tags: string[];
  status: string;
}

export interface ApiSegmentCriteria {
  age_range?: { min?: number; max?: number } | null;
  gender?: string[] | null;
  cities?: string[] | null;
  occupation_type?: string[] | null;
  app_installed?: string | null;
  existing_customer?: string | null;
}

export interface ApiSegment {
  segment_id: string;
  campaign_id: string;
  segment_name: string;
  description: string;
  customer_ids: string[];
  segment_criteria: ApiSegmentCriteria | null;
}

export interface ApiMetrics {
  variant_id: string;
  campaign_id: string;
  open_rate: number;
  click_rate: number;
  click_through_rate: number;
  total_sent: number;
  unique_opens: number;
  unique_clicks: number;
}

export interface ApiPaginated<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

// ── Campaign endpoints ─────────────────────────────────────────────────────

export async function listCampaigns(skip = 0, limit = 100): Promise<ApiPaginated<ApiCampaign>> {
  const res = await fetch(`${API_BASE}/api/v1/campaigns?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to fetch campaigns (${res.status})`);
  return res.json();
}

export async function getCampaign(id: string): Promise<ApiCampaign> {
  const res = await fetch(`${API_BASE}/api/v1/campaigns/${id}`);
  if (!res.ok) throw new Error(`Campaign not found (${res.status})`);
  return res.json();
}

export async function patchCampaignStatus(id: string, status: string): Promise<ApiCampaign> {
  const res = await fetch(`${API_BASE}/api/v1/campaigns/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error(`Failed to update campaign (${res.status})`);
  return res.json();
}

export async function getCampaignVariants(id: string): Promise<{ variants: ApiVariant[] }> {
  const res = await fetch(`${API_BASE}/api/v1/campaigns/${id}/variants`);
  if (!res.ok) return { variants: [] };
  return res.json();
}

export async function getCampaignSegments(id: string): Promise<{ segments: ApiSegment[] }> {
  const res = await fetch(`${API_BASE}/api/v1/campaigns/${id}/segments`);
  if (!res.ok) return { segments: [] };
  return res.json();
}
