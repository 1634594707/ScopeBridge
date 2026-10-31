import { CircleHelp, KeyRound, Receipt, RefreshCw, ShieldCheck } from "lucide-react";
import { StatusPill } from "../../components/StatusPill";
import { Section, SectionHeading } from "./Section";

const flow = [
  {
    icon: KeyRound,
    title: "One attempt per key",
    body: "Starting a payment sends an idempotency key. A double click or a retried request reuses the same attempt instead of opening a second order.",
  },
  {
    icon: ShieldCheck,
    title: "Captured by the server",
    body: "Returning from PayPal does not mark anything paid. The server captures the order and checks amount, currency and payee against the locked quote.",
  },
  {
    icon: CircleHelp,
    title: "Unknown is its own state",
    body: "A timeout or an ambiguous answer becomes Verifying. The quote stays locked, so nobody can pay twice or start work on a guess.",
  },
  {
    icon: RefreshCw,
    title: "Recovery is explicit",
    body: "The studio asks the server to check PayPal again, or closes the attempt after confirming in the PayPal dashboard that no order exists.",
  },
  {
    icon: Receipt,
    title: "The snapshot is the receipt",
    body: "After a verified capture the exact paid lines are written to an order snapshot. A paid brief cannot be deleted.",
  },
];

export function Payments() {
  return (
    <Section id="payments">
      <SectionHeading
        eyebrow="Verified payments"
        title="“The redirect came back” is not the same as “paid”."
        lede="Payments run on the PayPal sandbox. The desk treats every external answer as untrusted until the server has checked it."
      />
      <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <ol className="relative flex flex-col gap-1 border-l border-line pl-6">
          {flow.map((step) => {
            const Icon = step.icon;
            return (
              <li key={step.title} className="relative pb-6 last:pb-0">
                <span className="absolute -left-[37px] top-0 flex h-7 w-7 items-center justify-center rounded-full border border-line bg-paper-card text-pine shadow-card">
                  <Icon size={14} />
                </span>
                <h3 className="text-[15px] font-semibold text-ink">{step.title}</h3>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-muted">{step.body}</p>
              </li>
            );
          })}
        </ol>

        <div className="surface overflow-hidden shadow-panel">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <div className="flex flex-col gap-0.5">
              <span className="label">Payment attempt · specimen</span>
              <span className="font-mono text-[13px] text-ink">order 5O190127TN364715T</span>
            </div>
            <StatusPill status="RECONCILING" />
          </div>
          <div className="flex flex-col gap-4 px-5 py-5">
            <div className="rounded-md border border-flag-warn/40 bg-flag-warn/5 px-4 py-3">
              <p className="text-[13px] font-medium text-flag-warn">PayPal did not give a clear answer.</p>
              <p className="mt-1 text-[12.5px] leading-relaxed text-ink-muted">
                The capture request timed out. The quote stays locked until the server confirms
                the outcome. Nothing has been marked paid or failed.
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line text-[12px]">
              {[
                ["error code", "capture_unknown"],
                ["retries", "1"],
                ["quote", "v2 · payment locked"],
                ["snapshot", "not written"],
              ].map(([key, value]) => (
                <div key={key} className="bg-paper-card px-3 py-2.5">
                  <dt className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">{key}</dt>
                  <dd className="mt-0.5 font-mono text-ink">{value}</dd>
                </div>
              ))}
            </dl>
            <div className="flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-md border border-pine bg-pine px-3 py-1.5 text-[12px] font-medium text-ink-invert">
                <RefreshCw size={12} /> Check with PayPal again
              </span>
              <span className="inline-flex items-center rounded-md border border-line px-3 py-1.5 text-[12px] text-ink-muted">
                Close attempt with a note
              </span>
            </div>
            <p className="font-mono text-[10px] text-ink-faint">
              Specimen view of the studio's recovery panel. Buttons here are illustrations.
            </p>
          </div>
        </div>
      </div>
    </Section>
  );
}
