import { Check, TriangleAlert } from "lucide-react";
import type { Proposal, ServiceRules } from "../lib/types";
import { formatMoney } from "../lib/format";
import { Money } from "./Money";
import { Tag } from "./Tag";
import { Button } from "./Button";
import { cn } from "../lib/cn";

interface ProposalCardProps {
  proposal: Proposal;
  rules: ServiceRules | undefined;
  budgetMinor: number | null;
  stale: boolean;
  busy: boolean;
  onSelect?: (proposal: Proposal) => void;
}

export function ProposalCard({ proposal, rules, budgetMinor, stale, busy, onSelect }: ProposalCardProps) {
  const delta = budgetMinor === null ? null : budgetMinor - proposal.total_minor;
  const selected = proposal.selected_at !== null;
  const addonLabels =
    rules?.addons.filter((addon) => proposal.addon_codes.includes(addon.code)) ?? [];

  return (
    <article
      className={cn(
        "flex flex-col gap-4 rounded-lg border bg-paper-card px-5 py-5 transition-shadow duration-200",
        selected ? "border-pine shadow-lift" : "border-line hover:shadow-card",
      )}
    >
      <header className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="label">Scope option</span>
            {selected ? (
              <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.14em] text-pine">
                <Check size={12} /> chosen
              </span>
            ) : null}
          </div>
          <h3 className="text-[16px] font-semibold leading-snug tracking-[-0.015em] text-ink">
            {proposal.label}
          </h3>
        </div>
        <Money amountMinor={proposal.total_minor} currency={proposal.currency} size="lg" />
      </header>

      <ul className="flex flex-col divide-y divide-line/70 border-y border-line/70">
        <li className="flex items-baseline justify-between gap-4 py-2">
          <span className="text-[13px] text-ink-muted">
            {proposal.pages} page{proposal.pages > 1 ? "s" : ""}, mobile-ready
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            included
          </span>
        </li>
        {addonLabels.map((addon) => (
          <li key={addon.code} className="flex items-baseline justify-between gap-4 py-2">
            <span className="text-[13px] text-ink-muted">{addon.label}</span>
            <span className="numeric text-[12px] text-ink-muted">
              {addon.amount_minor === 0 ? "included" : formatMoney(addon.amount_minor, proposal.currency)}
            </span>
          </li>
        ))}
        {rules && rules.exclusions.length > 0 ? (
          <li className="flex flex-col gap-1 py-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
              not included
            </span>
            <span className="text-[12px] leading-relaxed text-ink-faint">
              {rules.exclusions.join(" · ")}
            </span>
          </li>
        ) : null}
      </ul>

      {delta !== null ? (
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
            Against your {formatMoney(budgetMinor ?? 0, proposal.currency)} budget
          </span>
          <span
            className={cn(
              "numeric text-[12px]",
              delta >= 0 ? "text-flag-good" : "text-flag-bad",
            )}
          >
            {delta >= 0 ? `${formatMoney(delta, proposal.currency)} left` : `${formatMoney(-delta, proposal.currency)} over`}
          </span>
        </div>
      ) : null}

      {proposal.violations.length > 0 ? (
        <div className="flex flex-col gap-2 rounded-md border border-flag-warn/30 bg-flag-warn/5 px-3 py-3">
          <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-flag-warn">
            <TriangleAlert size={12} /> unsatisfied conditions
          </span>
          <ul className="flex flex-col gap-1.5">
            {proposal.violations.map((violation) => (
              <li key={`${violation.code}-${violation.detail}`} className="text-[12px] leading-relaxed text-ink-muted">
                {violation.detail}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-auto flex items-center justify-between gap-3 pt-1">
        <Tag tone={proposal.feasible ? "good" : "warn"}>
          {proposal.feasible ? "Deliverable as scoped" : "Cannot be delivered"}
        </Tag>
        {stale ? (
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            older revision
          </span>
        ) : onSelect ? (
          <Button
            size="sm"
            variant={selected ? "secondary" : "primary"}
            disabled={!proposal.feasible || selected || stale}
            busy={busy}
            onClick={() => onSelect(proposal)}
          >
            {selected ? "Chosen" : "Choose this scope"}
          </Button>
        ) : null}
      </div>
    </article>
  );
}
