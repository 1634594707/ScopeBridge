import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUpRight, Plus } from "lucide-react";
import { api } from "../lib/api";
import { formatDate, formatDateTime } from "../lib/format";
import { applyFilters, useBriefFilters } from "../lib/briefFilters";
import { BriefToolbar, DeadlineBadge, StatCard } from "../components/BriefToolbar";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { RequirementPill } from "../components/StatusPill";
import type { RequirementSummary } from "../lib/types";

function BriefRow({ brief }: { brief: RequirementSummary }) {
  return (
    <Link
      to={`/briefs/${brief.id}`}
      className="group grid grid-cols-1 gap-3 px-5 py-4 transition-colors duration-150 hover:bg-paper sm:grid-cols-[1.4fr_0.7fr_0.7fr_auto] sm:items-center"
    >
      <div className="flex flex-col gap-0.5">
        <span className="flex items-center gap-2 text-[14px] font-medium text-ink">
          {brief.client_business || brief.client_name}
          <ArrowUpRight
            size={13}
            className="text-ink-faint opacity-0 transition-opacity duration-150 group-hover:opacity-100"
          />
        </span>
        <span className="text-[12px] text-ink-faint">
          {brief.client_business ? brief.client_name : "Submitted by you"}
        </span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="label sm:hidden">Budget</span>
        <Money amountMinor={brief.budget_minor ?? 0} size="sm" />
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="label sm:hidden">Live by</span>
        <span className="text-[13px] text-ink">{formatDate(brief.deadline)}</span>
        <DeadlineBadge deadline={brief.deadline} status={brief.status} />
      </div>
      <div className="flex items-center justify-between gap-3 sm:justify-end">
        <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">
          {formatDateTime(brief.updated_at)}
        </span>
        <RequirementPill status={brief.status} />
      </div>
    </Link>
  );
}

export default function BriefsPage() {
  const briefs = useQuery({ queryKey: ["briefs"], queryFn: api.clientBriefs });
  const { filters, update, reset, active } = useBriefFilters();

  const rows = briefs.data ?? [];
  const visible = applyFilters(rows, filters);
  const open = rows.filter((row) => row.status === "OPEN").length;

  return (
    <div>
      <PageHeader
        eyebrow="Your briefs"
        title="Everything you have on the desk."
        description="Open a brief to compare scope options, confirm the reviewed quote and follow the payment through."
        actions={
          <Link to="/start">
            <Button icon={<Plus size={15} />}>New brief</Button>
          </Link>
        }
      />

      {briefs.isLoading ? (
        <div className="py-16 text-sm text-ink-faint">Loading your briefs…</div>
      ) : briefs.error ? (
        <div className="py-16 text-sm text-flag-bad">
          Your briefs could not be loaded. Check that the API is running on port 8000.
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No briefs yet"
          body="Describe the work you need in plain language. The studio answers with priced scope options you can actually choose between."
          action={
            <Link to="/start">
              <Button variant="secondary" size="sm">
                Start with a brief
              </Button>
            </Link>
          }
        />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-3">
            <StatCard
              label="Open"
              value={open}
              hint="Still being priced or paid"
              onClick={() => update({ status: filters.status === "OPEN" ? "all" : "OPEN" })}
              selected={filters.status === "OPEN"}
            />
            <StatCard
              label="Closed"
              value={rows.filter((row) => row.status === "CLOSED").length}
              hint="Finished briefs"
              onClick={() => update({ status: filters.status === "CLOSED" ? "all" : "CLOSED" })}
              selected={filters.status === "CLOSED"}
            />
            <div className="col-span-2 flex flex-col justify-between gap-3 rounded-lg border border-pine/20 bg-pine-wash/70 px-4 py-4 lg:col-span-1">
              <span className="label text-pine-deep">What happens next</span>
              <p className="text-[12.5px] leading-relaxed text-pine-deep">
                Open a brief to compare the priced options, confirm the reviewed quote and pay that
                exact version.
              </p>
            </div>
          </div>
          <BriefToolbar
            filters={filters}
            onChange={update}
            onReset={reset}
            active={active}
            shown={visible.length}
            total={rows.length}
          />
          {visible.length === 0 ? (
            <EmptyState
              title="No brief matches these filters"
              body="Clear the search or the filters to see all of your briefs."
              action={
                <Button variant="secondary" size="sm" onClick={reset}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <Card className="overflow-hidden">
              <div className="hidden grid-cols-[1.4fr_0.7fr_0.7fr_auto] gap-3 border-b border-line bg-paper/60 px-5 py-3 sm:grid">
                {["Brief", "Budget", "Live by", "Status"].map((column) => (
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
