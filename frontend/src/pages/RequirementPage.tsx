import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, FileText, MessageSquarePlus } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatDeadline, formatMoney } from "../lib/format";
import { Button } from "../components/Button";
import { Card, CardHeader } from "../components/Card";
import { Field, TextArea } from "../components/Field";
import { MessageTimeline } from "../components/MessageTimeline";
import { ModelDraftPanel } from "../components/ModelDraftPanel";
import { Money } from "../components/Money";
import { PaymentHistory } from "../components/PaymentHistory";
import { PageHeader } from "../components/PageHeader";
import { ScopeEditor } from "../components/ScopeEditor";
import { StatusPill } from "../components/StatusPill";
import { Tag } from "../components/Tag";

export default function RequirementPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [reply, setReply] = useState("");
  const [seed, setSeed] = useState<{
    key: string;
    label: string;
    pages: number;
    addons: string[];
  } | null>(null);

  const requirement = useQuery({
    queryKey: ["requirement", id],
    queryFn: () => api.requirement(id),
    enabled: id.length > 0,
  });
  const proposals = useQuery({
    queryKey: ["proposals", id],
    queryFn: () => api.proposals(id),
    enabled: id.length > 0,
  });
  const quotes = useQuery({
    queryKey: ["quotes", id],
    queryFn: () => api.quotes(id),
    enabled: id.length > 0,
  });
  const rules = useQuery({ queryKey: ["service-rules"], queryFn: api.serviceRules });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["requirement", id] });
    queryClient.invalidateQueries({ queryKey: ["proposals", id] });
    queryClient.invalidateQueries({ queryKey: ["quotes", id] });
    queryClient.invalidateQueries({ queryKey: ["requirements"] });
  };

  const createQuote = useMutation({
    mutationFn: (proposalId: string) => api.createQuote(id, { proposal_id: proposalId }),
    onSuccess: (quote) => {
      refresh();
      navigate(`/quotes/${quote.id}`);
    },
  });

  const addReply = useMutation({
    mutationFn: (payload: { body: string; expected_revision: number }) =>
      api.addSellerMessage(id, payload),
    onSuccess: () => {
      setReply("");
      refresh();
    },
  });

  if (requirement.isLoading) {
    return <div className="py-20 text-sm text-ink-faint">Loading brief…</div>;
  }

  if (!requirement.data) {
    return <div className="py-20 text-sm text-flag-bad">This brief could not be loaded.</div>;
  }

  const detail = requirement.data;
  const brief = detail.requirement;
  const proposalRows = proposals.data ?? [];
  const quoteRows = quotes.data ?? [];
  const currentProposals = proposalRows.filter((row) => row.source_revision === brief.revision);
  const quoteError = createQuote.error instanceof ApiError ? createQuote.error : null;
  const replyError = addReply.error instanceof ApiError ? addReply.error : null;

  return (
    <div>
      <div className="pb-4">
        <Link
          to="/console"
          className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint hover:text-ink"
        >
          <ArrowLeft size={12} /> console
        </Link>
      </div>

      <PageHeader
        eyebrow={`Brief · rev ${brief.revision}`}
        title={
          <>
            {brief.client_name}
            {brief.client_business ? (
              <span className="text-ink-faint"> · {brief.client_business}</span>
            ) : null}
          </>
        }
        description="Read the original messages, price a scope against the published rules, then issue a quote for the client to confirm."
        meta={
          <>
            <span className="flex items-baseline gap-2">
              <span className="label">Budget</span>
              <Money amountMinor={brief.budget_minor ?? 0} size="sm" />
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Live by</span>
              <span className="text-[13px]">{formatDeadline(brief.deadline)}</span>
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Assets</span>
              <Tag tone={brief.assets_ready ? "good" : "warn"}>
                {brief.assets_ready ? "ready" : "pending"}
              </Tag>
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Messages</span>
              <span className="numeric text-[13px]">{brief.message_count}</span>
            </span>
          </>
        }
      />

      <div className="grid gap-8 lg:grid-cols-[1.35fr_0.9fr]">
        <div className="flex flex-col gap-6">
          <Card className="px-5 py-5">
            <CardHeader
              eyebrow="Original brief"
              title="What the client actually said"
              description="Revisions are append-only. Nothing here can be edited after the fact."
            />
            <div className="mt-5">
              <MessageTimeline messages={detail.messages} />
            </div>
          </Card>

          <Card className="px-5 py-5">
            <CardHeader eyebrow="Reply" title="Add a note to this brief" />
            <form
              className="mt-4 flex flex-col gap-3"
              onSubmit={(event) => {
                event.preventDefault();
                if (reply.trim().length < 2) return;
                addReply.mutate({ body: reply.trim(), expected_revision: brief.revision });
              }}
            >
              <Field
                label="Message"
                htmlFor="seller-reply"
                hint={`Sending creates revision ${brief.revision + 1} and supersedes any open draft quote.`}
                error={replyError?.message}
              >
                <TextArea
                  id="seller-reply"
                  value={reply}
                  onChange={(event) => setReply(event.target.value)}
                  placeholder="The three page version with on-site ordering is outside the $500 budget. Here is what fits."
                  rows={3}
                />
              </Field>
              <div className="flex justify-end">
                <Button
                  type="submit"
                  variant="secondary"
                  busy={addReply.isPending}
                  icon={<MessageSquarePlus size={15} />}
                >
                  Send message
                </Button>
              </div>
            </form>
          </Card>

          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <span className="label">Quotes on this brief</span>
              <span className="font-mono text-[10px] text-ink-faint">{quoteRows.length}</span>
            </div>
            {quoteRows.length === 0 ? (
              <p className="px-5 py-5 text-[13px] text-ink-muted">
                No quote yet. Price a scope, then issue the draft to review.
              </p>
            ) : (
              <ul className="divide-y divide-line">
                {quoteRows.map((quote) => (
                  <li key={quote.id}>
                    <Link
                      to={`/quotes/${quote.id}`}
                      className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-paper"
                    >
                      <span className="flex items-center gap-3">
                        <span className="font-mono text-[11px] text-ink-faint">
                          v{quote.quote_number}
                        </span>
                        <span className="text-[13px] text-ink">rev {quote.source_revision}</span>
                      </span>
                      <span className="flex items-center gap-3">
                        <Money amountMinor={quote.total_minor} size="sm" tone="muted" />
                        <StatusPill status={quote.status} />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <PaymentHistory requirementId={id} />
        </div>

        <aside className="flex flex-col gap-6">
          <ModelDraftPanel
            requirementId={id}
            onUse={(candidate) =>
              setSeed({
                key: `${candidate.label}-${candidate.total_minor}-${Date.now()}`,
                label: candidate.label,
                pages: candidate.pages,
                addons: candidate.addon_codes,
              })
            }
          />

          <Card className="px-5 py-5">
            {rules.data ? (
              <ScopeEditor
                key={seed?.key ?? "manual"}
                requirementId={id}
                revision={brief.revision}
                rules={rules.data}
                usedAtThisRevision={currentProposals.length}
                initialLabel={seed?.label}
                initialPages={seed?.pages}
                initialAddons={seed?.addons}
              />
            ) : (
              <p className="text-[13px] text-ink-faint">Loading the price list…</p>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <span className="label">Priced options</span>
              <span className="font-mono text-[10px] text-ink-faint">
                {currentProposals.length}/2 this revision
              </span>
            </div>
            {proposalRows.length === 0 ? (
              <p className="px-5 py-5 text-[13px] text-ink-muted">
                Nothing priced yet. The client sees exactly what you price here.
              </p>
            ) : (
              <ul className="divide-y divide-line">
                {proposalRows
                  .slice()
                  .reverse()
                  .map((proposal) => {
                    const stale = proposal.source_revision !== brief.revision;
                    return (
                      <li key={proposal.id} className="flex flex-col gap-2 px-5 py-3.5">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex flex-col gap-0.5">
                            <span className="text-[13px] font-medium text-ink">{proposal.label}</span>
                            <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">
                              {proposal.pages} pages · rev {proposal.source_revision}
                              {proposal.selected_at ? " · chosen by client" : ""}
                            </span>
                          </div>
                          <Money amountMinor={proposal.total_minor} size="sm" />
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <Tag tone={proposal.feasible ? "good" : "warn"}>
                            {proposal.feasible ? "deliverable" : "cannot deliver"}
                          </Tag>
                          <Button
                            size="sm"
                            variant="secondary"
                            disabled={!proposal.feasible || stale || createQuote.isPending}
                            busy={createQuote.isPending && createQuote.variables === proposal.id}
                            icon={<FileText size={13} />}
                            onClick={() => createQuote.mutate(proposal.id)}
                          >
                            Draft quote
                          </Button>
                        </div>
                        {proposal.violations.length > 0 ? (
                          <ul className="flex flex-col gap-1 border-t border-line/70 pt-2">
                            {proposal.violations.map((violation) => (
                              <li key={violation.code + violation.detail} className="text-[11px] leading-relaxed text-flag-warn">
                                {violation.detail}
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </li>
                    );
                  })}
              </ul>
            )}
          </Card>

          {quoteError ? (
            <p className="text-[12px] text-flag-bad">{quoteError.message}</p>
          ) : null}

          {rules.data ? (
            <p className="px-1 font-mono text-[10px] uppercase leading-relaxed tracking-[0.1em] text-ink-faint">
              {formatMoney(rules.data.base_page_minor, rules.data.currency)} first page ·{" "}
              {rules.data.lead_time_days} working days · {rules.data.revisions_included} revision rounds
            </p>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
