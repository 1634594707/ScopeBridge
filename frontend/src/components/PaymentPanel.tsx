import { Link } from "react-router-dom";
import { CheckCircle2, CreditCard, ShieldCheck } from "lucide-react";
import type { OrderSnapshot, Payment, Quote } from "../lib/types";
import { formatDateTime, formatMoney } from "../lib/format";
import { Button } from "./Button";
import { Card, CardHeader } from "./Card";
import { StatusPill } from "./StatusPill";

interface PaymentPanelProps {
  quote: Quote;
  payment?: Payment;
  order?: OrderSnapshot | null;
  onStart: () => void;
  busy: boolean;
  error: string;
}

export function PaymentPanel({ quote, payment, order, onStart, busy, error }: PaymentPanelProps) {
  const label = formatMoney(quote.total_minor, quote.currency);

  if (quote.status === "PAID" && order) {
    return (
      <Card className="px-5 py-5">
        <CardHeader
          eyebrow="Paid"
          title="This version is settled"
          description="PayPal confirmed the capture. The snapshot below is frozen and cannot be edited."
        />
        <dl className="mt-4 flex flex-col divide-y divide-line/70">
          <Row label="Amount" value={label} />
          <Row label="PayPal order" value={order.order_id} mono />
          <Row label="Capture" value={order.capture_id} mono />
          <Row label="Payer" value={order.payer_email || "sandbox buyer"} />
          <Row label="Captured" value={formatDateTime(order.captured_at)} />
          <Row label="Line items" value={`${order.items.length} locked`} />
        </dl>
        <p className="mt-4 flex items-start gap-2 text-[11px] leading-relaxed text-ink-faint">
          <ShieldCheck size={13} className="mt-[2px] shrink-0" />
          Amount and currency were verified against this quote before the snapshot was written.
        </p>
      </Card>
    );
  }

  if (quote.status === "PAYMENT_LOCKED" || quote.status === "PAID") {
    return (
      <Card className="px-5 py-5">
        <CardHeader
          eyebrow="Payment in progress"
          title="The version is locked"
          description="Nothing on this quote can change while PayPal is settling the payment."
        />
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <StatusPill status={payment?.status ?? "RECONCILING"} />
          <span className="font-mono text-[11px] text-ink-faint">
            {payment?.paypal_order_id ?? "no order id yet"}
          </span>
        </div>
        {payment ? (
          <Link
            to={`/pay/${payment.id}`}
            className="mt-4 inline-flex text-[12px] font-medium text-pine underline decoration-pine/30 underline-offset-4 hover:decoration-pine"
          >
            Open payment status
          </Link>
        ) : null}
      </Card>
    );
  }

  return (
    <Card className="px-5 py-5">
      <CardHeader
        eyebrow="Payment"
        title={`Pay ${label} in the PayPal sandbox`}
        description="The sandbox mimics a real PayPal checkout. No real card is charged and no card details reach this app."
      />
      {payment?.status === "FAILED" ? (
        <p className="mt-3 text-[12px] leading-relaxed text-flag-bad">
          The last attempt failed ({payment.error_code ?? "unknown"}). Nothing was charged; you can
          try again.
        </p>
      ) : null}
      {error ? <p className="mt-3 text-[12px] leading-relaxed text-flag-bad">{error}</p> : null}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button busy={busy} icon={<CreditCard size={15} />} onClick={onStart}>
          Continue to PayPal
        </Button>
        <span className="flex items-center gap-1.5 text-[11px] text-ink-faint">
          <CheckCircle2 size={13} />
          Amount is read from the confirmed quote on the server
        </span>
      </div>
    </Card>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2">
      <dt className="text-[11px] text-ink-faint">{label}</dt>
      <dd className={mono ? "numeric text-[12px] text-ink" : "text-[12px] text-ink"}>{value}</dd>
    </div>
  );
}
