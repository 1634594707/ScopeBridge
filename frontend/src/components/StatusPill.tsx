import { cn } from "../lib/cn";

const styles: Record<string, string> = {
  DRAFT: "border-line bg-paper-deep text-ink-muted",
  REVIEWED: "border-flag-warn/30 bg-flag-warn/10 text-flag-warn",
  CONFIRMED: "border-pine/30 bg-pine-wash text-pine-deep",
  PAYMENT_LOCKED: "border-pine/40 bg-pine-wash text-pine-deep",
  PAID: "border-flag-good/30 bg-flag-good/10 text-flag-good",
  SUPERSEDED: "border-line bg-transparent text-ink-faint line-through decoration-1",
  CREATING: "border-line bg-paper-deep text-ink-muted",
  AWAITING_APPROVAL: "border-flag-warn/30 bg-flag-warn/10 text-flag-warn",
  CAPTURING: "border-flag-warn/30 bg-flag-warn/10 text-flag-warn",
  RECONCILING: "border-flag-warn/40 bg-flag-warn/15 text-flag-warn",
  COMPLETED: "border-flag-good/30 bg-flag-good/10 text-flag-good",
  FAILED: "border-flag-bad/30 bg-flag-bad/5 text-flag-bad",
  ABANDONED: "border-line bg-transparent text-ink-faint line-through decoration-1",
};

const labels: Record<string, string> = {
  DRAFT: "Draft",
  REVIEWED: "Reviewed",
  CONFIRMED: "Confirmed",
  PAYMENT_LOCKED: "Payment locked",
  PAID: "Paid",
  SUPERSEDED: "Superseded",
  CREATING: "Creating",
  AWAITING_APPROVAL: "Awaiting approval",
  CAPTURING: "Capturing",
  RECONCILING: "Verifying",
  COMPLETED: "Completed",
  FAILED: "Failed",
  ABANDONED: "Closed by hand",
};

export function StatusPill({ status, className }: { status: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-sm border px-2 py-[3px] font-mono text-[10px] uppercase tracking-[0.14em]",
        styles[status] ?? "border-line bg-paper-deep text-ink-muted",
        className,
      )}
    >
      {labels[status] ?? status.replace(/_/g, " ").toLowerCase()}
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
