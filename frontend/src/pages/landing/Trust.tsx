import { useState } from "react";
import { ArrowRight, Check, ChevronDown, Lock, Minus, Scale, ScrollText, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "../../components/Button";
import { cn } from "../../lib/cn";
import { Section, SectionHeading } from "./Section";

const guarantees = [
  {
    icon: Scale,
    title: "Prices come from rules, not from the model",
    body: "A quote line is never typed or invented. Each one carries the reference of the published rule that produced it, so any number on the invoice traces back to a rate both sides can read.",
  },
  {
    icon: Lock,
    title: "The reviewed version is the paid version",
    body: "A quote freezes when the studio issues it, and the client confirms that exact version. Payment opens against the frozen lines, not against a chat summary of what was maybe agreed.",
  },
  {
    icon: ShieldCheck,
    title: "Payment is verified, not assumed",
    body: "The server checks the payment with PayPal before anything is marked paid. An outcome the server cannot confirm waits in a reconciling state instead of being guessed at.",
  },
  {
    icon: ScrollText,
    title: "Every step leaves a record",
    body: "Extraction, pricing, confirmation and capture each append to the brief's history, and the paid quote is snapshotted. You can reconstruct the deal months later, line by line.",
  },
];

const seats = [
  {
    label: "For the client",
    cta: { to: "/start", text: "Start a brief" },
    points: [
      "Create an account and describe the work the way you would in an email.",
      "Choose between up to two priced scopes, including the one that does not fit, with the reason.",
      "Confirm the exact version that was reviewed, then pay it. Nothing changes behind your back.",
    ],
  },
  {
    label: "For the studio",
    cta: { to: "/console", text: "Open the console" },
    points: [
      "Review every brief that lands on the desk before anything is promised.",
      "Price against the published rules; the model proposes structure, never amounts.",
      "Verify the payment before work starts. The order snapshot is the receipt.",
    ],
  },
];

const comparison: { row: string; email: boolean | string; desk: boolean | string }[] = [
  { row: "Each price line names its source", email: false, desk: true },
  { row: "Budget conflicts are shown, not trimmed away", email: "sometimes", desk: true },
  { row: "Client confirms one frozen version", email: false, desk: true },
  { row: "Payment tied to that version", email: false, desk: true },
  { row: "Unclear payment outcome handled explicitly", email: false, desk: true },
  { row: "History you can replay months later", email: "scattered", desk: true },
];

const questions = [
  {
    q: "Does the AI decide the price?",
    a: "No. The model reads the brief and proposes structure; the price comes from the published rules and the verdict comes from the program. The same brief in, the same price out.",
  },
  {
    q: "What if my budget does not fit the request?",
    a: "You still see a scope: the one that cannot be met, with the reason it fails. The desk does not quietly trim the request to hit a number.",
  },
  {
    q: "Can the studio change the price after I confirm?",
    a: "No. Quote lines freeze when the studio reviews them. If the brief changes after confirmation, that confirmed version is superseded and needs a fresh confirmation; it is never edited in place.",
  },
  {
    q: "Do both sides need accounts?",
    a: "Yes. The studio signs in to price and review; the client signs in to submit, confirm and pay. Every action is attributed to a signed-in account, which is what makes the record auditable.",
  },
  {
    q: "Is this a real payment?",
    a: "No. The desk runs on the PayPal sandbox. No card details are collected and no money moves.",
  },
  {
    q: "What does “Verifying” mean on a payment?",
    a: "The server sent a request to PayPal and did not get a clear answer. The quote stays locked until the server checks again, so the same quote cannot be paid twice.",
  },
  {
    q: "What happens after payment?",
    a: "The server verifies the capture with PayPal, marks the quote paid and writes an order snapshot of the exact lines. That snapshot, not the page, is the record.",
  },
];

function Cell({ value }: { value: boolean | string }) {
  if (value === true) {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-pine text-ink-invert">
        <Check size={13} />
      </span>
    );
  }
  if (value === false) {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-paper-deep text-ink-faint">
        <Minus size={13} />
      </span>
    );
  }
  return <span className="font-mono text-[11px] text-ink-faint">{value}</span>;
}

function FaqItem({ q, a, defaultOpen }: { q: string; a: string; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(Boolean(defaultOpen));
  return (
    <div className="border-b border-line last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center justify-between gap-6 px-5 py-4 text-left"
      >
        <span className="text-[15px] font-medium text-ink">{q}</span>
        <ChevronDown
          size={16}
          className={cn("shrink-0 text-ink-faint transition-transform duration-200", open && "rotate-180 text-pine")}
        />
      </button>
      {open ? (
        <p className="max-w-[70ch] px-5 pb-5 text-[13.5px] leading-relaxed text-ink-muted animate-fade-up">{a}</p>
      ) : null}
    </div>
  );
}

export function Trust() {
  return (
    <>
      <Section id="guarantees">
        <SectionHeading eyebrow="Guarantees" title="Four things the desk will not let happen." />
        <div className="grid gap-4 sm:grid-cols-2">
          {guarantees.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.title} className="surface flex gap-4 px-6 py-6">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-pine text-ink-invert">
                  <Icon size={18} />
                </span>
                <div className="flex flex-col gap-2">
                  <h3 className="text-[16px] font-semibold tracking-[-0.01em] text-ink">{item.title}</h3>
                  <p className="text-[13.5px] leading-relaxed text-ink-muted">{item.body}</p>
                </div>
              </article>
            );
          })}
        </div>
      </Section>

      <Section id="roles">
        <SectionHeading eyebrow="Two seats" title="One desk, two sides of the same agreement." />
        <div className="grid gap-4 md:grid-cols-2">
          {seats.map((seat) => (
            <article key={seat.label} className="surface flex flex-col gap-5 px-6 py-6">
              <span className="eyebrow">{seat.label}</span>
              <ol className="flex flex-col gap-4">
                {seat.points.map((point, index) => (
                  <li key={point} className="flex gap-3">
                    <span className="numeric mt-0.5 text-[12px] text-pine">0{index + 1}</span>
                    <span className="text-[14px] leading-relaxed text-ink">{point}</span>
                  </li>
                ))}
              </ol>
              <Link
                to={seat.cta.to}
                className="mt-auto inline-flex w-fit items-center gap-1.5 text-[13px] font-medium text-pine underline-offset-4 hover:underline"
              >
                {seat.cta.text} <ArrowRight size={13} />
              </Link>
            </article>
          ))}
        </div>
      </Section>

      <Section id="compare">
        <SectionHeading
          eyebrow="Compared"
          title="What changes against email and an invoice."
          lede="The usual way works until someone asks which message justified which line."
        />
        <div className="surface overflow-x-auto">
          <table className="w-full min-w-[520px] text-left">
            <thead>
              <tr className="border-b border-line">
                <th className="label px-5 py-3 font-normal">Capability</th>
                <th className="label w-[150px] px-5 py-3 text-center font-normal">Email + invoice</th>
                <th className="w-[150px] bg-pine-wash px-5 py-3 text-center font-mono text-[11px] uppercase tracking-[0.16em] text-pine-deep">
                  ScopeBridge
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {comparison.map((row) => (
                <tr key={row.row}>
                  <td className="px-5 py-3.5 text-[13.5px] text-ink">{row.row}</td>
                  <td className="px-5 py-3.5 text-center">
                    <Cell value={row.email} />
                  </td>
                  <td className="bg-pine-wash/50 px-5 py-3.5 text-center">
                    <Cell value={row.desk} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="faq">
        <SectionHeading eyebrow="FAQ" title="Common questions." />
        <div className="surface">
          {questions.map((item, index) => (
            <FaqItem key={item.q} q={item.q} a={item.a} defaultOpen={index === 0} />
          ))}
        </div>
      </Section>

      <section className="relative overflow-hidden rounded-2xl bg-pine px-6 py-12 text-ink-invert sm:px-12 sm:py-16">
        <div className="absolute inset-0 opacity-[0.12] grid-paper [filter:invert(1)]" />
        <div className="relative flex flex-col items-start gap-6 md:flex-row md:items-end md:justify-between">
          <div className="flex max-w-[52ch] flex-col gap-3">
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-invert/70">
              Ready when you are
            </span>
            <h2 className="text-[30px] font-semibold leading-[1.12] tracking-[-0.025em] sm:text-[38px]">
              Write the brief once. Agree on one version. Pay for exactly that.
            </h2>
            <p className="text-[14px] leading-relaxed text-ink-invert/75">
              The demo runs locally against the PayPal sandbox. Create a client account, submit a
              brief and follow it all the way to a verified payment.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/start">
              <Button className="border-paper-card bg-paper-card text-pine-deep shadow-none hover:border-paper hover:bg-paper" icon={<ArrowRight size={15} />}>
                Start a brief
              </Button>
            </Link>
            <Link to="/rules">
              <Button variant="ghost" className="border-ink-invert/30 text-ink-invert hover:bg-ink-invert/10 hover:text-ink-invert">
                Read the price list
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
