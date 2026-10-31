import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUpRight, Trash2 } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatDate, formatDateTime, todayIso } from "../lib/format";
import { applyFilters, daysUntil, downloadBriefsCsv, useBriefFilters } from "../lib/briefFilters";
import { AttentionPanel } from "../components/AttentionPanel";
import { BriefToolbar, DeadlineBadge, StatCard } from "../components/BriefToolbar";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { RequirementPill } from "../components/StatusPill";
import type { RequirementSummary } from "../lib/types";

function DeleteControl({ brief }: { brief: RequirementSummary }) {
  const [confirming, setConfirming] = useState(false);
  const queryClient = useQueryClient();

  const remove = useMutation({
    mutationFn: () => api.deleteRequirement(brief.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["requirements"] }),
  });
  const error = remove.error instanceof ApiError ? remove.error : null;

  if (!confirming) {
    return (
      <button
        type="button"
        aria-label={`Delete the brief for ${brief.client_name}`}
        onClick={() => setConfirming(true)}
        className="cursor-pointer rounded-sm p-1.5 text-ink-faint transition-colors duration-150 hover:bg-flag-bad/5 hover:text-flag-bad"
      >
        <Trash2 size={14} />
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {remove.isPending ? (
        <span className="h-3 w-3 animate-spin rounded-full border border-pine border-t-transparent" />
      ) : (
        <>
          <Button
            variant="danger"
            size="sm"
            onClick={() => remove.mutate()}
            disabled={remove.isPending}
          >
            Delete
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
            Cancel
          </Button>
        </>
      )}
      {error ? (
        <span className="text-[11px] text-flag-bad">
          {error.code === "payment_completed" ? "Paid briefs cannot be deleted." : error.message}
        </span>
      ) : null}
    </div>
  );
}

function BriefRow({ brief }: { brief: RequirementSummary }) {
  return (
    <div className="grid grid-cols-1 gap-3 px-5 py-4 transition-colors duration-150 hover:bg-paper sm:grid-cols-[1.4fr_0.7fr_0.7fr_0.5fr_auto] sm:items-center">
      <Link
        to={`/requirements/${brief.id}`}
        className="group flex flex-col gap-0.5"
      >
        <span className="flex items-center gap-2 text-[14px] font-medium text-ink">
          {brief.client_name}
          <ArrowUpRight
            size={13}
            className="text-ink-faint opacity-0 transition-opacity duration-150 group-hover:opacity-100"
          />
        </span>
        <span className="text-[12px] text-ink-faint">{brief.client_business || "Independent"}</span>
      </Link>
      <div className="flex flex-col gap-0.5">
        <span className="label sm:hidden">Budget</span>
        <Money amountMinor={brief.budget_minor ?? 0} size="sm" />
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="label sm:hidden">Live by</span>
        <span className="text-[13px] text-ink">{formatDate(brief.deadline)}</span>
        <DeadlineBadge deadline={brief.deadline} status={brief.status} />
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="label sm:hidden">Rev</span>
        <span className="font-mono text-[13px] text-ink">{brief.revision}</span>
      </div>
      <div className="flex items-center justify-between gap-3 sm:justify-end">
        <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">
          {formatDateTime(brief.updated_at)}
        </span>
        <RequirementPill status={brief.status} />
        {brief.deletable === false ? null : <DeleteControl brief={brief} />}
      </div>
    </div>
  );
}

export default function ConsolePage() {
  const briefs = useQuery({ queryKey: ["requirements"], queryFn: api.requirements });
  const { filters, update, reset, active } = useBriefFilters();

  const rows = briefs.data ?? [];
  const visible = applyFilters(rows, filters);
  const open = rows.filter((row) => row.status === "OPEN").length;
  const pendingAssets = rows.filter((row) => row.status === "OPEN" && row.assets_ready === false).length;
  const dueSoon = rows.filter((row) => {
    const days = daysUntil(row.deadline);
    return row.status === "OPEN" && days !== null && days <= 7;
  }).length;

  return (
    <div>
      <PageHeader
        eyebrow="Seller console"
        title="Every brief on the desk."
        description="Open a brief to read the original messages, price a scope against the published rules and issue a quote for review."
        actions={
          <span className="hidden items-center gap-1.5 font-mono text-[11px] text-ink-faint sm:flex">
            <kbd className="rounded-sm border border-line bg-paper-card px-1.5 py-0.5">ctrl k</kbd> jump to a brief
          </span>
        }
      />

      {briefs.data ? (
        <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="Open"
            value={open}
            hint="Waiting on pricing or payment"
            onClick={() => update({ status: filters.status === "OPEN" ? "all" : "OPEN" })}
            selected={filters.status === "OPEN"}
          />
          <StatCard
            label="Due within 7 days"
            value={dueSoon}
            hint="Open briefs, by deadline"
            tone={dueSoon > 0 ? "warn" : "default"}
            onClick={() => update({ status: "OPEN", sort: "deadline" })}
            selected={filters.status === "OPEN" && filters.sort === "deadline"}
          />
          <StatCard
            label="Assets pending"
            value={pendingAssets}
            hint="Open briefs without assets"
            onClick={() => update({ assets: filters.assets === "pending" ? "all" : "pending" })}
            selected={filters.assets === "pending"}
          />
          <StatCard label="Total" value={rows.length} hint="Every brief on the desk" />
        </div>
      ) : null}

      <div className="mb-6">
        <AttentionPanel />
      </div>

      {briefs.isLoading ? (
        <div className="py-16 text-sm text-ink-faint">Loading briefs…</div>
      ) : briefs.error ? (
        <div className="py-16 text-sm text-flag-bad">
          The console could not be loaded. Check that the API is running on port 8000.
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No briefs on the desk"
          body="Clients submit briefs from their own account; when one arrives it lands here for pricing."
        />
      ) : (
        <>
          <BriefToolbar
            filters={filters}
            onChange={update}
            onReset={reset}
            active={active}
            shown={visible.length}
            total={rows.length}
            onExport={() => downloadBriefsCsv(visible, `scopebridge-briefs-${todayIso()}.csv`)}
          />
          {visible.length === 0 ? (
            <EmptyState
              title="No brief matches these filters"
              body="Clear the search or the filters to see every brief on the desk."
              action={
                <Button variant="secondary" size="sm" onClick={reset}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <Card className="overflow-hidden">
              <div className="hidden grid-cols-[1.4fr_0.7fr_0.7fr_0.5fr_auto] gap-3 border-b border-line bg-paper/60 px-5 py-3 sm:grid">
                {["Client", "Budget", "Deadline", "Revision", "Activity"].map((column) => (
                  <span key={column} className="label">
                    {column}
                  </span>
                ))}
              </div>
              <div className="divide-y divide-line">
                {visible.map((brief) => (
                  <BriefRow key={brief.id} brief={brief} />
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
