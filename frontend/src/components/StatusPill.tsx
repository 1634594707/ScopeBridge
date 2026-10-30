import type { QuoteStatus } from "../lib/types";
import { cn } from "../lib/cn";

const styles: Record<QuoteStatus, string> = {
  DRAFT: "border-line bg-paper-deep text-ink-muted",
  REVIEWED: "border-flag-warn/30 bg-flag-warn/10 text-flag-warn",
  CONFIRMED: "border-pine/30 bg-pine-wash text-pine-deep",
  SUPERSEDED: "border-line bg-transparent text-ink-faint line-through decoration-1",
};

const labels: Record<QuoteStatus, string> = {
  DRAFT: "Draft",
  REVIEWED: "Reviewed",
  CONFIRMED: "Confirmed",
  SUPERSEDED: "Superseded",
};

export function StatusPill({ status, className }: { status: QuoteStatus; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-[3px] font-mono text-[10px] uppercase tracking-[0.14em]",
        styles[status],
        className,
      )}
    >
      {labels[status]}
    </span>
  );
}

const requirementTone: Record<string, string> = {
  OPEN: "border-pine/25 bg-pine-wash/60 text-pine-deep",
  CLOSED: "border-line bg-paper-deep text-ink-faint",
};

export function RequirementPill({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-[3px] font-mono text-[10px] uppercase tracking-[0.14em]",
        requirementTone[status] ?? requirementTone.OPEN,
      )}
    >
      {status.toLowerCase()}
    </span>
  );
}
