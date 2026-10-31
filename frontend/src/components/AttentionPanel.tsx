import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight } from "lucide-react";
import { api } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { Card } from "./Card";
import { EndpointNotice } from "./EndpointNotice";
import { Money } from "./Money";
import { StatusPill } from "./StatusPill";

/**
 * Seller-side list of payment attempts the server reports as needing a human:
 * RECONCILING (outcome unknown) and FAILED. The list and its amounts come from
 * the server as-is; the panel only links to the brief where recovery happens.
 */
export function AttentionPanel() {
  const attention = useQuery({ queryKey: ["payments", "attention"], queryFn: api.attentionPayments });

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
        <span className="flex items-center gap-2">
          <AlertTriangle size={14} className="text-flag-warn" />
          <span className="text-[14px] font-semibold text-ink">Payments that need you</span>
        </span>
        {attention.data ? (
          <span className="numeric text-[12px] text-ink-faint">{attention.data.length}</span>
        ) : null}
      </div>

      {attention.isLoading ? (
        <p className="px-5 py-5 text-[13px] text-ink-faint">Checking payment attempts…</p>
      ) : attention.error ? (
        <div className="p-4">
          <EndpointNotice
            error={attention.error}
            endpoint="GET /api/payments/attention"
            feature="The payment attention list"
          />
        </div>
      ) : (attention.data ?? []).length === 0 ? (
        <p className="px-5 py-5 text-[13px] text-ink-muted">
          No payment is waiting on verification or a decision.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {(attention.data ?? []).map((payment) => (
            <li key={payment.id}>
              <Link
                to={`/requirements/${payment.requirement_id}`}
                className="group flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 transition-colors hover:bg-paper"
              >
                <span className="flex flex-col gap-0.5">
                  <span className="flex items-center gap-1.5 text-[13px] font-medium text-ink">
                    {payment.client_business || payment.client_name}
                    <ArrowUpRight size={12} className="text-ink-faint opacity-0 transition-opacity group-hover:opacity-100" />
                  </span>
                  <span className="font-mono text-[10.5px] text-ink-faint">
                    quote v{payment.quote_number} · {payment.error_code ?? "no error code"} · {formatDateTime(payment.updated_at)}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <Money amountMinor={payment.amount_minor} currency={payment.currency} size="sm" />
                  <StatusPill status={payment.status} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
