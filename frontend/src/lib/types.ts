export type QuoteStatus =
  | "DRAFT"
  | "REVIEWED"
  | "CONFIRMED"
  | "PAYMENT_LOCKED"
  | "PAID"
  | "SUPERSEDED";
export type Author = "CLIENT" | "SELLER";

export type AccountRole = "SELLER" | "CLIENT";

export interface SessionAccount {
  id: string;
  email: string;
  display_name: string;
  role: AccountRole;
}

export interface SessionResponse {
  account: SessionAccount;
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
  /** Seller list only: false once an order snapshot (the receipt) exists. */
  deletable?: boolean;
}

export interface Clarification {
  id: string;
  requirement_id: string;
  source_revision: number;
  kind: "AI" | "MANUAL";
  status: "PENDING" | "CONFIRMED";
  questions: string[];
  unsupported_requests: string[];
  answers: string;
  acknowledged: boolean;
  acknowledged_unsupported: boolean;
  reason_code: string | null;
  note: string;
  confirmed_at: string | null;
  created_at: string;
}

export interface RequirementDetail {
  requirement: RequirementSummary;
  messages: Message[];
  clarification: Clarification | null;
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
  clarification: Clarification | null;
}

export interface Payment {
  id: string;
  quote_id: string;
  requirement_id: string;
  status: string;
  amount_minor: number;
  currency: string;
  approve_url: string | null;
  paypal_order_id: string | null;
  paypal_capture_id: string | null;
  error_code: string | null;
  retry_count: number;
  resolved_at: string | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface SnapshotItem {
  code: string;
  label: string;
  amount_minor: number;
  included: boolean;
}

export interface OrderSnapshot {
  id: string;
  requirement_id: string;
  quote_id: string;
  order_id: string;
  capture_id: string;
  amount_minor: number;
  currency: string;
  payer_email: string;
  captured_at: string;
  items: SnapshotItem[];
}

export interface PortalView {
  requirement: RequirementSummary;
  messages: Message[];
  proposals: Proposal[];
  quotes: Quote[];
  payments: Payment[];
  order: OrderSnapshot | null;
  clarification: Clarification | null;
  service_rule_version: number;
  currency: string;
}

export interface ModelFacts {
  pages: number | null;
  budget_usd: number | null;
  deadline_days: number | null;
  assets_ready: boolean | null;
  features: string[];
}

export interface ExtractionRecord {
  revision: number;
  budget_minor: number | null;
  deadline: string | null;
  assets_ready: boolean | null;
}

export interface PricedCandidate {
  label: string;
  pages: number;
  addon_codes: string[];
  requested_features: string[];
  rationale: string;
  feasible: boolean;
  total_minor: number;
  currency: string;
  violations: Violation[];
}

export interface Extraction {
  id: string;
  model: string;
  prompt_version: string;
  latency_ms: number;
  created_at: string;
  facts: ModelFacts;
  record: ExtractionRecord;
  source_message_ids: string[];
  unsupported_requests: string[];
  questions: string[];
  candidates: PricedCandidate[];
}

export interface ExtractionEnvelope {
  extraction: Extraction | null;
}

export interface IntakeResponse {
  requirement_id: string;
  brief_path: string;
}

/** Response of `POST /api/service-rules/estimate`. */
export interface ScopeEstimate {
  rule_version: number;
  currency: string;
  total_minor: number;
  items: { code: string; label: string; amount_minor: number; rule_ref: string }[];
  violations: Violation[];
}

/** Row of `GET /api/payments/attention`. */
export interface AttentionPayment extends Payment {
  client_name: string;
  client_business: string;
  quote_number: number;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}
