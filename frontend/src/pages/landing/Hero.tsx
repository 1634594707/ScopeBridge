import { ArrowRight, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "../../components/Button";
import { BrandMark } from "../../components/BrandMark";
import { Money } from "../../components/Money";
import { RuleChip } from "../../components/Tag";
import { StatusPill } from "../../components/StatusPill";

/** Facts about how the system is built, not usage metrics. */
const facts = [
  { value: "0", label: "prices written by the model", detail: "Every amount comes from the rules layer" },
  { value: "1", label: "frozen version per payment", detail: "The confirmed quote is the paid quote" },
  { value: "2", label: "humans sign off", detail: "Studio reviews, client confirms" },
  { value: "1", label: "server check before “paid”", detail: "Unknown outcomes wait in Verifying" },
];

const promises = [
  "Each quote line names the rule that priced it",
  "Infeasible scopes stay visible, with the reason",
  "PayPal is verified server-side before work starts",
];

function SpecimenQuote() {
  return (
    <aside className="relative">
      <div className="absolute -inset-4 -z-10 rounded-2xl grid-paper opacity-70 [mask-image:radial-gradient(circle_at_center,black,transparent_75%)]" />
      <div className="absolute -right-3 -top-3 hidden rounded-md border border-line bg-paper-card px-3 py-2 shadow-panel sm:block">
        <span className="label">Source</span>
        <p className="mt-0.5 max-w-[22ch] text-[11px] leading-snug text-ink-muted">
          “Three pages, ordering on the site, budget $500.”
        </p>
      </div>
      <div className="surface animate-fade-up-slow px-5 py-5 shadow-float">
        <div className="flex items-start justify-between border-b border-line pb-4">
          <div className="flex flex-col gap-1">
            <span className="label">Quote · v1</span>
            <span className="text-[15px] font-semibold tracking-[-0.015em]">Fern &amp; Filter Coffee</span>
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
              <span className="text-[13px] text-ink-muted line-through decoration-ink-faint">On-site ordering</span>
              <span className="font-mono text-[10px] text-flag-bad">not offered · stays visible</span>
            </div>
            <Money amountMinor={0} size="sm" tone="muted" />
          </li>
          <li className="flex items-start justify-between gap-4 py-3">
            <div className="flex flex-col gap-1">
              <span className="text-[13px] text-ink">Total, confirmed version</span>
              <span className="font-mono text-[10px] text-flag-warn">budget short by $200.00</span>
            </div>
            <Money amountMinor={70000} size="lg" />
          </li>
        </ul>

        <div className="mt-1 flex items-center justify-between rounded-md bg-paper px-3 py-2.5">
          <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            <span className="h-1.5 w-1.5 animate-soft-pulse rounded-full bg-flag-warn" />
            Waiting for client confirmation
          </span>
          <span className="font-mono text-[10px] text-ink-faint">rules v1</span>
        </div>
      </div>
      <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
        Specimen quote · demo price list, not a market rate
      </p>
    </aside>
  );
}

export function Hero() {
  return (
    <div className="flex flex-col gap-14">
      <section className="grid items-center gap-12 pt-6 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16 lg:pt-10">
        <div className="flex flex-col gap-7">
          <div className="flex w-fit items-center gap-2.5 rounded-full border border-line bg-paper-card px-3 py-1.5 shadow-card">
            <BrandMark className="h-4 w-4 text-pine" />
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
              Agreement desk for studio work
            </span>
          </div>

          <h1 className="max-w-[18ch] text-[40px] font-semibold leading-[1.04] tracking-[-0.04em] text-ink sm:text-[56px]">
            Agree on the work <span className="text-pine">before</span> anyone pays for it.
          </h1>

          <p className="max-w-[54ch] text-[16px] leading-[1.7] text-ink-muted">
            ScopeBridge turns an ambiguous client request into a priced, rule-checked scope. Every
            line on the quote points back to the sentence that caused it, and nothing moves forward
            without a second human confirming the same version.
          </p>

          <ul className="flex flex-col gap-2">
            {promises.map((promise) => (
              <li key={promise} className="flex items-center gap-2.5 text-[14px] text-ink">
                <CheckCircle2 size={16} className="shrink-0 text-pine" />
                {promise}
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Link to="/start">
              <Button size="md" icon={<ArrowRight size={15} />}>
                Start a brief
              </Button>
            </Link>
            <Link to="/console">
              <Button variant="secondary" size="md">
                Enter the seller console
              </Button>
            </Link>
            <Link
              to={{ pathname: "/", hash: "#how-it-works" }}
              className="px-2 text-[13px] text-ink-muted underline-offset-4 hover:text-ink hover:underline"
            >
              See how it works
            </Link>
          </div>
        </div>

        <SpecimenQuote />
      </section>

      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line lg:grid-cols-4">
        {facts.map((fact) => (
          <div key={fact.label} className="flex flex-col gap-1.5 bg-paper-card px-5 py-5">
            <dt className="order-2 text-[13px] font-medium text-ink">{fact.label}</dt>
            <dd className="order-1 numeric text-[34px] font-semibold leading-none tracking-[-0.03em] text-pine">
              {fact.value}
            </dd>
            <dd className="order-3 text-[12px] leading-snug text-ink-faint">{fact.detail}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
