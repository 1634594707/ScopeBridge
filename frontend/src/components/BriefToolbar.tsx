import type { ReactNode } from "react";
import { Download, Search, X } from "lucide-react";
import { cn } from "../lib/cn";
import { daysUntil, type AssetsFilter, type BriefFilters, type SortKey, type StatusFilter } from "../lib/briefFilters";

const statusOptions: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "OPEN", label: "Open" },
  { value: "CLOSED", label: "Closed" },
];

const assetOptions: { value: AssetsFilter; label: string }[] = [
  { value: "all", label: "Any assets" },
  { value: "pending", label: "Assets pending" },
  { value: "ready", label: "Assets ready" },
];

const sortOptions: { value: SortKey; label: string }[] = [
  { value: "updated", label: "Recent activity" },
  { value: "deadline", label: "Nearest deadline" },
  { value: "budget", label: "Largest budget" },
  { value: "name", label: "Name A–Z" },
];

export function BriefToolbar({
  filters,
  onChange,
  onReset,
  active,
  shown,
  total,
  onExport,
}: {
  filters: BriefFilters;
  onChange: (patch: Partial<BriefFilters>) => void;
  onReset: () => void;
  active: boolean;
  shown: number;
  total: number;
  onExport?: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 pb-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <label className="relative flex-1">
          <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            value={filters.q}
            onChange={(event) => onChange({ q: event.target.value })}
            placeholder="Search by client or business"
            aria-label="Search briefs"
            className="input-base pl-9"
          />
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <div role="group" aria-label="Status" className="flex rounded-md border border-line bg-paper-card p-0.5">
            {statusOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onChange({ status: option.value })}
                aria-pressed={filters.status === option.value}
                className={cn(
                  "cursor-pointer rounded-[5px] px-3 py-1.5 text-[12px] transition-colors duration-150",
                  filters.status === option.value
                    ? "bg-pine text-ink-invert"
                    : "text-ink-muted hover:text-ink",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          <select
            value={filters.assets}
            onChange={(event) => onChange({ assets: event.target.value as AssetsFilter })}
            aria-label="Assets"
            className="input-base h-9 w-auto cursor-pointer pr-8 text-[12px]"
          >
            {assetOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            value={filters.sort}
            onChange={(event) => onChange({ sort: event.target.value as SortKey })}
            aria-label="Sort"
            className="input-base h-9 w-auto cursor-pointer pr-8 text-[12px]"
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {onExport ? (
            <button
              type="button"
              onClick={onExport}
              disabled={shown === 0}
              className="inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-md border border-line bg-paper-card px-3 text-[12px] text-ink-muted transition-colors hover:border-ink/25 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download size={13} /> CSV
            </button>
          ) : null}
        </div>
      </div>
      <div className="flex items-center gap-3 font-mono text-[11px] text-ink-faint">
        <span>
          {shown === total ? `${total} briefs` : `${shown} of ${total} briefs`}
        </span>
        {active ? (
          <button
            type="button"
            onClick={onReset}
            className="inline-flex cursor-pointer items-center gap-1 text-pine underline-offset-4 hover:underline"
          >
            <X size={11} /> clear filters
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function DeadlineBadge({ deadline, status }: { deadline: string | null; status: string }) {
  const days = daysUntil(deadline);
  if (days === null || status !== "OPEN" || days > 7) return null;
  const tone =
    days < 0
      ? "border-flag-bad/30 bg-flag-bad/5 text-flag-bad"
      : days <= 3
        ? "border-flag-warn/30 bg-flag-warn/10 text-flag-warn"
        : "border-line bg-paper-deep text-ink-muted";
  const text = days < 0 ? `${-days}d overdue` : days === 0 ? "due today" : `in ${days}d`;
  return (
    <span className={cn("inline-flex w-fit rounded-sm border px-1.5 py-[1px] font-mono text-[10px]", tone)}>{text}</span>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  onClick,
  selected,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "warn" | "bad";
  onClick?: () => void;
  selected?: boolean;
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      aria-pressed={onClick ? selected : undefined}
      className={cn(
        "surface flex flex-col gap-1 px-4 py-4 text-left transition-all duration-150",
        onClick && "cursor-pointer hover:shadow-panel",
        selected && "border-pine/50 ring-2 ring-pine/10",
      )}
    >
      <span className="label">{label}</span>
      <span
        className={cn(
          "numeric text-[28px] font-semibold leading-none tracking-[-0.03em]",
          tone === "warn" ? "text-flag-warn" : tone === "bad" ? "text-flag-bad" : "text-ink",
        )}
      >
        {value}
      </span>
      {hint ? <span className="text-[11.5px] text-ink-faint">{hint}</span> : null}
    </Tag>
  );
}
