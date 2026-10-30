import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCheck, Lock, Send } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatDateTime, formatMoney } from "../lib/format";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { PageHeader } from "../components/PageHeader";
import { QuoteDiff } from "../components/QuoteDiff";
import { QuoteDocument } from "../components/QuoteDocument";
import { RuleChip } from "../components/Tag";

export default function QuotePage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();

  const quote = useQuery({ queryKey: ["quote", id], queryFn: () => api.quote(id), enabled: !!id });
  const requirement = useQuery({
    queryKey: ["requirement", quote.data?.requirement_id ?? ""],
    queryFn: () => api.requirement(quote.data!.requirement_id),
    enabled: Boolean(quote.data?.requirement_id),
  });
  const rules = useQuery({ queryKey: ["service-rules"], queryFn: api.serviceRules });
  const siblings = useQuery({
    queryKey: ["quotes", quote.data?.requirement_id],
    queryFn: () => api.quotes(quote.data!.requirement_id),
    enabled: Boolean(quote.data),
  });
  const previousQuote = siblings.data?.find(
    (item) => item.quote_number === (quote.data?.quote_number ?? 0) - 1,
  );

  const review = useMutation({
    mutationFn: () => api.reviewQuote(id),
    onSuccess: (updated) => {
      queryClient.setQueryData(["quote", id], updated);
      queryClient.invalidateQueries({ queryKey: ["quotes", updated.requirement_id] });
      queryClient.invalidateQueries({ queryKey: ["requirement", updated.requirement_id] });
    },
  });

  if (quote.isLoading) {
    return <div className="py-20 text-sm text-ink-faint">Loading quote…</div>;
  }

  if (!quote.data) {
    return <div className="py-20 text-sm text-flag-bad">This quote could not be loaded.</div>;
  }

  const data = quote.data;
  const brief = requirement.data?.requirement;
  const messages = requirement.data?.messages ?? [];
  const error = review.error instanceof ApiError ? review.error : null;

  const action =
    data.status === "DRAFT" ? (
      <>
        <p className="max-w-[46ch] text-[12px] leading-relaxed text-ink-muted">
          Reviewing freezes the scope and prices for the client. Amounts, sources and rule references
          become read-only from that point.
        </p>
        <Button busy={review.isPending} icon={<Send size={15} />} onClick={() => review.mutate()}>
          Review and issue
        </Button>
      </>
    ) : data.status === "REVIEWED" ? (
      <>
        <p className="flex items-center gap-2 text-[12px] text-ink-muted">
          <CheckCheck size={14} className="text-pine" />
          Reviewed {formatDateTime(data.reviewed_at)} · waiting for the client to confirm
        </p>
        <Link to={`/requirements/${data.requirement_id}`}>
          <Button variant="secondary" size="sm">
            Back to brief
          </Button>
        </Link>
      </>
    ) : data.status === "CONFIRMED" ? (
      <>
        <p className="flex items-center gap-2 text-[12px] text-pine-deep">
          <Lock size={14} /> Confirmed {formatDateTime(data.confirmed_at)} · this version is now
          read-only
        </p>
        <Link to={`/requirements/${data.requirement_id}`}>
          <Button variant="secondary" size="sm">
            Back to brief
          </Button>
        </Link>
      </>
    ) : (
      <>
        <p className="text-[12px] text-ink-muted">
          Superseded {formatDateTime(data.superseded_at)} after the brief changed.
        </p>
        <Link to={`/requirements/${data.requirement_id}`}>
          <Button variant="secondary" size="sm">
            Back to brief
          </Button>
        </Link>
      </>
    );

  return (
    <div>
      <div className="pb-4">
        <Link
          to={`/requirements/${data.requirement_id}`}
          className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint hover:text-ink"
        >
          <ArrowLeft size={12} /> brief
        </Link>
      </div>

      <PageHeader
        eyebrow={`Quote v${data.quote_number}`}
        title="The version both sides sign."
        description="Amounts are computed from the published rule list. Each line carries the rule that priced it and the client message that justified it."
      />

      <div className="grid gap-8 lg:grid-cols-[1.6fr_0.85fr]">
        <div className="flex flex-col gap-4">
          <QuoteDocument
            quote={data}
            messages={messages}
            clientName={brief?.client_name}
            clientBusiness={brief?.client_business}
            actions={action}
          />
          {previousQuote && data ? <QuoteDiff current={data} previous={previousQuote} /> : null}
          {error ? <p className="text-[12px] text-flag-bad">{error.message}</p> : null}
        </div>

        <aside className="flex flex-col gap-5">
          <Card className="px-5 py-5">
            <span className="label">Rule references</span>
            <ul className="mt-3 flex flex-col gap-2.5">
              {rules.data ? (
                <>
                  <li className="flex items-center justify-between gap-3">
                    <RuleChip ruleRef="rule.base_page" />
                    <span className="numeric text-[12px]">
                      {formatMoney(rules.data.base_page_minor, rules.data.currency)}
                    </span>
                  </li>
                  <li className="flex items-center justify-between gap-3">
                    <RuleChip ruleRef="rule.extra_page" />
                    <span className="numeric text-[12px]">
                      {formatMoney(rules.data.extra_page_minor, rules.data.currency)} / page
                    </span>
                  </li>
                  {rules.data.addons.map((addon) => (
                    <li key={addon.code} className="flex items-center justify-between gap-3">
                      <RuleChip ruleRef={`rule.addon.${addon.code}`} />
                      <span className="numeric text-[12px]">
                        {addon.amount_minor === 0
                          ? "included"
                          : formatMoney(addon.amount_minor, rules.data.currency)}
                      </span>
                    </li>
                  ))}
                  <li className="flex items-center justify-between gap-3 border-t border-line pt-2">
                    <RuleChip ruleRef="rule.lead_time" />
                    <span className="font-mono text-[11px] text-ink-muted">
                      {rules.data.lead_time_days} working days
                    </span>
                  </li>
                </>
              ) : (
                <li className="text-[12px] text-ink-faint">Loading rules…</li>
              )}
            </ul>
          </Card>

          <Card className="px-5 py-5">
            <span className="label">Source messages</span>
            <ul className="mt-3 flex flex-col gap-3">
              {messages
                .filter((message) => message.author === "CLIENT")
                .slice(-2)
                .map((message) => (
                  <li key={message.id} className="flex flex-col gap-1 border-l-2 border-line pl-3">
                    <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
                      rev {message.revision}
                    </span>
                    <p className="line-clamp-4 text-[12px] leading-relaxed text-ink-muted">
                      {message.body}
                    </p>
                  </li>
                ))}
            </ul>
          </Card>

          <p className="px-1 text-[11px] leading-relaxed text-ink-faint">
            Confirmation covers this version only. New scope means a new revision, a new review and a
            new confirmation.
          </p>
        </aside>
      </div>
    </div>
  );
}
