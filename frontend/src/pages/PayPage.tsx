import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { AlertTriangle, ArrowRight, RefreshCw, ShieldCheck } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatDateTime, formatMoney } from "../lib/format";
import { Button } from "../components/Button";
import { Card, CardHeader } from "../components/Card";
import { StatusPill } from "../components/StatusPill";

export default function PayPage() {
  const { paymentId = "" } = useParams();
  const [params] = useSearchParams();
  // PayPal appends token + PayerID on the approve-return navigation. token alone
  // also appears on buyer cancel, so PayerID is what proves the buyer came back
  // from approving; without it this page must not auto-capture.
  const returnedFromPaypal = params.has("token") && params.has("PayerID");
  const autoTried = useRef(false);

  const payment = useQuery({
    queryKey: ["payment", paymentId],
    queryFn: () => api.payment(paymentId),
    enabled: Boolean(paymentId),
    refetchInterval: (query) =>
      ["CREATING", "CAPTURING", "RECONCILING"].includes(query.state.data?.status ?? "")
        ? 5000
        : false,
  });

  const queryClient = useQueryClient();
  const capture = useMutation({
    mutationFn: () => api.capturePayment(paymentId),
    onSuccess: () => {
      // The snapshot is written in the same transaction as COMPLETED; refetching the
      // payment alone leaves the order summary stale until a manual reload.
      payment.refetch();
      queryClient.invalidateQueries({ queryKey: ["portal"] });
    },
  });

  const requirementId = payment.data?.requirement_id ?? null;

  const portal = useQuery({
    queryKey: ["portal", requirementId],
    queryFn: () => api.portal(requirementId as string),
    enabled: Boolean(requirementId),
  });

  const status = payment.data?.status;
  useEffect(() => {
    if (!returnedFromPaypal || autoTried.current) return;
    if (status !== "AWAITING_APPROVAL") return;
    autoTried.current = true;
    capture.mutate();
  }, [returnedFromPaypal, status, capture]);

  if (payment.isLoading) {
    return <Shell eyebrow="Payment" title="Checking the payment" body="Reading the latest state." />;
  }

  if (payment.error) {
    const status = payment.error instanceof ApiError ? payment.error.status : 0;
    return (
      <Shell
        eyebrow="Payment"
        title={status === 404 ? "This payment is not on your account" : "The payment could not be loaded"}
        body="Open it again from your briefs list. Payment state is only visible to the account that owns the brief."
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

        {["CREATING", "CAPTURING", "RECONCILING"].includes(data.status) ? (
          <div className="mt-5 flex flex-col gap-3">
            <p className="flex items-start gap-2 text-[12px] leading-relaxed text-flag-warn">
              <AlertTriangle size={14} className="mt-[2px] shrink-0" />
              {data.status === "RECONCILING"
                ? "PayPal has not confirmed the result yet. Nothing counts as paid until the payment is verified."
                : "The server is waiting for a PayPal result. If the process stops, this attempt is parked for verification."}{" "}
              This page checks again every few seconds.
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
                to={requirementId ? `/briefs/${requirementId}` : "/briefs"}
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
              to={requirementId ? `/briefs/${requirementId}` : "/briefs"}
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
              to={requirementId ? `/briefs/${requirementId}` : "/briefs"}
              className="text-[12px] font-medium text-pine underline underline-offset-4"
            >
              Start a new attempt from the brief
            </Link>
          </div>
        ) : null}

        {data.status === "ABANDONED" ? (
          <div className="mt-5 flex flex-col gap-3">
            <p className="flex items-start gap-2 text-[12px] leading-relaxed text-ink-muted">
              <AlertTriangle size={14} className="mt-[2px] shrink-0" />
              This attempt was closed after a PayPal check. Nothing was charged for it.
            </p>
            <Link
              to={requirementId ? `/briefs/${requirementId}` : "/briefs"}
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
    case "CREATING":
      return "Preparing the PayPal order";
    case "CAPTURING":
      return "Confirming your payment";
    case "RECONCILING":
      return "Verifying with PayPal";
    case "COMPLETED":
      return "Payment confirmed";
    case "FAILED":
      return "This attempt did not go through";
    case "ABANDONED":
      return "This attempt was closed";
    default:
      return "Preparing the payment";
  }
}

function describe(status: string): string {
  switch (status) {
    case "AWAITING_APPROVAL":
      return "The order exists in the PayPal sandbox. Only the buyer can approve it.";
    case "CREATING":
      return "The server is creating the PayPal order. If it does not receive an order id, the attempt is parked for verification.";
    case "CAPTURING":
      return "PayPal is processing the payment. This usually takes a few seconds.";
    case "RECONCILING":
      return "The result was unclear, so the studio checks the original order instead of guessing.";
    case "COMPLETED":
      return "PayPal confirmed the payment for the exact amount on this quote.";
    case "FAILED":
      return "PayPal declined or the order expired. The quote is unlocked again.";
    case "ABANDONED":
      return "The studio checked PayPal and closed this attempt; the quote is unlocked again.";
    default:
      return "Creating the PayPal order for this quote.";
  }
}
