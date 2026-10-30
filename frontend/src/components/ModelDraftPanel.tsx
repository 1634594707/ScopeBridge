import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Sparkles } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { Extraction, PricedCandidate } from "../lib/types";
import { Button } from "./Button";
import { Card } from "./Card";
import { Money } from "./Money";
import { Tag } from "./Tag";

interface ModelDraftPanelProps {
  requirementId: string;
  onUse: (candidate: PricedCandidate) => void;
}

export function ModelDraftPanel({ requirementId, onUse }: ModelDraftPanelProps) {
  const queryClient = useQueryClient();
  const previous = useQuery({
    queryKey: ["extraction", requirementId],
    queryFn: () => api.latestExtraction(requirementId),
    retry: false,
    staleTime: 30_000,
  });

  const draft = useMutation({
    mutationFn: () => api.requestExtraction(requirementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["extraction", requirementId] });
    },
  });

  const extraction: Extraction | undefined = draft.data ?? previous.data?.extraction ?? undefined;
  const error = draft.error instanceof ApiError ? draft.error : null;
  const modelLabel = extraction?.model ?? "deepseek-v4.1-flash";

  return (
    <Card className="flex flex-col gap-4 px-5 py-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="label">Model draft</span>
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            {modelLabel} · {extraction?.prompt_version ?? "facts-v4"}
          </span>
        </div>
        <Tag tone="neutral">advisory</Tag>
      </div>

      <p className="text-[12px] leading-relaxed text-ink-muted">
        The model reads the brief and returns facts. This studio turns those facts into options and
        prices them — the model never sets an amount, and nothing reaches the client until you price
        and issue it.
      </p>

      <Button
        type="button"
        variant="secondary"
        busy={draft.isPending}
        icon={<Sparkles size={15} />}
        onClick={() => draft.mutate()}
      >
        {draft.isPending ? "Reading the brief…" : "Draft with the model"}
      </Button>

      {error ? (
        <div className="flex items-start gap-2 rounded-md border border-flag-bad/30 bg-flag-bad/5 px-3 py-2">
          <AlertTriangle size={14} className="mt-[2px] shrink-0 text-flag-bad" />
          <p className="text-[12px] leading-relaxed text-flag-bad">
            {error.message}
            <span className="ml-1 font-mono text-[10px] uppercase tracking-[0.1em]">
              {error.code}
            </span>
          </p>
        </div>
      ) : null}

      {extraction ? (
        <div className="flex flex-col gap-4 border-t border-line pt-4">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            <span>rev {extraction.record.revision}</span>
            <span>{extraction.latency_ms} ms</span>
            <span>{extraction.candidates.length} option(s)</span>
          </div>

          <dl className="flex flex-col divide-y divide-line/70">
            <ReadRow label="Pages read" value={extraction.facts.pages ?? "—"} />
            <ReadRow
              label="Budget read"
              value={
                extraction.facts.budget_usd === null
                  ? "—"
                  : formatMoney(Math.round(extraction.facts.budget_usd * 100), "USD")
              }
            />
            <ReadRow
              label="Record budget"
              value={
                extraction.record.budget_minor === null
                  ? "—"
                  : formatMoney(extraction.record.budget_minor, "USD")
              }
            />
            <ReadRow
              label="Assets read"
              value={
                extraction.facts.assets_ready === null
                  ? "—"
                  : extraction.facts.assets_ready
                    ? "ready"
                    : "pending"
              }
            />
          </dl>

          {extraction.facts.features.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {extraction.facts.features.map((feature) => (
                <span
                  key={feature}
                  className="rounded-sm border border-line bg-paper px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-[0.08em] text-ink-muted"
                >
                  {feature.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          ) : null}

          {extraction.unsupported_requests.length > 0 ? (
            <p className="text-[11px] leading-relaxed text-flag-warn">
              Asked for but not offered: {extraction.unsupported_requests.join(", ")}. Options below
              narrow the scope instead of promising it.
            </p>
          ) : null}

          {extraction.questions.length > 0 ? (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
                questions before pricing
              </span>
              <ul className="flex flex-col gap-1">
                {extraction.questions.map((question) => (
                  <li key={question} className="text-[12px] leading-relaxed text-ink-muted">
                    — {question}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <ul className="flex flex-col gap-3">
            {extraction.candidates.map((candidate) => (
              <li
                key={candidate.label}
                className="flex flex-col gap-2 rounded-md border border-line bg-paper-card px-3 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-[13px] font-medium leading-snug text-ink">
                    {candidate.label}
                  </span>
                  <Money amountMinor={candidate.total_minor} size="sm" />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <Tag tone={candidate.feasible ? "good" : "warn"}>
                    {candidate.feasible ? "deliverable" : "cannot deliver"}
                  </Tag>
                  <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">
                    {candidate.pages} page{candidate.pages > 1 ? "s" : ""}
                  </span>
                </div>
                <p className="text-[11px] leading-relaxed text-ink-muted">{candidate.rationale}</p>
                {candidate.violations.map((violation) => (
                  <p
                    key={violation.code + violation.detail}
                    className="text-[11px] leading-relaxed text-flag-warn"
                  >
                    {violation.detail}
                  </p>
                ))}
                <div className="flex justify-end">
                  <Button size="sm" variant="ghost" onClick={() => onUse(candidate)}>
                    Use this scope
                  </Button>
                </div>
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap gap-1">
            {extraction.source_message_ids.map((id) => (
              <span
                key={id}
                title={id}
                className="rounded-sm border border-line bg-paper px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-[0.08em] text-ink-faint"
              >
                read msg {id.slice(0, 6)}
              </span>
            ))}
          </div>

          <p className="font-mono text-[10px] uppercase leading-relaxed tracking-[0.1em] text-ink-faint">
            Facts only. Using an option fills the editor below; the server still prices it.
          </p>
        </div>
      ) : null}
    </Card>
  );
}

function ReadRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <dt className="text-[11px] text-ink-faint">{label}</dt>
      <dd className="numeric text-[12px] text-ink">{value}</dd>
    </div>
  );
}
