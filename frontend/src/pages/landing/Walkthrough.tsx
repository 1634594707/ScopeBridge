import { useState } from "react";
import { BadgeCheck, CreditCard, FileCheck2, GitCompareArrows, MessageSquareText, ScanSearch } from "lucide-react";
import { cn } from "../../lib/cn";
import { Money } from "../../components/Money";
import { RuleChip, Tag } from "../../components/Tag";
import { StatusPill } from "../../components/StatusPill";
import { Section, SectionHeading } from "./Section";

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
    icon: MessageSquareText,
    title: "The client writes a brief",
    who: "Client",
    body: "Plain language, the way they would write an email. Budget, deadline and whether assets are ready are asked as fields, so the important facts are never buried in prose.",
  },
  {
    icon: ScanSearch,
    title: "The model extracts facts",
    who: "Model",
    body: "Pages, features, deadline, assets. The model returns facts and questions only. It never returns a scope price, and missing facts stay missing instead of being guessed.",
  },
  {
    icon: GitCompareArrows,
    title: "Rules price two options",
    who: "Rules",
    body: "Candidate scopes are priced by the published rule version. A scope that breaks the budget or the deadline is still shown, with the violated rule next to it.",
  },
  {
    icon: FileCheck2,
    title: "Studio reviews, client confirms",
    who: "Both",
    body: "The studio freezes one version. The client confirms that exact version. Any new message bumps the revision and the old quote is superseded, not edited.",
  },
  {
    icon: CreditCard,
    title: "Payment is verified",
    who: "Server",
    body: "The client approves in the PayPal sandbox. The server captures and checks the order before marking the quote paid and writing the order snapshot.",
  },
];

function StepPreview({ index }: { index: number }) {
  if (index === 0) {
    return (
      <div className="flex flex-col gap-3">
        <span className="label">Message · rev 1 · client</span>
        <p className="rounded-md border border-line bg-paper px-4 py-3 text-[14px] leading-relaxed text-ink">
          We are opening a second café and need a small site: home, menu and a visit page. Ordering
          online would be great. Launch is in two weeks and we have about $500.
        </p>
        <div className="flex flex-wrap gap-2">
          <Tag>budget · $500.00</Tag>
          <Tag>live by · in 14 days</Tag>
          <Tag tone="warn">assets · not ready</Tag>
        </div>
      </div>
    );
  }
  if (index === 1) {
    return (
      <div className="flex flex-col gap-3">
        <span className="label">Extraction · facts only</span>
        <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line text-[13px]">
          {[
            ["pages", "3"],
            ["features", "online_ordering"],
            ["deadline_days", "14"],
            ["assets_ready", "false"],
          ].map(([key, value]) => (
            <div key={key} className="flex flex-col gap-0.5 bg-paper-card px-3 py-2.5">
              <dt className="font-mono text-[10px] text-ink-faint">{key}</dt>
              <dd className="font-mono text-ink">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="rounded-md border border-dashed border-flag-warn/40 bg-flag-warn/5 px-3 py-2 text-[12px] text-flag-warn">
          Question for the client: should the menu page be editable after launch?
        </div>
        <p className="font-mono text-[10px] text-ink-faint">No amount field exists in the model's output schema.</p>
      </div>
    );
  }
  if (index === 2) {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        {[
          { label: "Within budget", pages: "1 page", total: 50000, ok: true },
          { label: "As requested", pages: "3 pages + ordering", total: 70000, ok: false },
        ].map((option) => (
          <div key={option.label} className="flex flex-col gap-2 rounded-md border border-line bg-paper-card px-3 py-3">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-ink">{option.label}</span>
              <Tag tone={option.ok ? "good" : "bad"}>{option.ok ? "feasible" : "over budget"}</Tag>
            </div>
            <span className="font-mono text-[11px] text-ink-faint">{option.pages}</span>
            <Money amountMinor={option.total} size="lg" />
            <RuleChip ruleRef={option.ok ? "rule.base_page" : "rule.budget"} className="w-fit" />
          </div>
        ))}
        <p className="font-mono text-[10px] text-ink-faint sm:col-span-2">Specimen numbers from the demo price list.</p>
      </div>
    );
  }
  if (index === 3) {
    return (
      <div className="flex flex-col gap-2">
        {[
          { v: "v1", status: "SUPERSEDED", note: "rev 1 · replaced after a new client message" },
          { v: "v2", status: "REVIEWED", note: "rev 2 · frozen by the studio" },
          { v: "v2", status: "CONFIRMED", note: "rev 2 · confirmed by the client" },
        ].map((row, i) => (
          <div key={i} className="flex items-center justify-between rounded-md border border-line bg-paper-card px-3 py-2.5">
            <span className="flex items-center gap-3">
              <span className="font-mono text-[12px] text-ink">{row.v}</span>
              <span className="text-[12px] text-ink-muted">{row.note}</span>
            </span>
            <StatusPill status={row.status} />
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {["AWAITING_APPROVAL", "CAPTURING", "COMPLETED"].map((status, i) => (
        <div key={status} className="flex items-center gap-3 rounded-md border border-line bg-paper-card px-3 py-2.5">
          <span className="font-mono text-[11px] text-ink-faint">0{i + 1}</span>
          <StatusPill status={status} />
          <span className="text-[12px] text-ink-muted">
            {i === 0 ? "Client approves in the sandbox" : i === 1 ? "Server captures the order" : "Server checks PayPal, writes the snapshot"}
          </span>
        </div>
      ))}
      <p className="flex items-center gap-2 pt-1 text-[12px] text-pine">
        <BadgeCheck size={14} /> Only a server-verified capture marks the quote paid.
      </p>
    </div>
  );
}

export function Walkthrough() {
  const [active, setActive] = useState(0);

  return (
    <>
      <Section>
        <SectionHeading
          eyebrow="The problem"
          title="Freelance web work fails in the gap between the brief and the invoice."
        />
        <div className="grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-3">
          {problems.map((item) => (
            <article key={item.index} className="flex flex-col gap-3 bg-paper-card px-6 py-7">
              <span className="font-mono text-[12px] tracking-[0.16em] text-pine">{item.index}</span>
              <h3 className="text-[16px] font-semibold tracking-[-0.01em]">{item.title}</h3>
              <p className="text-[13.5px] leading-relaxed text-ink-muted">{item.body}</p>
            </article>
          ))}
        </div>
      </Section>

      <Section id="how-it-works">
        <SectionHeading
          eyebrow="How it works"
          title="Five steps from a paragraph to a paid, provable scope."
          lede="Each step has one owner. Pick a step to see what that owner produces."
        />
        <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <ol className="flex flex-col gap-2">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const selected = index === active;
              return (
                <li key={step.title}>
                  <button
                    type="button"
                    onClick={() => setActive(index)}
                    aria-pressed={selected}
                    className={cn(
                      "flex w-full cursor-pointer items-start gap-4 rounded-lg border px-4 py-4 text-left transition-all duration-150",
                      selected
                        ? "border-pine/40 bg-paper-card shadow-panel"
                        : "border-transparent hover:border-line hover:bg-paper-card/70",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-9 w-9 shrink-0 items-center justify-center rounded-md border",
                        selected ? "border-pine bg-pine text-ink-invert" : "border-line bg-paper-card text-pine",
                      )}
                    >
                      <Icon size={16} />
                    </span>
                    <span className="flex flex-col gap-1">
                      <span className="flex items-center gap-2">
                        <span className="font-mono text-[11px] text-ink-faint">0{index + 1}</span>
                        <span className="text-[15px] font-semibold text-ink">{step.title}</span>
                        <span className="rounded-sm bg-paper-deep px-1.5 py-[1px] font-mono text-[10px] uppercase tracking-[0.1em] text-ink-muted">
                          {step.who}
                        </span>
                      </span>
                      {selected ? (
                        <span className="text-[13px] leading-relaxed text-ink-muted animate-fade-up">{step.body}</span>
                      ) : null}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
          <div className="surface relative overflow-hidden px-5 py-6 shadow-panel sm:px-7">
            <div className="absolute inset-0 -z-0 grid-paper opacity-40" />
            <div key={active} className="relative animate-fade-up">
              <StepPreview index={active} />
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}
