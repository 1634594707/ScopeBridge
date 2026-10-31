import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Calculator, Minus, Plus } from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/cn";
import type { ServiceRules } from "../lib/types";
import { Button } from "./Button";
import { Card } from "./Card";
import { EndpointNotice } from "./EndpointNotice";
import { Money } from "./Money";
import { RuleChip } from "./Tag";

const MIN_PAGES = 1;
const MAX_PAGES = 20;

/**
 * Lets anyone price a scope against the published rules before writing a brief.
 * The browser only sends the choices (page count and add-on codes); the total
 * and every line come back from the server. The component never adds amounts up.
 */
export function ScopeEstimator({ rules }: { rules: ServiceRules }) {
  const [pages, setPages] = useState(1);
  const [addons, setAddons] = useState<string[]>([]);

  const estimate = useMutation({
    mutationFn: (payload: { pages: number; addon_codes: string[] }) => api.estimateScope(payload),
  });

  const result = estimate.data;
  const sent = estimate.variables;
  const stale =
    result !== undefined &&
    sent !== undefined &&
    (sent.pages !== pages ||
      sent.addon_codes.length !== addons.length ||
      sent.addon_codes.some((code) => !addons.includes(code)));

  function toggle(code: string) {
    setAddons((current) => (current.includes(code) ? current.filter((value) => value !== code) : [...current, code]));
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
        <div className="flex flex-col gap-1">
          <span className="flex items-center gap-2 text-[15px] font-semibold text-ink">
            <Calculator size={15} className="text-pine" /> Scope estimator
          </span>
          <span className="text-[12.5px] leading-relaxed text-ink-muted">
            Choose a scope and the server prices it with rule version v{rules.version_no}. This is an
            estimate, not a quote; only the studio can issue one.
          </span>
        </div>
      </div>

      <div className="grid gap-px bg-line lg:grid-cols-[1fr_1fr]">
        <div className="flex flex-col gap-5 bg-paper-card px-5 py-5">
          <div className="flex items-center justify-between">
            <span className="flex flex-col gap-0.5">
              <span className="text-[13px] font-medium text-ink">Pages</span>
              <span className="font-mono text-[10px] text-ink-faint">1 to {MAX_PAGES}</span>
            </span>
            <div className="flex items-center rounded-md border border-line">
              <button
                type="button"
                aria-label="Fewer pages"
                onClick={() => setPages((value) => Math.max(MIN_PAGES, value - 1))}
                disabled={pages <= MIN_PAGES}
                className="cursor-pointer p-2 text-ink-muted hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Minus size={14} />
              </button>
              <span className="numeric w-10 text-center text-[15px] text-ink">{pages}</span>
              <button
                type="button"
                aria-label="More pages"
                onClick={() => setPages((value) => Math.min(MAX_PAGES, value + 1))}
                disabled={pages >= MAX_PAGES}
                className="cursor-pointer p-2 text-ink-muted hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Plus size={14} />
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <span className="text-[13px] font-medium text-ink">Add-ons</span>
            {rules.addons.length === 0 ? (
              <span className="text-[12px] text-ink-faint">This rule version publishes no add-ons.</span>
            ) : (
              <div className="flex flex-wrap gap-2">
                {rules.addons.map((addon) => {
                  const selected = addons.includes(addon.code);
                  return (
                    <button
                      key={addon.code}
                      type="button"
                      onClick={() => toggle(addon.code)}
                      aria-pressed={selected}
                      className={cn(
                        "cursor-pointer rounded-md border px-3 py-1.5 text-[12px] transition-colors duration-150",
                        selected
                          ? "border-pine bg-pine-wash text-pine-deep"
                          : "border-line text-ink-muted hover:border-ink/25 hover:text-ink",
                      )}
                    >
                      {addon.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <Button
            onClick={() => estimate.mutate({ pages, addon_codes: addons })}
            busy={estimate.isPending}
            className="self-start"
          >
            Price this scope
          </Button>
        </div>

        <div className="flex flex-col gap-3 bg-paper px-5 py-5">
          <span className="label">Server estimate</span>
          {estimate.error ? (
            <EndpointNotice
              error={estimate.error}
              endpoint="POST /api/service-rules/estimate"
              feature="The scope estimator"
            />
          ) : result ? (
            <div className={cn("flex flex-col gap-3", stale && "opacity-50")}>
              <ul className="flex flex-col divide-y divide-line rounded-md border border-line bg-paper-card">
                {result.items.map((item) => (
                  <li key={`${item.code}-${item.rule_ref}`} className="flex items-start justify-between gap-3 px-3 py-2.5">
                    <span className="flex flex-col gap-1">
                      <span className="text-[13px] text-ink">{item.label}</span>
                      <RuleChip ruleRef={item.rule_ref} className="w-fit" />
                    </span>
                    <Money amountMinor={item.amount_minor} currency={result.currency} size="sm" />
                  </li>
                ))}
              </ul>
              <div className="flex items-baseline justify-between">
                <span className="text-[13px] text-ink-muted">Total · rules v{result.rule_version}</span>
                <Money amountMinor={result.total_minor} currency={result.currency} size="lg" />
              </div>
              {result.violations.map((violation) => (
                <p key={violation.code} className="rounded-md border border-flag-bad/30 bg-flag-bad/5 px-3 py-2 text-[12px] text-flag-bad">
                  {violation.detail} <span className="font-mono text-[10px]">{violation.rule_ref}</span>
                </p>
              ))}
              {stale ? (
                <p className="font-mono text-[11px] text-flag-warn">Choices changed. Price the scope again.</p>
              ) : null}
            </div>
          ) : (
            <p className="text-[13px] leading-relaxed text-ink-faint">
              No estimate yet. Pick pages and add-ons, then ask the server to price them.
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}
