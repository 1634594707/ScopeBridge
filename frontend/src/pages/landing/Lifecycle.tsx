import { ArrowRight, CornerDownRight } from "lucide-react";
import { StatusPill } from "../../components/StatusPill";
import { Section, SectionHeading } from "./Section";

const quoteStates = [
  { status: "DRAFT", who: "Studio", body: "Priced from a proposal. A newer quote replaces it instead of editing it." },
  { status: "REVIEWED", who: "Studio", body: "Frozen. The lines and the total can no longer change." },
  { status: "CONFIRMED", who: "Client", body: "The client accepted this exact version and revision." },
  { status: "PAYMENT_LOCKED", who: "Server", body: "A payment attempt is open; the quote cannot be replaced." },
  { status: "PAID", who: "Server", body: "Capture verified with PayPal; an order snapshot is written." },
];

const paymentStates = [
  { status: "CREATING", body: "The server asks PayPal for an order." },
  { status: "AWAITING_APPROVAL", body: "The client approves in the sandbox window." },
  { status: "CAPTURING", body: "The server captures the approved order." },
  { status: "COMPLETED", body: "Capture verified. The quote becomes paid." },
];

const exits = [
  {
    status: "RECONCILING",
    title: "Outcome unknown",
    body: "A timeout or an unclear PayPal answer. The attempt is neither paid nor failed until the server checks again. The studio can trigger that check from the brief.",
  },
  {
    status: "FAILED",
    title: "PayPal refused",
    body: "The order was declined or could not be created. The quote stays confirmed and the client may start a new attempt.",
  },
  {
    status: "ABANDONED",
    title: "Closed by hand",
    body: "The studio confirms no order exists and closes the attempt with a note. That note is kept on the record.",
  },
  {
    status: "SUPERSEDED",
    title: "Brief changed",
    body: "A new message bumps the revision. Draft, reviewed and confirmed quotes are superseded, never edited; a locked or paid quote cannot be replaced this way.",
  },
];

export function Lifecycle() {
  return (
    <Section id="lifecycle">
      <SectionHeading
        eyebrow="Lifecycle"
        title="Every quote and every payment has one state, owned by one party."
        lede="States only move forward through explicit actions. Nothing is inferred from a redirect or a page refresh, and an answer the server cannot confirm is shown as Verifying."
      />

      <div className="surface overflow-hidden shadow-panel">
        <div className="border-b border-line px-5 py-3">
          <span className="label">Quote</span>
        </div>
        <ol className="grid gap-px bg-line md:grid-cols-5">
          {quoteStates.map((state, index) => (
            <li key={state.status} className="relative flex flex-col gap-3 bg-paper-card px-4 py-5">
              <div className="flex items-center justify-between">
                <StatusPill status={state.status} />
                {index < quoteStates.length - 1 ? (
                  <ArrowRight size={13} className="hidden text-ink-faint md:block" />
                ) : null}
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
                by {state.who}
              </span>
              <p className="text-[12.5px] leading-relaxed text-ink-muted">{state.body}</p>
            </li>
          ))}
        </ol>

        <div className="border-y border-line px-5 py-3">
          <span className="label">Payment attempt · inside PAYMENT_LOCKED</span>
        </div>
        <ol className="grid gap-px bg-line sm:grid-cols-2 md:grid-cols-4">
          {paymentStates.map((state) => (
            <li key={state.status} className="flex flex-col gap-2 bg-paper px-4 py-4">
              <StatusPill status={state.status} className="w-fit" />
              <p className="text-[12.5px] leading-relaxed text-ink-muted">{state.body}</p>
            </li>
          ))}
        </ol>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {exits.map((exit) => (
          <article
            key={exit.status}
            className={
              exit.status === "RECONCILING"
                ? "flex flex-col gap-3 rounded-lg border border-flag-warn/40 bg-flag-warn/5 px-5 py-5"
                : "surface flex flex-col gap-3 px-5 py-5"
            }
          >
            <div className="flex items-center gap-2">
              <CornerDownRight size={14} className="text-ink-faint" />
              <StatusPill status={exit.status} />
            </div>
            <h3 className="text-[14px] font-semibold text-ink">{exit.title}</h3>
            <p className="text-[12.5px] leading-relaxed text-ink-muted">{exit.body}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
