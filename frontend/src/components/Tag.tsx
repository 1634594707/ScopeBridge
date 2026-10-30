import type { ReactNode } from "react";
import { cn } from "../lib/cn";

export function RuleChip({ ruleRef, className }: { ruleRef: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm border border-line bg-paper px-1.5 py-[2px] font-mono text-[10px] tracking-[0.02em] text-ink-muted",
        className,
      )}
      title={`Priced by ${ruleRef}`}
    >
      {ruleRef}
    </span>
  );
}

export function SourceChip({
  revision,
  expanded,
  onClick,
  children,
}: {
  revision: number | null;
  expanded: boolean;
  onClick: () => void;
  children?: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex cursor-pointer items-center gap-1 rounded-sm border px-1.5 py-[2px] font-mono text-[10px] transition-colors duration-150",
        expanded
          ? "border-pine/40 bg-pine-wash text-pine-deep"
          : "border-line bg-paper text-ink-muted hover:border-ink/25 hover:text-ink",
      )}
      aria-expanded={expanded}
    >
      {revision === null ? "excluded" : `source · rev ${revision}`}
      {children}
    </button>
  );
}

export function Tag({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "good" | "warn" | "bad" }) {
  const tones = {
    neutral: "border-line text-ink-muted",
    good: "border-flag-good/30 bg-flag-good/5 text-flag-good",
    warn: "border-flag-warn/30 bg-flag-warn/5 text-flag-warn",
    bad: "border-flag-bad/30 bg-flag-bad/5 text-flag-bad",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-sm border px-2 py-[2px] text-[11px] font-medium",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}
