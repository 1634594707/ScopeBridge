import { useSearchParams } from "react-router-dom";
import { formatMoney } from "./format";
import type { RequirementSummary } from "./types";

export type StatusFilter = "all" | "OPEN" | "CLOSED";
export type AssetsFilter = "all" | "pending" | "ready";
export type SortKey = "updated" | "deadline" | "name" | "budget";

export interface BriefFilters {
  q: string;
  status: StatusFilter;
  assets: AssetsFilter;
  sort: SortKey;
}

const statuses: StatusFilter[] = ["all", "OPEN", "CLOSED"];
const assetOptions: AssetsFilter[] = ["all", "pending", "ready"];
const sortKeys: SortKey[] = ["updated", "deadline", "name", "budget"];

function pick<T extends string>(value: string | null, allowed: T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

/** Filters live in the URL so a filtered view survives a reload and can be shared. */
export function useBriefFilters() {
  const [params, setParams] = useSearchParams();
  const filters: BriefFilters = {
    q: params.get("q") ?? "",
    status: pick(params.get("status"), statuses, "all"),
    assets: pick(params.get("assets"), assetOptions, "all"),
    sort: pick(params.get("sort"), sortKeys, "updated"),
  };

  const update = (patch: Partial<BriefFilters>) => {
    const next = { ...filters, ...patch };
    const out = new URLSearchParams();
    if (next.q.trim()) out.set("q", next.q);
    if (next.status !== "all") out.set("status", next.status);
    if (next.assets !== "all") out.set("assets", next.assets);
    if (next.sort !== "updated") out.set("sort", next.sort);
    setParams(out, { replace: true });
  };

  const active = filters.q.trim() !== "" || filters.status !== "all" || filters.assets !== "all";

  return { filters, update, reset: () => setParams(new URLSearchParams(), { replace: true }), active };
}

/** Whole days from today to the deadline date; negative means overdue. */
export function daysUntil(deadline: string | null): number | null {
  if (!deadline) return null;
  const [year, month, day] = deadline.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return null;
  const target = new Date(year, month - 1, day).getTime();
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  return Math.round((target - today) / 86_400_000);
}

export function applyFilters(rows: RequirementSummary[], filters: BriefFilters): RequirementSummary[] {
  const needle = filters.q.trim().toLowerCase();
  const filtered = rows.filter((row) => {
    if (filters.status !== "all" && row.status !== filters.status) return false;
    if (filters.assets === "pending" && row.assets_ready !== false) return false;
    if (filters.assets === "ready" && row.assets_ready !== true) return false;
    if (!needle) return true;
    return `${row.client_name} ${row.client_business}`.toLowerCase().includes(needle);
  });

  const byDeadline = (row: RequirementSummary) => daysUntil(row.deadline) ?? Number.POSITIVE_INFINITY;
  return [...filtered].sort((a, b) => {
    switch (filters.sort) {
      case "deadline":
        return byDeadline(a) - byDeadline(b);
      case "name":
        return (a.client_business || a.client_name).localeCompare(b.client_business || b.client_name);
      case "budget":
        return (b.budget_minor ?? -1) - (a.budget_minor ?? -1);
      default:
        return b.updated_at.localeCompare(a.updated_at);
    }
  });
}

function csvCell(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

/** Exports exactly what the server returned for the visible rows; no derived amounts. */
export function downloadBriefsCsv(rows: RequirementSummary[], filename: string) {
  const header = ["client", "business", "status", "revision", "budget", "deadline", "assets_ready", "messages", "updated_at"];
  const lines = rows.map((row) =>
    [
      row.client_name,
      row.client_business,
      row.status,
      String(row.revision),
      row.budget_minor === null ? "" : formatMoney(row.budget_minor),
      row.deadline ?? "",
      row.assets_ready === null ? "" : String(row.assets_ready),
      String(row.message_count),
      row.updated_at,
    ]
      .map(csvCell)
      .join(","),
  );
  const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
