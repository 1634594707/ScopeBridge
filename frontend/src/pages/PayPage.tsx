import { useEffect, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { AlertTriangle, ArrowRight, RefreshCw, ShieldCheck } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { readPortalToken } from "../lib/customerToken";
import { formatDateTime, formatMoney } from "../lib/format";
import { Button } from "../components/Button";
import { Card, CardHeader } from "../components/Card";
import { StatusPill } from "../components/StatusPill";

export default function PayPage() {
  const { paymentId = "" } = useParams();
  const [params] = useSearchParams();
  const token = readPortalToken();
  const returnedFromPaypal = params.get("paypal") === "return";
  const autoTried = useRef(false);

  const payment = useQuery({
    queryKey: ["payment", paymentId],
    queryFn: () => api.payment(paymentId),
    enabled: Boolean(paymentId) && Boolean(token),
    refetchInterval: (query) =>
      query.state.data?.status === "RECONCILING" ? 5000 : false,
  });

  const capture = useMutation({
    mutationFn: () => api.capturePayment(paymentId),
    onSuccess: () => payment.refetch(),
  });

  const portal = useQuery({
    queryKey: ["portal", token],
    queryFn: api.portal,
    enabled: payment.data?.status === "COMPLETED" && Boolean(token),
  });

  const status = payment.data?.status;
  useEffect(() => {
    if (!returnedFromPaypal || autoTried.current) return;
    if (status !== "AWAITING_APPROVAL") return;
    autoTried.current = true;
    capture.mutate();
  }, [returnedFromPaypal, status, capture]);

  if (!token) {
    return (
      <Shell
        eyebrow="Payment"
        title="Open your private brief link"
        body="This page needs the client link that was created with your brief. Open that link, then start the payment again."
      />
    );
  }

  if (payment.isLoading) {
    return <Shell eyebrow="Payment" title="Checking the payment" body="Reading the latest state." />;
  }

  if (payment.error) {
    const code = payment.error instanceof ApiError ? payment.error.status : 0;
    return (
      <Shell
        eyebrow="Payment"
        title={code === 401 ? "This link cannot see the payment" : "The payment could not be loaded"}
        body="Open the private brief link again. Payment state is only visible to the brief it belongs to."
      />
    );
  }

  const data = payment.data;
  if (!data) return null;

  const error = capture.error instanceof ApiError ? capture.error : null;
  const confirming = capture.isPending || data.status === "CAPTURING";
  const order = portal.data?.order;

  return (
    <div className="mx-auto max-w-[640px]">
      <Card className="px-6 py-7">
        <CardHeader
          eyebrow="PayPal sandbox"
          title={titleFor(data.status, returnedFromPaypal)}
          description={describe(data.status)}
        />

        <div className="mt-5 flex flex-wrap items-center gap-3 border-y border-line py-3">
          <StatusPill status={data.status} />
          <span className="numeric text-[13px] text-ink">
            {formatMoney(data.amount_minor, data.currency)}
          </span>
          {data.paypal_order_id ? (
            <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">
              {data.paypal_order_id}
            </span>
          ) : null}
        </div>

        {confirming ? (
          <p className="mt-5 flex items-center gap-2 text-[12px] leading-relaxed text-ink-muted">
            <span className="h-3 w-3 animate-spin rounded-full border border-pine border-t-transparent" />
            Confirming the payment with PayPal. Do not close this page.
          </p>
        ) : null}

        {data.status === "AWAITING_APPROVAL" && !confirming ? (
          <div className="mt-5 flex flex-col gap-3">
            {data.approve_url ? (
              <a href={data.approve_url} className="inline-flex w-fit">
                <Button icon={<ArrowRight size={15} />}>Continue to PayPal</Button>
              </a>
            ) : null}
            <p className="text-[12px] leading-relaxed text-ink-muted">
              Approve the payment in PayPal, then you will come back here automatically. Returning
              is not proof of payment — the studio's server confirms it with PayPal first.
            </p>
            {data.error_code === "not_approved" ? (
              <p className="text-[12px] leading-relaxed text-flag-warn">
                PayPal says this order is not approved yet. Approve it there first, then confirm
                again.
              </p>
            ) : null}
            {returnedFromPaypal ? (
              <Button
                variant="secondary"
                busy={capture.isPending}
                icon={<ShieldCheck size={15} />}
                onClick={() => capture.mutate()}
              >
                Confirm again
              </Button>
            ) : null}
          </div>
        ) : null}

        {data.status === "RECONCILING" ? (
          <div className="mt-5 flex flex-col gap-3">
            <p className="flex items-start gap-2 text-[12px] leading-relaxed text-flag-warn">
              <AlertTriangle size={14} className="mt-[2px] shrink-0" />
              PayPal has not confirmed the result yet. Nothing counts as paid until the payment is
              verified; this page checks again every few seconds.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                busy={payment.isFetching}
                icon={<RefreshCw size={15} />}
                onClick={() => payment.refetch()}
              >
                Check now
              </Button>
              <Link
                to={`/r/${token}`}
                className="text-[12px] text-ink-muted underline decoration-line underline-offset-4 hover:text-ink"
              >
                Back to your brief
              </Link>
            </div>
          </div>
        ) : null}

        {data.status === "COMPLETED" ? (
          <div className="mt-5 flex flex-col gap-4">
            <p className="flex items-start gap-2 text-[12px] leading-relaxed text-flag-good">
              <ShieldCheck size={14} className="mt-[2px] shrink-0" />
              Payment confirmed for {formatMoney(data.amount_minor, data.currency)}. The quote is
              now read-only and the order summary is stored with your brief.
            </p>

            {order ? (
              <dl className="flex flex-col divide-y divide-line/70 rounded-md border border-line bg-paper px-4 py-2">
                <Row label="PayPal order" value={order.order_id} />
                <Row label="Payment reference" value={order.capture_id} />
                <Row label="Paid by" value={order.payer_email || "sandbox buyer"} />
                <Row label="Confirmed" value={formatDateTime(order.captured_at)} />
              </dl>
            ) : null}

            <Link
              to={`/r/${token}`}
              className="inline-flex w-fit items-center gap-1.5 text-[12px] font-medium text-pine underline decoration-pine/30 underline-offset-4 hover:decoration-pine"
            >
              Back to your brief and order <ArrowRight size={13} />
            </Link>
          </div>
        ) : null}

        {data.status === "FAILED" ? (
          <div className="mt-5 flex flex-col gap-3">
            <p className="flex items-start gap-2 text-[12px] leading-relaxed text-flag-bad">
              <AlertTriangle size={14} className="mt-[2px] shrink-0" />
              This attempt did not go through ({data.error_code ?? "unknown"}). Nothing was charged.
            </p>
            <Link
              to={`/r/${token}`}
              className="text-[12px] font-medium text-pine underline underline-offset-4"
            >
              Start a new attempt from the brief
            </Link>
          </div>
        ) : null}

        {error ? (
          <p className="mt-4 text-[12px] leading-relaxed text-flag-bad">
            {error.code === "not_approved"
              ? "PayPal says the order is not approved yet. Approve it in PayPal, then confirm again."
              : error.message}
          </p>
        ) : null}
      </Card>
    </div>
  );
}

function Shell({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div className="mx-auto max-w-[560px] py-24">
      <span className="label">{eyebrow}</span>
      <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em]">{title}</h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-muted">{body}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2">
      <dt className="text-[11px] text-ink-faint">{label}</dt>
      <dd className="numeric text-[11px] text-ink">{value}</dd>
    </div>
  );
}

function titleFor(status: string, returned: boolean): string {
  switch (status) {
    case "AWAITING_APPROVAL":
      return returned ? "Confirming your payment" : "Approve the payment in PayPal";
    case "CAPTURING":
      return "Confirming your payment";
    case "RECONCILING":
      return "Verifying with PayPal";
    case "COMPLETED":
      return "Payment confirmed";
    case "FAILED":
      return "This attempt did not go through";
    default:
      return "Preparing the payment";
  }
}

function describe(status: string): string {
  switch (status) {
    case "AWAITING_APPROVAL":
      return "The order exists in the PayPal sandbox. Only the buyer can approve it.";
    case "CAPTURING":
      return "PayPal is processing the payment. This usually takes a few seconds.";
    case "RECONCILING":
      return "The result was unclear, so the studio checks the original order instead of guessing.";
    case "COMPLETED":
      return "PayPal confirmed the payment for the exact amount on this quote.";
    case "FAILED":
      return "PayPal declined or the order expired. The quote is unlocked again.";
    default:
      return "Creating the PayPal order for this quote.";
  }
}
