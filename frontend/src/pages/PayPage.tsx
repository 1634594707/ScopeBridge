import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { AlertTriangle, ExternalLink, RefreshCw, ShieldCheck } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { readPortalToken } from "../lib/customerToken";
import { formatMoney } from "../lib/format";
import { Button } from "../components/Button";
import { Card, CardHeader } from "../components/Card";
import { StatusPill } from "../components/StatusPill";

export default function PayPage() {
  const { paymentId = "" } = useParams();
  const token = readPortalToken();

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
    return (
      <Shell
        eyebrow="Payment"
        title="Checking the payment"
        body="Reading the latest state from the studio's server."
      />
    );
  }

  if (payment.error) {
    const status = payment.error instanceof ApiError ? payment.error.status : 0;
    return (
      <Shell
        eyebrow="Payment"
        title={status === 401 ? "This link cannot see the payment" : "The payment could not be loaded"}
        body="Open the private brief link again. Payment state is only visible to the brief it belongs to."
      />
    );
  }

  const data = payment.data;
  if (!data) {
    return null;
  }

  const error = capture.error instanceof ApiError ? capture.error : null;

  return (
    <div className="mx-auto max-w-[640px]">
      <Card className="px-6 py-7">
        <CardHeader
          eyebrow="PayPal sandbox"
          title={titleFor(data.status)}
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

        {data.status === "AWAITING_APPROVAL" ? (
          <div className="mt-5 flex flex-col gap-3">
            {data.approve_url ? (
              <a href={data.approve_url} className="inline-flex">
                <Button icon={<ExternalLink size={15} />}>Approve in PayPal</Button>
              </a>
            ) : null}
            <p className="text-[12px] leading-relaxed text-ink-muted">
              Approve the payment in PayPal, then come back here. Returning from PayPal is not proof
              of payment — the studio's server has to capture and verify the order.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                busy={capture.isPending}
                icon={<ShieldCheck size={15} />}
                onClick={() => capture.mutate()}
              >
                I approved — capture now
              </Button>
              <a
                href="/"
                className="text-[11px] text-ink-faint underline decoration-line underline-offset-4 hover:text-ink"
              >
                Leave this page
              </a>
            </div>
          </div>
        ) : null}

        {data.status === "RECONCILING" ? (
          <div className="mt-5 flex flex-col gap-3">
            <p className="flex items-start gap-2 text-[12px] leading-relaxed text-flag-warn">
              <AlertTriangle size={14} className="mt-[2px] shrink-0" />
              PayPal has not confirmed the outcome yet. Nothing here counts as paid until the
              capture is verified; the studio can retry the check from the console.
            </p>
            <Button
              variant="secondary"
              busy={payment.isFetching}
              icon={<RefreshCw size={15} />}
              onClick={() => payment.refetch()}
            >
              Check again
            </Button>
          </div>
        ) : null}

        {data.status === "COMPLETED" ? (
          <div className="mt-5 flex flex-col gap-3">
            <p className="flex items-start gap-2 text-[12px] leading-relaxed text-flag-good">
              <ShieldCheck size={14} className="mt-[2px] shrink-0" />
              Capture verified: {formatMoney(data.amount_minor, data.currency)}. The order snapshot
              is now read-only.
            </p>
            <a href="/" className="text-[12px] font-medium text-pine underline underline-offset-4">
              Back to the studio
            </a>
          </div>
        ) : null}

        {data.status === "FAILED" ? (
          <div className="mt-5 flex flex-col gap-3">
            <p className="flex items-start gap-2 text-[12px] leading-relaxed text-flag-bad">
              <AlertTriangle size={14} className="mt-[2px] shrink-0" />
              This attempt failed ({data.error_code ?? "unknown"}). Nothing was charged. Open your
              brief again to start a new attempt.
            </p>
          </div>
        ) : null}

        {error ? (
          <p className="mt-4 text-[12px] leading-relaxed text-flag-bad">{error.message}</p>
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

function titleFor(status: string): string {
  switch (status) {
    case "AWAITING_APPROVAL":
      return "Approve the payment in PayPal";
    case "CAPTURING":
      return "Capturing the payment";
    case "RECONCILING":
      return "Verifying with PayPal";
    case "COMPLETED":
      return "Payment captured";
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
      return "PayPal is processing the capture. Do not close this page.";
    case "RECONCILING":
      return "The capture response was unclear, so the studio checks the original order instead of guessing.";
    case "COMPLETED":
      return "PayPal confirmed the capture for the exact amount on this quote.";
    case "FAILED":
      return "PayPal declined or the order expired. The quote is unlocked again.";
    default:
      return "Creating the PayPal order for this quote.";
  }
}
