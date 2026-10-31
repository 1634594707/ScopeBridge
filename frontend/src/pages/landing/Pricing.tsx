import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bot, Calculator, Gavel, UserCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../lib/api";
import { Money } from "../../components/Money";
import { Tag } from "../../components/Tag";
import { Section, SectionHeading } from "./Section";

const authorities = [
  {
    icon: Bot,
    who: "The model",
    may: "Read the brief, extract pages, features, deadline and assets, ask clarifying questions.",
    never: "Write an amount. Its output schema has no price field.",
  },
  {
    icon: Calculator,
    who: "The rules",
    may: "Price each line from the published version: base page, extra pages, add-ons.",
    never: "Change silently. A new price is a new version; issued quotes keep theirs.",
  },
  {
    icon: Gavel,
    who: "The program",
    may: "Judge feasibility against budget, lead time and capabilities, and name the rule.",
    never: "Trim the request to fit. An infeasible scope is shown, not hidden.",
  },
  {
    icon: UserCheck,
    who: "The people",
    may: "Studio reviews and freezes a version. Client confirms and pays that version.",
    never: "Pay for something different from what was reviewed.",
  },
];

function LivePriceList() {
  const rules = useQuery({ queryKey: ["service-rules"], queryFn: api.serviceRules });

  if (rules.isLoading) {
    return (
      <div className="surface flex min-h-[280px] items-center justify-center px-6 py-10 text-[13px] text-ink-faint">
        Loading the published price list…
      </div>
    );
  }

  if (rules.error || !rules.data) {
    const code = rules.error instanceof ApiError ? rules.error.code : "network_error";
    return (
      <div className="flex min-h-[280px] flex-col justify-center gap-2 rounded-lg border border-flag-bad/30 bg-flag-bad/5 px-6 py-8">
        <span className="label text-flag-bad">Price list unavailable</span>
        <p className="text-[13px] leading-relaxed text-ink-muted">
          The server did not return the published rules, so no prices are shown here. Nothing on
          this page invents a number in their place.
        </p>
        <span className="font-mono text-[11px] text-ink-faint">code · {code}</span>
      </div>
    );
  }

  const data = rules.data;
  const rows = [
    { label: "First page", ref: "rule.base_page", amount: data.base_page_minor },
    { label: "Each additional page", ref: "rule.extra_page", amount: data.extra_page_minor },
    ...data.addons.slice(0, 4).map((addon) => ({
      label: addon.label,
      ref: `rule.addon.${addon.code}`,
      amount: addon.amount_minor,
    })),
  ];

  return (
    <div className="surface overflow-hidden shadow-panel">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div className="flex flex-col gap-0.5">
          <span className="label">Live from the server</span>
          <span className="text-[14px] font-semibold text-ink">Published rules · v{data.version_no}</span>
        </div>
        <Tag tone="good">
          <span className="h-1.5 w-1.5 rounded-full bg-flag-good" />
          {data.currency}
        </Tag>
      </div>
      <ul className="divide-y divide-line">
        {rows.map((row) => (
          <li key={row.ref} className="flex items-center justify-between gap-4 px-5 py-3">
            <span className="flex flex-col gap-0.5">
              <span className="text-[13px] text-ink">{row.label}</span>
              <span className="font-mono text-[10px] text-ink-faint">{row.ref}</span>
            </span>
            <Money amountMinor={row.amount} currency={data.currency} size="sm" tone={row.amount === 0 ? "muted" : "default"} />
          </li>
        ))}
      </ul>
      <div className="grid grid-cols-2 gap-px border-t border-line bg-line">
        <div className="bg-paper px-5 py-3">
          <span className="label">Revisions</span>
          <p className="numeric text-[15px] text-ink">{data.revisions_included} included</p>
        </div>
        <div className="bg-paper px-5 py-3">
          <span className="label">Lead time</span>
          <p className="numeric text-[15px] text-ink">{data.lead_time_days} working days</p>
        </div>
      </div>
      <Link
        to="/rules"
        className="flex items-center justify-between border-t border-line px-5 py-3 text-[13px] font-medium text-pine transition-colors hover:bg-pine-wash"
      >
        See the full price list and estimator
        <ArrowRight size={14} />
      </Link>
    </div>
  );
}

export function Pricing() {
  return (
    <Section id="pricing">
      <SectionHeading
        eyebrow="Rules-based pricing"
        title="Four parties touch a quote. Only one of them sets the price."
        lede="Splitting the work this way is what makes a quote reproducible: the same brief and the same rule version always produce the same lines and the same total."
      />
      <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="grid gap-4 sm:grid-cols-2">
          {authorities.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.who} className="surface flex flex-col gap-3 px-5 py-5 transition-shadow duration-200 hover:shadow-panel">
                <span className="flex items-center gap-2.5">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-pine-wash text-pine">
                    <Icon size={16} />
                  </span>
                  <span className="text-[15px] font-semibold text-ink">{item.who}</span>
                </span>
                <div className="flex flex-col gap-1">
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-flag-good">may</span>
                  <p className="text-[13px] leading-relaxed text-ink-muted">{item.may}</p>
                </div>
                <div className="flex flex-col gap-1 border-t border-line pt-3">
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-flag-bad">never</span>
                  <p className="text-[13px] leading-relaxed text-ink-muted">{item.never}</p>
                </div>
              </article>
            );
          })}
        </div>
        <LivePriceList />
      </div>
    </Section>
  );
}
