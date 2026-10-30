export type QuoteStatus = "DRAFT" | "REVIEWED" | "CONFIRMED" | "SUPERSEDED";
export type Author = "CLIENT" | "SELLER";

export interface Seller {
  id: string;
  email: string;
  display_name: string;
}

export interface SessionResponse {
  seller: Seller;
  csrf_token: string;
}

export interface Addon {
  code: string;
  label: string;
  amount_minor: number;
  description: string;
}

export interface ServiceRules {
  id: string;
  version_no: number;
  currency: string;
  base_page_minor: number;
  extra_page_minor: number;
  revisions_included: number;
  lead_time_days: number;
  asset_buffer_days: number;
  addons: Addon[];
  capabilities: string[];
  exclusions: string[];
  notes: string;
}

export interface Message {
  id: string;
  author: Author;
  body: string;
  budget_minor: number | null;
  deadline: string | null;
  assets_ready: boolean | null;
  revision: number;
  created_at: string;
}

export interface RequirementSummary {
  id: string;
  client_name: string;
  client_business: string;
  revision: number;
  status: string;
  budget_minor: number | null;
  deadline: string | null;
  assets_ready: boolean | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface RequirementDetail {
  requirement: RequirementSummary;
  messages: Message[];
}

export interface Violation {
  code: string;
  detail: string;
  rule_ref: string;
}

export interface Proposal {
  id: string;
  requirement_id: string;
  source_revision: number;
  label: string;
  pages: number;
  addon_codes: string[];
  requested_features: string[];
  assets_ready: boolean;
  feasible: boolean;
  total_minor: number;
  currency: string;
  violations: Violation[];
  selected_at: string | null;
  created_at: string;
}

export interface QuoteItem {
  id: string;
  position: number;
  code: string;
  label: string;
  amount_minor: number;
  rule_ref: string;
  source_message_id: string | null;
  included: boolean;
}

export interface Quote {
  id: string;
  requirement_id: string;
  proposal_id: string;
  quote_number: number;
  source_revision: number;
  currency: string;
  total_minor: number;
  status: QuoteStatus;
  scope_summary: string;
  reviewed_at: string | null;
  confirmed_at: string | null;
  superseded_at: string | null;
  expires_at: string | null;
  created_at: string;
  items: QuoteItem[];
}

export interface PortalView {
  requirement: RequirementSummary;
  messages: Message[];
  proposals: Proposal[];
  quotes: Quote[];
  service_rule_version: number;
  currency: string;
}

export interface IntakeResponse {
  requirement_id: string;
  portal_token: string;
  portal_path: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}
