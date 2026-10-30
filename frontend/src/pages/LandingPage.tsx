import { ArrowRight, FileCheck2, GitCompareArrows, ScanSearch } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "../components/Button";
import { Money } from "../components/Money";
import { RuleChip } from "../components/Tag";
import { StatusPill } from "../components/StatusPill";

const problems = [
  {
    index: "01",
    title: "The brief arrives as a paragraph",
    body: "“Three pages, online ordering, live next week, budget $500.” Four constraints, at least two of them in conflict, and no shared reading of what was promised.",
  },
  {
    index: "02",
    title: "Scope grows, the price does not",
    body: "Every extra round is agreed in chat. By delivery nobody can reconstruct which message justified which line on the invoice.",
  },
  {
    index: "03",
    title: "Payment and agreement drift apart",
    body: "A deposit lands against a version of the scope that has already changed. Nobody can prove what was bought.",
  },
];

const steps = [
  {
    icon: ScanSearch,
    title: "Read the brief",
    body: "Budget, deadline and assets become structured fields. Missing facts stay missing — the desk asks instead of guessing.",
    note: "Extraction, no pricing",
  },
  {
    icon: GitCompareArrows,
    title: "Compare two honest options",
    body: "Each candidate scope is priced and judged by rules, not by the model. Infeasible scopes stay visible with the reason they fail.",
    note: "Rules decide",
  },
  {
    icon: FileCheck2,
    title: "Review, confirm, then pay",
    body: "The studio reviews a frozen version; the client confirms that exact version. Only then does the sandbox payment open.",
    note: "Two humans, one version",
  },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-20 pb-16">
      <section className="grid items-start gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:gap-14">
        <div className="flex flex-col gap-7 pt-4">
          <div className="flex items-center gap-3">
            <span className="h-px w-8 bg-pine" />
            <span className="label">ScopeBridge · agreement desk for studio work</span>
          </div>

          <h1 className="max-w-[22ch] text-[38px] font-semibold leading-[1.06] tracking-[-0.035em] text-ink sm:text-[48px]">
            Agree on the work before anyone pays for it.
          </h1>

          <p className="max-w-[56ch] text-[15px] leading-[1.7] text-ink-muted">
            ScopeBridge turns an ambiguous client request into a priced, rule-checked scope.
            Every line on the quote points back to the sentence that caused it, and nothing moves
            forward without a second human confirming the same version.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <Link to="/start">
              <Button size="md" icon={<ArrowRight size={15} />}>
                Open a client brief
              </Button>
            </Link>
            <Link to="/console">
              <Button variant="secondary" size="md">
                Enter the seller console
              </Button>
            </Link>
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 pt-2 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-faint">
            <span>Runs locally</span>
            <span className="h-3 w-px bg-line" />
            <span>PayPal sandbox</span>
            <span className="h-3 w-px bg-line" />
            <span>MIT licensed</span>
          </div>
        </div>

        <aside className="relative">
          <div className="surface animate-fade-up px-5 py-5 shadow-lift">
            <div className="flex items-start justify-between border-b border-line pb-4">
              <div className="flex flex-col gap-1">
                <span className="label">Quote · v1</span>
                <span className="text-[15px] font-semibold tracking-[-0.015em]">
                  Fern &amp; Filter Coffee
                </span>
                <span className="font-mono text-[11px] text-ink-faint">3 pages · 5 working days</span>
              </div>
              <StatusPill status="REVIEWED" />
            </div>

            <ul className="flex flex-col">
              <li className="flex items-start justify-between gap-4 border-b border-line/70 py-3">
                <div className="flex flex-col gap-1">
                  <span className="text-[13px] text-ink">Landing page (base build)</span>
                  <RuleChip ruleRef="rule.base_page" />
                </div>
                <Money amountMinor={50000} size="sm" />
              </li>
              <li className="flex items-start justify-between gap-4 border-b border-line/70 py-3">
                <div className="flex flex-col gap-1">
                  <span className="text-[13px] text-ink">Additional page ×2</span>
                  <RuleChip ruleRef="rule.extra_page" />
                </div>
                <Money amountMinor={20000} size="sm" />
              </li>
              <li className="flex items-start justify-between gap-4 border-b border-line/70 py-3">
                <div className="flex flex-col gap-1">
                  <span className="text-[13px] text-ink-muted">On-site ordering</span>
                  <span className="font-mono text-[10px] text-flag-bad">not offered</span>
                </div>
                <Money amountMinor={0} size="sm" tone="muted" />
              </li>
              <li className="flex items-start justify-between gap-4 py-3">
                <div className="flex flex-col gap-1">
                  <span className="text-[13px] text-ink">Total, confirmed version</span>
                  <span className="font-mono text-[10px] text-ink-faint">budget short by $200.00</span>
                </div>
                <Money amountMinor={70000} size="lg" />
              </li>
            </ul>
          </div>
          <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
            Specimen quote · demo price list, not a market rate
          </p>
        </aside>
      </section>

      <section className="flex flex-col gap-6">
        <div className="flex items-end justify-between gap-6">
          <h2 className="max-w-[24ch] text-[24px] font-semibold leading-tight tracking-[-0.02em]">
            Freelance web work fails in the gap between the brief and the invoice.
          </h2>
          <span className="hidden shrink-0 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint sm:block">
            Three failures
          </span>
        </div>
        <div className="grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3">
          {problems.map((item) => (
            <article key={item.index} className="flex flex-col gap-3 bg-paper-card px-5 py-6">
              <span className="font-mono text-[11px] tracking-[0.16em] text-pine">{item.index}</span>
              <h3 className="text-[15px] font-semibold tracking-[-0.01em]">{item.title}</h3>
              <p className="text-[13px] leading-relaxed text-ink-muted">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-8">
        <div className="flex flex-col gap-2">
          <span className="label">The desk</span>
          <h2 className="max-w-[30ch] text-[26px] font-semibold leading-tight tracking-[-0.025em]">
            Three moves, and two of them belong to a human.
          </h2>
        </div>
        <div className="grid gap-8 sm:grid-cols-3">
          {steps.map(({ icon: Icon, title, body, note }, index) => (
            <div key={title} className="flex flex-col gap-3 border-t border-line pt-5">
              <div className="flex items-center justify-between">
                <Icon size={18} strokeWidth={1.6} className="text-pine" />
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </div>
              <h3 className="text-[15px] font-semibold tracking-[-0.01em]">{title}</h3>
              <p className="text-[13px] leading-relaxed text-ink-muted">{body}</p>
              <span className="mt-auto font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
                {note}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col items-start justify-between gap-5 rounded-lg border border-pine/20 bg-pine-wash px-6 py-7 sm:flex-row sm:items-center">
        <div className="flex flex-col gap-1.5">
          <h2 className="text-[19px] font-semibold tracking-[-0.02em] text-pine-deep">
            Try the whole loop with the demo brief.
          </h2>
          <p className="text-[13px] leading-relaxed text-pine-deep/75">
            Submit a request as a client, price it as the studio, then confirm the exact version that
            was reviewed.
          </p>
        </div>
        <Link to="/start" className="shrink-0">
          <Button icon={<ArrowRight size={15} />}>Start with a brief</Button>
        </Link>
      </section>
    </div>
  );
}
