import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card } from "../components/Card";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { Tag } from "../components/Tag";

export default function RulesPage() {
  const rules = useQuery({ queryKey: ["service-rules"], queryFn: api.serviceRules });

  if (rules.isLoading) {
    return <div className="py-20 text-sm text-ink-faint">Loading the price list…</div>;
  }

  if (!rules.data) {
    return <div className="py-20 text-sm text-flag-bad">The price list could not be loaded.</div>;
  }

  const data = rules.data;

  return (
    <div>
      <PageHeader
        eyebrow="Published terms"
        title="The studio's price list, in one place."
        description="These numbers are what the server uses to price a scope. Changing any of them creates a new rule version; quotes already issued keep their original numbers."
        meta={
          <>
            <span className="flex items-baseline gap-2">
              <span className="label">Version</span>
              <span className="font-mono text-[12px]">v{data.version_no}</span>
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Currency</span>
              <span className="font-mono text-[12px]">{data.currency}</span>
            </span>
            <span className="flex items-baseline gap-2">
              <span className="label">Lead time</span>
              <span className="font-mono text-[12px]">{data.lead_time_days} working days</span>
            </span>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4">
            <span className="label">Base work</span>
          </div>
          <ul className="divide-y divide-line">
            <li className="flex items-baseline justify-between px-5 py-4">
              <div className="flex flex-col gap-0.5">
                <span className="text-[14px] text-ink">First page</span>
                <span className="font-mono text-[11px] text-ink-faint">rule.base_page</span>
              </div>
              <Money amountMinor={data.base_page_minor} currency={data.currency} />
            </li>
            <li className="flex items-baseline justify-between px-5 py-4">
              <div className="flex flex-col gap-0.5">
                <span className="text-[14px] text-ink">Each additional page</span>
                <span className="font-mono text-[11px] text-ink-faint">rule.extra_page</span>
              </div>
              <Money amountMinor={data.extra_page_minor} currency={data.currency} />
            </li>
            <li className="flex items-baseline justify-between px-5 py-4">
              <div className="flex flex-col gap-0.5">
                <span className="text-[14px] text-ink">Revision rounds included</span>
                <span className="font-mono text-[11px] text-ink-faint">rule.revisions</span>
              </div>
              <span className="numeric text-[15px]">{data.revisions_included}</span>
            </li>
            <li className="flex items-baseline justify-between px-5 py-4">
              <div className="flex flex-col gap-0.5">
                <span className="text-[14px] text-ink">Asset collection buffer</span>
                <span className="font-mono text-[11px] text-ink-faint">rule.lead_time</span>
              </div>
              <span className="numeric text-[15px]">{data.asset_buffer_days} working days</span>
            </li>
          </ul>
        </Card>

        <div className="flex flex-col gap-6">
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <span className="label">Add-ons</span>
              <Tag>{data.addons.length}</Tag>
            </div>
            <ul className="divide-y divide-line">
              {data.addons.map((addon) => (
                <li key={addon.code} className="flex items-start justify-between gap-4 px-5 py-3.5">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[13px] font-medium text-ink">{addon.label}</span>
                    <span className="text-[12px] leading-relaxed text-ink-muted">
                      {addon.description}
                    </span>
                    <span className="font-mono text-[10px] text-ink-faint">
                      rule.addon.{addon.code}
                    </span>
                  </div>
                  <Money
                    amountMinor={addon.amount_minor}
                    currency={data.currency}
                    size="sm"
                    tone={addon.amount_minor === 0 ? "muted" : "default"}
                  />
                </li>
              ))}
            </ul>
          </Card>

          <Card className="px-5 py-4">
            <span className="label">Services offered</span>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {data.capabilities.map((capability) => (
                <Tag key={capability} tone="good">
                  {capability.replace(/_/g, " ")}
                </Tag>
              ))}
            </div>
            <div className="mt-4 border-t border-line pt-3">
              <span className="label">Never included</span>
              <ul className="mt-2 flex flex-col gap-1">
                {data.exclusions.map((exclusion) => (
                  <li key={exclusion} className="text-[12px] text-ink-muted">
                    {exclusion}
                  </li>
                ))}
              </ul>
            </div>
            <p className="mt-4 border-t border-line pt-3 text-[12px] leading-relaxed text-ink-faint">
              {data.notes}
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
