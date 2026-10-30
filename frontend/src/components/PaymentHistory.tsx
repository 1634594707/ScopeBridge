import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, RotateCcw, XCircle } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatDateTime, formatMoney } from "../lib/format";
import { Button } from "./Button";
import { Card } from "./Card";
import { Field, TextArea } from "./Field";
import { Money } from "./Money";
import { StatusPill } from "./StatusPill";

export function PaymentHistory({ requirementId }: { requirementId: string }) {
  const queryClient = useQueryClient();
  const [closingId, setClosingId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  const payments = useQuery({
    queryKey: ["payments", requirementId],
    queryFn: () => api.requirementPayments(requirementId),
  });
  const order = useQuery({
    queryKey: ["order", requirementId],
    queryFn: () => api.requirementOrder(requirementId),
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["payments", requirementId] });
    queryClient.invalidateQueries({ queryKey: ["order", requirementId] });
    queryClient.invalidateQueries({ queryKey: ["quotes", requirementId] });
  };

  const reconcile = useMutation({
    mutationFn: (paymentId: string) => api.reconcilePayment(paymentId),
    onSuccess: refresh,
  });
  const retry = useMutation({
    mutationFn: (paymentId: string) => api.retryCreatePayment(paymentId),
    onSuccess: refresh,
  });
  const close = useMutation({
    mutationFn: (paymentId: string) => api.closePayment(paymentId, note.trim()),
    onSuccess: () => {
      setClosingId(null);
      setNote("");
      setError("");
      refresh();
    },
    onError: (cause) => {
      setError(cause instanceof ApiError ? cause.message : "The attempt could not be closed.");
    },
  });

  const rows = payments.data ?? [];
  const snapshot = order.data?.order ?? null;
  const busy = reconcile.isPending || retry.isPending || close.isPending;

  const startClosing = (paymentId: string) => {
    setClosingId(paymentId);
    setNote("");
    setError("");
  };

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
          {rows.map((payment) => {
            const needsRetry = payment.status === "RECONCILING" && !payment.paypal_order_id;
            const canClose = ["RECONCILING", "FAILED"].includes(payment.status);
            return (
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

                <div className="flex items-start justify-between gap-3">
                  <span className="text-[11px] leading-relaxed text-ink-faint">
                    started {formatDateTime(payment.created_at)}
                    {payment.error_code ? ` · ${payment.error_code}` : ""}
                    {payment.retry_count > 0 ? ` · retried ${payment.retry_count}x` : ""}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    {needsRetry ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        busy={retry.isPending}
                        icon={<RotateCcw size={13} />}
                        onClick={() => retry.mutate(payment.id)}
                      >
                        Retry create
                      </Button>
                    ) : null}
                    {payment.status === "RECONCILING" && payment.paypal_order_id ? (
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
                    {canClose ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        icon={<XCircle size={13} />}
                        onClick={() => startClosing(payment.id)}
                      >
                        Close
                      </Button>
                    ) : null}
                  </span>
                </div>

                {payment.resolution_note ? (
                  <p className="text-[11px] leading-relaxed text-ink-faint">
                    closed by hand · {payment.resolution_note}
                  </p>
                ) : null}

                {closingId === payment.id ? (
                  <div className="flex flex-col gap-2 rounded-md border border-line bg-paper px-3 py-3">
                    <p className="text-[11px] leading-relaxed text-ink-muted">
                      Only close this attempt after checking the PayPal sandbox dashboard and
                      confirming no order was created. The quote unlocks; nothing is refunded
                      because nothing was charged.
                    </p>
                    <Field
                      label="What did you check?"
                      htmlFor={`close-note-${payment.id}`}
                      error={error}
                    >
                      <TextArea
                        id={`close-note-${payment.id}`}
                        value={note}
                        rows={3}
                        placeholder="Checked PayPal activity for 30 Oct: no order for quote v2."
                        onChange={(event) => setNote(event.target.value)}
                      />
                    </Field>
                    <div className="flex items-center justify-between gap-3">
                      <Button
                        size="sm"
                        variant="danger"
                        busy={close.isPending}
                        disabled={note.trim().length < 10}
                        onClick={() => close.mutate(payment.id)}
                      >
                        Close attempt and unlock quote
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setClosingId(null)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
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
