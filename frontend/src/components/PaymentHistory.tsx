import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatDateTime, formatMoney } from "../lib/format";
import { Button } from "./Button";
import { Card } from "./Card";
import { Money } from "./Money";
import { StatusPill } from "./StatusPill";

export function PaymentHistory({ requirementId }: { requirementId: string }) {
  const queryClient = useQueryClient();
  const payments = useQuery({
    queryKey: ["payments", requirementId],
    queryFn: () => api.requirementPayments(requirementId),
  });
  const order = useQuery({
    queryKey: ["order", requirementId],
    queryFn: () => api.requirementOrder(requirementId),
  });

  const reconcile = useMutation({
    mutationFn: (paymentId: string) => api.reconcilePayment(paymentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments", requirementId] });
      queryClient.invalidateQueries({ queryKey: ["order", requirementId] });
      queryClient.invalidateQueries({ queryKey: ["quotes", requirementId] });
    },
  });

  const rows = payments.data ?? [];
  const error = reconcile.error instanceof ApiError ? reconcile.error.message : "";
  const snapshot = order.data?.order ?? null;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <span className="label">Payments</span>
        <span className="font-mono text-[10px] text-ink-faint">{rows.length}</span>
      </div>

      {rows.length === 0 ? (
        <p className="px-5 py-5 text-[13px] text-ink-muted">
          No payment attempt yet. The client starts one from their private link after confirming a
          quote.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((payment) => (
            <li key={payment.id} className="flex flex-col gap-2 px-5 py-3">
              <div className="flex items-center justify-between gap-4">
                <span className="font-mono text-[11px] text-ink-faint">
                  {payment.paypal_order_id ?? "order pending"}
                </span>
                <span className="flex items-center gap-3">
                  <Money amountMinor={payment.amount_minor} size="sm" tone="muted" />
                  <StatusPill status={payment.status} />
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] text-ink-faint">
                  started {formatDateTime(payment.created_at)}
                  {payment.error_code ? ` · ${payment.error_code}` : ""}
                </span>
                {payment.status === "RECONCILING" ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    busy={reconcile.isPending}
                    icon={<RefreshCw size={13} />}
                    onClick={() => reconcile.mutate(payment.id)}
                  >
                    Verify with PayPal
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      {snapshot ? (
        <div className="border-t border-line bg-paper/60 px-5 py-4">
          <div className="flex items-baseline justify-between gap-3">
            <span className="label">Order snapshot</span>
            <span className="numeric text-[12px] text-ink">
              {formatMoney(snapshot.amount_minor, snapshot.currency)}
            </span>
          </div>
          <dl className="mt-3 flex flex-col gap-1.5">
            <SnapshotRow label="Capture" value={snapshot.capture_id} />
            <SnapshotRow label="Payer" value={snapshot.payer_email || "sandbox buyer"} />
            <SnapshotRow label="Captured" value={formatDateTime(snapshot.captured_at)} />
          </dl>
        </div>
      ) : null}

      {error ? <p className="px-5 py-3 text-[12px] text-flag-bad">{error}</p> : null}
    </Card>
  );
}

function SnapshotRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-[11px] text-ink-faint">{label}</dt>
      <dd className="numeric text-[11px] text-ink">{value}</dd>
    </div>
  );
}
