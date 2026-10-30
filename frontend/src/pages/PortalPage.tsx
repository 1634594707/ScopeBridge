import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { CheckCircle2, MessageSquarePlus, RefreshCw } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { readPortalToken, rememberPortalToken } from "../lib/customerToken";
import { formatDeadline, formatMoney } from "../lib/format";
import { Button } from "../components/Button";
import { Card, CardHeader } from "../components/Card";
import { Field, Input, TextArea } from "../components/Field";
import { MessageTimeline } from "../components/MessageTimeline";
import { Money } from "../components/Money";
import { PaymentPanel } from "../components/PaymentPanel";
import { PageHeader } from "../components/PageHeader";
import { ProposalCard } from "../components/ProposalCard";
import { QuoteDocument } from "../components/QuoteDocument";
import { StatusPill } from "../components/StatusPill";
import { Tag } from "../components/Tag";
import { EmptyState } from "../components/EmptyState";

export default function PortalPage() {
  const { token = "" } = useParams();
  const [storedToken] = useState(() => {
    if (readPortalToken() !== token) rememberPortalToken(token);
    return token;
  });
  const queryClient = useQueryClient();
  const [changeNote, setChangeNote] = useState("");
  const [formError, setFormError] = useState("");

  const portal = useQuery({
    queryKey: ["portal", storedToken],
    queryFn: api.portal,
    enabled: storedToken.length > 0,
  });
  const rules = useQuery({ queryKey: ["service-rules"], queryFn: api.serviceRules });

  const select = useMutation({
    mutationFn: api.selectProposal,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["portal", storedToken] }),
  });

  const confirm = useMutation({
    mutationFn: api.confirmQuote,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["portal", storedToken] }),
  });

  const startPayment = useMutation({
    mutationFn: (quoteId: string) => api.startPayment(quoteId, crypto.randomUUID()),
    onSuccess: (payment) => {
      queryClient.invalidateQueries({ queryKey: ["portal", storedToken] });
      if (payment.approve_url) {
        window.location.href = payment.approve_url;
      }
    },
  });

  const [budget, setBudget] = useState("");
  const [deadline, setDeadline] = useState("");
  const [assets, setAssets] = useState<"keep" | "ready" | "pending">("keep");
  const [changeSaved, setChangeSaved] = useState<number | null>(null);

  const requestChange = useMutation({
    mutationFn: api.portalMessage,
    onSuccess: (message) => {
      setChangeSaved(message.revision);
      setFormError("");
      setChangeNote("");
      setBudget("");
      setDeadline("");
      setAssets("keep");
      queryClient.invalidateQueries({ queryKey: ["portal", storedToken] });
    },
  });

  const data = portal.data;
  const messages = data?.messages ?? [];
  const currentRevision = data?.requirement.revision ?? 1;
  const proposals = useMemo(
    () => [...(data?.proposals ?? [])].sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [data?.proposals],
  );
  const quotes = data?.quotes ?? [];
  const latestQuote = quotes[0];
  const latestRound = proposals.filter((proposal) => proposal.source_revision === currentRevision);

  const submitChange = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const note = changeNote.trim();
    if (note.length < 5) {
      setFormError("Describe the change in a sentence.");
      return;
    }
    const budgetValue = budget === "" ? undefined : Math.round(Number(budget) * 100);
    if (budgetValue !== undefined && (Number.isNaN(budgetValue) || budgetValue < 0)) {
      setFormError("Enter the new budget as a number, or leave it empty.");
      return;
    }
    setFormError("");
    setChangeSaved(null);
    requestChange.mutate({
      body: note,
      expected_revision: currentRevision,
      budget_minor: budgetValue,
      deadline: deadline === "" ? undefined : deadline,
      assets_ready: assets === "keep" ? undefined : assets === "ready",
    });
  };

  const changeError = requestChange.error instanceof ApiError ? requestChange.error : null;
  const changeErrorMessage = changeError
    ? changeError.code === "revision_conflict"
      ? "This brief changed while you were writing. Reload to see the latest revision — your text is still here."
      : changeError.message
    : "";

  if (portal.isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <span className="h-4 w-4 animate-spin rounded-full border border-pine border-t-transparent" />
      </div>
    );
  }

  if (portal.error) {
    const status = portal.error instanceof ApiError ? portal.error.status : 0;
    return (
      <div className="mx-auto max-w-md py-24">
        <span className="label">Private link</span>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em]">
          {status === 401 ? "This link is no longer valid" : "The brief could not be loaded"}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          Ask the studio to send a fresh link, or open the brief from the message that contained it.
        </p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const requirement = data.requirement;
  const selectError = select.error instanceof ApiError ? select.error : null;
  const confirmError = confirm.error instanceof ApiError ? confirm.error : null;

  return (
    <div>
      <PageHeader
        eyebrow="Client portal"
        title={
          <>
            {requirement.client_name}
            {requirement.client_business ? (
              <span className="text-ink-faint"> · {requirement.client_business}</span>
            ) : null}
          </>
        }
        description="This page is private to your brief. Every price below was computed from the studio's published rules, not typed by hand."
        meta={
          <>
            <span className="flex items-baseline gap-2">
              <span className="label">Budget</span>
              <Money amountMinor={requirement.budget_minor ?? 0} size="sm" />
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Live by</span>
              <span className="text-[13px] font-medium">{formatDeadline(requirement.deadline)}</span>
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Brief</span>
              <span className="font-mono text-[12px]">rev {requirement.revision}</span>
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Price list</span>
              <span className="font-mono text-[12px]">v{data.service_rule_version}</span>
            </span>
          </>
        }
      />

      <div className="grid gap-8 lg:grid-cols-[1.55fr_0.85fr]">
        <div className="flex flex-col gap-8">
          <section className="flex flex-col gap-4">
            <div className="flex items-end justify-between gap-4">
              <div className="flex flex-col gap-1">
                <span className="label">Scope options</span>
                <h2 className="text-[20px] font-semibold tracking-[-0.02em]">
                  What the studio can do with your brief
                </h2>
              </div>
              <Tag>{latestRound.length}/2 options</Tag>
            </div>

            {proposals.length === 0 ? (
              <EmptyState
                title="No scopes yet"
                body="The studio is reading your brief. You will see up to two priced options here, including any that cannot be delivered and why."
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {proposals.map((proposal) => (
                  <ProposalCard
                    key={proposal.id}
                    proposal={proposal}
                    rules={rules.data}
                    budgetMinor={requirement.budget_minor}
                    stale={proposal.source_revision !== currentRevision}
                    busy={select.isPending}
                    onSelect={(value) => select.mutate(value.id)}
                  />
                ))}
              </div>
            )}
            {selectError ? (
              <p className="text-[12px] text-flag-bad">{selectError.message}</p>
            ) : null}
          </section>

          <section className="flex flex-col gap-4">
            <div className="flex items-end justify-between gap-4">
              <div className="flex flex-col gap-1">
                <span className="label">Quote</span>
                <h2 className="text-[20px] font-semibold tracking-[-0.02em]">The version you confirm</h2>
              </div>
            </div>

            {!latestQuote ? (
              <EmptyState
                title="No quote issued yet"
                body="Once you choose a scope, the studio reviews it and issues a quote. Nothing is payable before then."
              />
            ) : (
              <>
                <QuoteDocument
                  quote={latestQuote}
                  messages={messages}
                  clientName={requirement.client_name}
                  clientBusiness={requirement.client_business}
                  actions={
                    <>
                      <p className="max-w-[42ch] text-[12px] leading-relaxed text-ink-muted">
                        {latestQuote.status === "REVIEWED"
                          ? "Confirming freezes this version and opens the sandbox payment step."
                          : latestQuote.status === "SUPERSEDED"
                            ? "This version was replaced after the brief changed."
                            : latestQuote.status === "DRAFT"
                              ? "The studio has not reviewed this draft yet."
                              : "Anything that changes the work starts a new brief; this version stays as it is."}
                      </p>
                      {latestQuote.status === "REVIEWED" ? (
                        <Button
                          busy={confirm.isPending}
                          icon={<CheckCircle2 size={15} />}
                          onClick={() => confirm.mutate(latestQuote.id)}
                        >
                          Confirm this version
                        </Button>
                      ) : null}
                    </>
                  }
                />

                {["CONFIRMED", "PAYMENT_LOCKED", "PAID"].includes(latestQuote.status) ? (
                  <PaymentPanel
                    quote={latestQuote}
                    payment={data.payments.find((item) => item.quote_id === latestQuote.id)}
                    order={data.order}
                    busy={startPayment.isPending}
                    error={
                      startPayment.error instanceof ApiError ? startPayment.error.message : ""
                    }
                    onStart={() => startPayment.mutate(latestQuote.id)}
                  />
                ) : null}
                {confirmError ? (
                  <p className="text-[12px] text-flag-bad">{confirmError.message}</p>
                ) : null}

                {quotes.length > 1 ? (
                  <ul className="flex flex-col divide-y divide-line rounded-lg border border-line bg-paper-card">
                    {quotes.slice(1).map((quote) => (
                      <li key={quote.id} className="flex items-center justify-between gap-4 px-4 py-2.5">
                        <span className="font-mono text-[11px] text-ink-faint">
                          v{quote.quote_number} · rev {quote.source_revision}
                        </span>
                        <div className="flex items-center gap-3">
                          <Money amountMinor={quote.total_minor} size="sm" tone="muted" />
                          <StatusPill status={quote.status} />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            )}
          </section>
        </div>

        <aside className="flex flex-col gap-5">
          <Card className="px-5 py-5">
            <CardHeader
              eyebrow="Conversation"
              title="Brief history"
              description="Every revision is kept. A change makes the current draft stale instead of rewriting history."
            />
            <div className="mt-5">
              <MessageTimeline messages={messages} />
            </div>
          </Card>

          <Card className="px-5 py-5">
            <CardHeader
              eyebrow="Request changes"
              title="Something missing?"
              description={`Adding a note creates revision ${currentRevision + 1} and pauses any open draft.`}
            />
            <form onSubmit={submitChange} className="mt-4 flex flex-col gap-3">
              <Field label="What changed?" htmlFor="portal-change" error={formError}>
                <TextArea
                  id="portal-change"
                  value={changeNote}
                  onChange={(event) => setChangeNote(event.target.value)}
                  placeholder="We also need a contact form and the menu in two languages."
                  rows={4}
                />
              </Field>

              <div className="grid gap-3 sm:grid-cols-2">
                <Field
                  label="New budget (USD)"
                  htmlFor="portal-budget"
                  hint="Leave empty to keep the current budget."
                >
                  <Input
                    id="portal-budget"
                    type="number"
                    min={0}
                    step="any"
                    value={budget}
                    onChange={(event) => setBudget(event.target.value)}
                    placeholder={
                      requirement.budget_minor === null
                        ? "500"
                        : String(requirement.budget_minor / 100)
                    }
                  />
                </Field>
                <Field
                  label="New go-live date"
                  htmlFor="portal-deadline"
                  hint="Leave empty to keep the current date."
                >
                  <Input
                    id="portal-deadline"
                    type="date"
                    value={deadline}
                    onChange={(event) => setDeadline(event.target.value)}
                  />
                </Field>
              </div>

              <fieldset className="flex flex-col gap-2">
                <legend className="label">Materials</legend>
                <div className="flex flex-wrap gap-2">
                  {(
                    [
                      ["keep", "No change"],
                      ["ready", "Photos and copy are ready"],
                      ["pending", "Still gathering"],
                    ] as const
                  ).map(([value, text]) => (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={assets === value}
                      onClick={() => setAssets(value)}
                      className={
                        assets === value
                          ? "rounded-sm border border-pine bg-pine-wash px-2.5 py-1.5 text-[12px] text-pine-deep"
                          : "rounded-sm border border-line bg-paper-card px-2.5 py-1.5 text-[12px] text-ink-muted hover:border-ink/25 hover:text-ink"
                      }
                    >
                      {text}
                    </button>
                  ))}
                </div>
              </fieldset>

              {changeErrorMessage ? (
                <p className="rounded-md border border-flag-bad/30 bg-flag-bad/5 px-3 py-2 text-[12px] leading-relaxed text-flag-bad">
                  {changeErrorMessage}
                </p>
              ) : null}
              {changeSaved !== null ? (
                <p className="rounded-md border border-flag-good/30 bg-flag-good/5 px-3 py-2 text-[12px] leading-relaxed text-flag-good">
                  Saved as revision {changeSaved}. The studio sees the new budget, date and material
                  state before pricing again.
                </p>
              ) : null}

              <Button
                type="submit"
                variant="secondary"
                busy={requestChange.isPending}
                icon={<MessageSquarePlus size={15} />}
              >
                Send to studio
              </Button>
            </form>
          </Card>

          <div className="flex items-start gap-2 px-1 text-[11px] leading-relaxed text-ink-faint">
            <RefreshCw size={13} className="mt-0.5 shrink-0" />
            <span>
              Keep this link private. It grants access to this brief only, and it is not a payment
              credential.
            </span>
          </div>

          {rules.data ? (
            <div className="px-1 font-mono text-[10px] uppercase leading-relaxed tracking-[0.12em] text-ink-faint">
              {rules.data.lead_time_days} working days from assets ·{" "}
              {formatMoney(rules.data.base_page_minor, rules.data.currency)} first page ·{" "}
              {rules.data.revisions_included} revision rounds
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
