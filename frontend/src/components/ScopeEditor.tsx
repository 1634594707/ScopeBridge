import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Calculator } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { formatMoney } from "../lib/format";
import type { ServiceRules } from "../lib/types";
import { Button } from "./Button";
import { Field, Input } from "./Field";
import { cn } from "../lib/cn";

interface ScopeEditorProps {
  requirementId: string;
  revision: number;
  rules: ServiceRules;
  usedAtThisRevision: number;
}

export function ScopeEditor({ requirementId, revision, rules, usedAtThisRevision }: ScopeEditorProps) {
  const queryClient = useQueryClient();
  const [label, setLabel] = useState("");
  const [pages, setPages] = useState(1);
  const [addons, setAddons] = useState<string[]>([]);
  const [features, setFeatures] = useState<string[]>(["landing_pages"]);
  const [assetsReady, setAssetsReady] = useState(true);

  const create = useMutation({
    mutationFn: () =>
      api.createProposal(requirementId, {
        label: label.trim() || `${pages} page${pages > 1 ? "s" : ""} option`,
        pages,
        addon_codes: addons,
        requested_features: features,
        assets_ready: assetsReady,
      }),
    onSuccess: () => {
      setLabel("");
      queryClient.invalidateQueries({ queryKey: ["proposals", requirementId] });
      queryClient.invalidateQueries({ queryKey: ["requirement", requirementId] });
    },
  });

  const toggle = (list: string[], value: string) =>
    list.includes(value) ? list.filter((item) => item !== value) : [...list, value];

  const limitReached = usedAtThisRevision >= 2;
  const error = create.error instanceof ApiError ? create.error : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="label">Scope editor</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
          rev {revision} · {usedAtThisRevision}/2 used
        </span>
      </div>

      <Field label="Option label" htmlFor="scope-label" hint="Shown to the client on the comparison card.">
        <Input
          id="scope-label"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          placeholder="One-page launch with external ordering"
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Pages" htmlFor="scope-pages">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setPages((value) => Math.max(1, value - 1))}
              aria-label="Fewer pages"
            >
              −
            </Button>
            <Input
              id="scope-pages"
              type="number"
              min={1}
              max={20}
              value={pages}
              onChange={(event) => setPages(Math.min(20, Math.max(1, Number(event.target.value) || 1)))}
              className="text-center"
            />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setPages((value) => Math.min(20, value + 1))}
              aria-label="More pages"
            >
              +
            </Button>
          </div>
        </Field>

        <Field label="Assets" htmlFor="scope-assets" hint="Drives the earliest delivery date.">
          <button
            id="scope-assets"
            type="button"
            onClick={() => setAssetsReady((value) => !value)}
            className={cn(
              "flex h-10 cursor-pointer items-center justify-between rounded-md border px-3 text-[13px] transition-colors duration-150",
              assetsReady
                ? "border-pine bg-pine-wash text-pine-deep"
                : "border-line bg-paper-card text-ink-muted hover:border-ink/25",
            )}
            aria-pressed={assetsReady}
          >
            {assetsReady ? "Ready to build" : "Still collecting"}
            <span className="font-mono text-[10px] uppercase tracking-[0.12em]">
              {assetsReady ? "on" : "off"}
            </span>
          </button>
        </Field>
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-[13px] font-medium text-ink">Add-ons</legend>
        <div className="flex flex-col divide-y divide-line rounded-md border border-line">
          {rules.addons.map((addon) => (
            <label
              key={addon.code}
              className="flex cursor-pointer items-start justify-between gap-3 px-3 py-2.5 hover:bg-paper"
            >
              <span className="flex flex-col gap-0.5">
                <span className="text-[13px] text-ink">{addon.label}</span>
                <span className="text-[11px] leading-relaxed text-ink-faint">{addon.description}</span>
              </span>
              <span className="flex items-center gap-3">
                <span className="numeric text-[12px] text-ink-muted">
                  {addon.amount_minor === 0
                    ? "included"
                    : formatMoney(addon.amount_minor, rules.currency)}
                </span>
                <input
                  type="checkbox"
                  checked={addons.includes(addon.code)}
                  onChange={() => setAddons((current) => toggle(current, addon.code))}
                  className="h-4 w-4 cursor-pointer accent-pine"
                />
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-[13px] font-medium text-ink">Requested features</legend>
        <div className="flex flex-wrap gap-1.5">
          {["on_site_ordering", "payment_integration", ...rules.capabilities].map((feature) => (
            <button
              key={feature}
              type="button"
              onClick={() => setFeatures((current) => toggle(current, feature))}
              className={cn(
                "cursor-pointer rounded-sm border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.1em] transition-colors duration-150",
                features.includes(feature)
                  ? "border-pine bg-pine-wash text-pine-deep"
                  : "border-line bg-paper-card text-ink-muted hover:border-ink/25",
              )}
              aria-pressed={features.includes(feature)}
            >
              {feature.replace(/_/g, " ")}
            </button>
          ))}
        </div>
        <p className="text-[11px] leading-relaxed text-ink-faint">
          Features outside the price list are refused by the rule check, not quietly dropped.
        </p>
      </fieldset>

      {error ? (
        <p className=" rounded-md border border-flag-bad/30 bg-flag-bad/5 px-3 py-2 text-[12px] text-flag-bad">
          {error.message}
        </p>
      ) : null}

      <Button
        type="button"
        busy={create.isPending}
        disabled={limitReached}
        icon={<Calculator size={15} />}
        onClick={() => create.mutate()}
      >
        {limitReached ? "Two options already priced" : "Price this scope"}
      </Button>
      <p className="font-mono text-[10px] uppercase leading-relaxed tracking-[0.1em] text-ink-faint">
        The server prices and judges the scope. No amount is sent from this form.
      </p>
    </div>
  );
}
