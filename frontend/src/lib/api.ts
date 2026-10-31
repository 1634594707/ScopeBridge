import type {
  ApiErrorBody,
  AttentionPayment,
  ScopeEstimate,
  Extraction,
  ExtractionEnvelope,
  IntakeResponse,
  Message,
  OrderSnapshot,
  Payment,
  PortalView,
  Proposal,
  Quote,
  RequirementDetail,
  RequirementSummary,
  ServiceRules,
  SessionResponse,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, body: ApiErrorBody | null) {
    super(body?.message ?? "The request could not be completed");
    this.name = "ApiError";
    this.status = status;
    this.code = body?.code ?? "unknown_error";
    this.details = body?.details;
  }
}

function csrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)sb_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const csrf = csrfToken();
  if (csrf) {
    headers["X-CSRF-Token"] = csrf;
  }
  if (options.headers) {
    Object.assign(headers, options.headers);
  }

  const response = await fetch(`/api${path}`, {
    method: options.method ?? "GET",
    credentials: "include",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = (await response.json()) as T | ApiErrorBody;
  if (!response.ok) {
    throw new ApiError(response.status, payload as ApiErrorBody);
  }
  return payload as T;
}

export const api = {
  signIn: (email: string, password: string) =>
    request<SessionResponse>("/session", { method: "POST", body: { email, password } }),

  registerClient: (payload: { email: string; password: string; display_name: string }) =>
    request<SessionResponse>("/clients", { method: "POST", body: payload }),

  clientSignIn: (email: string, password: string) =>
    request<SessionResponse>("/client-session", { method: "POST", body: { email, password } }),

  signOut: () => request<void>("/session", { method: "DELETE" }),

  session: () => request<SessionResponse>("/session"),

  deleteRequirement: (id: string) =>
    request<void>(`/requirements/${id}`, { method: "DELETE" }),

  serviceRules: () => request<ServiceRules>("/service-rules"),

  createRequirement: (payload: {
    client_name: string;
    client_business: string;
    client_email: string;
    message: string;
    budget_minor: number;
    deadline: string;
    assets_ready: boolean;
  }) => request<IntakeResponse>("/requirements", { method: "POST", body: payload }),

  requirements: () => request<RequirementSummary[]>("/requirements"),

  requirement: (id: string) => request<RequirementDetail>(`/requirements/${id}`),

  addSellerMessage: (
    id: string,
    payload: { body: string; expected_revision: number; assets_ready?: boolean },
  ) => request(`/requirements/${id}/messages`, { method: "POST", body: payload }),

  createProposal: (
    id: string,
    payload: {
      label: string;
      pages: number;
      addon_codes: string[];
      requested_features: string[];
      assets_ready: boolean;
    },
  ) => request<Proposal>(`/requirements/${id}/proposals`, { method: "POST", body: payload }),

  proposals: (id: string) => request<Proposal[]>(`/requirements/${id}/proposals`),

  requestExtraction: (id: string) =>
    request<Extraction>(`/requirements/${id}/extractions`, { method: "POST" }),

  latestExtraction: (id: string) =>
    request<ExtractionEnvelope>(`/requirements/${id}/extractions/latest`),

  createQuote: (id: string, payload: { proposal_id: string; scope_summary?: string }) =>
    request<Quote>(`/requirements/${id}/quotes`, { method: "POST", body: payload }),

  quotes: (id: string) => request<Quote[]>(`/requirements/${id}/quotes`),

  quote: (id: string) => request<Quote>(`/quotes/${id}`),

  reviewQuote: (id: string) => request<Quote>(`/quotes/${id}/review`, { method: "POST" }),

  portal: (requirementId: string) => request<PortalView>(`/portal/${requirementId}`),

  clientBriefs: () => request<RequirementSummary[]>("/portal/briefs"),

  portalMessage: (
    requirementId: string,
    payload: {
      body: string;
      expected_revision: number;
      budget_minor?: number;
      deadline?: string;
      assets_ready?: boolean;
    },
  ) => request<Message>(`/portal/${requirementId}/messages`, { method: "POST", body: payload }),

  selectProposal: (requirementId: string, proposalId: string) =>
    request<Proposal>(`/portal/${requirementId}/proposals/${proposalId}/select`, {
      method: "POST",
    }),

  confirmQuote: (requirementId: string, quoteId: string) =>
    request<Quote>(`/portal/${requirementId}/quotes/${quoteId}/confirm`, { method: "POST" }),

  startPayment: (requirementId: string, quoteId: string, idempotencyKey: string) =>
    request<Payment>(`/portal/${requirementId}/quotes/${quoteId}/payment-attempts`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    }),

  payment: (id: string) => request<Payment>(`/portal/payments/${id}`),

  capturePayment: (id: string) =>
    request<Payment>(`/portal/payments/${id}/capture`, { method: "POST" }),

  reconcilePayment: (id: string) =>
    request<Payment>(`/payments/${id}/reconcile`, { method: "POST" }),

  retryCreatePayment: (id: string) =>
    request<Payment>(`/payments/${id}/retry-create`, { method: "POST" }),

  closePayment: (id: string, note: string) =>
    request<Payment>(`/payments/${id}/close`, {
      method: "POST",
      body: { note, confirmed_no_order: true },
    }),

  requirementPayments: (id: string) =>
    request<Payment[]>(`/requirements/${id}/payments`),

  requirementOrder: (id: string) =>
    request<{ order: OrderSnapshot | null }>(`/requirements/${id}/order`),

  // Pending backend endpoints. The request carries scope choices only, never an amount;
  // the server prices them with the current rule version.
  estimateScope: (payload: { pages: number; addon_codes: string[] }) =>
    request<ScopeEstimate>("/service-rules/estimate", { method: "POST", body: payload }),

  attentionPayments: () => request<AttentionPayment[]>("/payments/attention"),
};
