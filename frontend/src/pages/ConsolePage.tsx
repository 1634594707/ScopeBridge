import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUpRight, Plus } from "lucide-react";
import { api } from "../lib/api";
import { formatDate, formatDateTime } from "../lib/format";
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
      to={`/requirements/${brief.id}`}
      className="group grid grid-cols-1 gap-3 px-5 py-4 transition-colors duration-150 hover:bg-paper sm:grid-cols-[1.4fr_0.7fr_0.7fr_0.5fr_auto] sm:items-center"
    >
      <div className="flex flex-col gap-0.5">
        <span className="flex items-center gap-2 text-[14px] font-medium text-ink">
          {brief.client_name}
          <ArrowUpRight
            size={13}
            className="text-ink-faint opacity-0 transition-opacity duration-150 group-hover:opacity-100"
          />
        </span>
        <span className="text-[12px] text-ink-faint">{brief.client_business || "Independent"}</span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="label sm:hidden">Budget</span>
        <Money amountMinor={brief.budget_minor ?? 0} size="sm" />
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="label sm:hidden">Live by</span>
        <span className="text-[13px] text-ink">{formatDate(brief.deadline)}</span>
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
      </div>
    </Link>
  );
}

export default function ConsolePage() {
  const briefs = useQuery({ queryKey: ["requirements"], queryFn: api.requirements });

  const rows = briefs.data ?? [];
  const open = rows.filter((row) => row.status === "OPEN").length;
  const pendingAssets = rows.filter((row) => row.assets_ready === false).length;

  return (
    <div>
      <PageHeader
        eyebrow="Seller console"
        title="Every brief on the desk."
        description="Open a brief to read the original messages, price a scope against the published rules and issue a quote for review."
        actions={
          <Link to="/start">
            <Button icon={<Plus size={15} />}>New brief</Button>
          </Link>
        }
        meta={
          <>
            <span className="flex items-baseline gap-2">
              <span className="label">Open</span>
              <span className="numeric text-[14px] text-ink">{open}</span>
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Total</span>
              <span className="numeric text-[14px] text-ink">{rows.length}</span>
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Assets pending</span>
              <span className="numeric text-[14px] text-ink">{pendingAssets}</span>
            </span>
          </>
        }
      />

      {briefs.isLoading ? (
        <div className="py-16 text-sm text-ink-faint">Loading briefs…</div>
      ) : briefs.error ? (
        <div className="py-16 text-sm text-flag-bad">
          The console could not be loaded. Check that the API is running on port 8000.
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No briefs on the desk"
          body="Submit a client brief to see how it is read, priced and turned into a confirmable quote."
          action={
            <Link to="/start">
              <Button variant="secondary" size="sm">
                Open the intake form
              </Button>
            </Link>
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <div className="hidden grid-cols-[1.4fr_0.7fr_0.7fr_0.5fr_auto] gap-3 border-b border-line px-5 py-3 sm:grid">
            {["Client", "Budget", "Deadline", "Revision", "Activity"].map((column) => (
              <span key={column} className="label">
                {column}
              </span>
            ))}
          </div>
          <div className="divide-y divide-line">
            {rows.map((brief) => (
              <BriefRow key={brief.id} brief={brief} />
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
