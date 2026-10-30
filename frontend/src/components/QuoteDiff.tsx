import { useMemo } from "react";
import type { Quote, QuoteItem } from "../lib/types";
import { formatMoney } from "../lib/format";
import { Card, CardHeader } from "./Card";
import { Money } from "./Money";
import { Tag } from "./Tag";

interface QuoteDiffProps {
  current: Quote;
  previous: Quote;
}

type Change = "added" | "removed" | "changed" | "same";

interface DiffRow {
  label: string;
  change: Change;
  before: number | null;
  after: number | null;
}

export function QuoteDiff({ current, previous }: QuoteDiffProps) {
  const rows = useMemo(() => diffItems(previous.items, current.items), [current, previous]);
  const delta = current.total_minor - previous.total_minor;
  const changed = rows.filter((row) => row.change !== "same");

  return (
    <Card className="px-5 py-5">
      <CardHeader
        eyebrow={`v${previous.quote_number} → v${current.quote_number}`}
        title="What changed"
        description="Line items are compared by label. Excluded lines never carry money, so a change there is a scope change, not a price change."
      />

      <div className="mt-4 flex items-baseline justify-between border-y border-line py-3">
        <span className="label">Total</span>
        <span className="flex items-baseline gap-3">
          <Money amountMinor={previous.total_minor} size="sm" tone="muted" />
          <span className="text-ink-faint">→</span>
          <Money amountMinor={current.total_minor} size="sm" />
          <span
            className={
              delta === 0
                ? "numeric text-[11px] text-ink-faint"
                : delta > 0
                  ? "numeric text-[11px] text-flag-bad"
                  : "numeric text-[11px] text-flag-good"
            }
          >
            {delta === 0
              ? "no change"
              : `${delta > 0 ? "+" : "−"}${formatMoney(Math.abs(delta), current.currency)}`}
          </span>
        </span>
      </div>

      {changed.length === 0 ? (
        <p className="mt-4 text-[12px] leading-relaxed text-ink-muted">
          The line items are identical to the previous version; only metadata changed.
        </p>
      ) : (
        <ul className="mt-3 flex flex-col divide-y divide-line/70">
          {changed.map((row) => (
            <li key={row.change + row.label} className="flex items-baseline justify-between gap-3 py-2">
              <span className="flex items-center gap-2">
                <Tag
                  tone={
                    row.change === "added" ? "good" : row.change === "removed" ? "bad" : "warn"
                  }
                >
                  {row.change}
                </Tag>
                <span className="text-[12px] text-ink">{row.label}</span>
              </span>
              <span className="numeric flex items-baseline gap-2 text-[11px]">
                {row.before === null ? null : (
                  <span className="text-ink-faint">{formatMoney(row.before, current.currency)}</span>
                )}
                {row.before !== null && row.after !== null ? (
                  <span className="text-ink-faint">→</span>
                ) : null}
                {row.after === null ? null : (
                  <span className="text-ink">{formatMoney(row.after, current.currency)}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function diffItems(before: QuoteItem[], after: QuoteItem[]): DiffRow[] {
  const previousByLabel = new Map(before.map((item) => [item.label, item]));
  const currentLabels = new Set(after.map((item) => item.label));
  const rows: DiffRow[] = [];

  for (const item of after) {
    const old = previousByLabel.get(item.label);
    if (!old) {
      rows.push({ label: item.label, change: "added", before: null, after: item.amount_minor });
      continue;
    }
    rows.push({
      label: item.label,
      change: old.amount_minor === item.amount_minor ? "same" : "changed",
      before: old.amount_minor,
      after: item.amount_minor,
    });
  }
  for (const item of before) {
    if (!currentLabels.has(item.label)) {
      rows.push({ label: item.label, change: "removed", before: item.amount_minor, after: null });
    }
  }
  return rows;
}
