import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Clock3, ShieldCheck } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { rememberPortalToken } from "../lib/customerToken";
import { formatMoney, isoInDays } from "../lib/format";
import { Button } from "../components/Button";
import { Card, CardHeader } from "../components/Card";
import { Field, Input, TextArea } from "../components/Field";
import { PageHeader } from "../components/PageHeader";

interface FormState {
  name: string;
  business: string;
  email: string;
  brief: string;
  budget: string;
  deadline: string;
  assetsReady: boolean;
}

const initialForm: FormState = {
  name: "",
  business: "",
  email: "",
  brief: "",
  budget: "500",
  deadline: isoInDays(21),
  assetsReady: false,
};

export default function StartPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(initialForm);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const rules = useQuery({ queryKey: ["service-rules"], queryFn: api.serviceRules });

  const create = useMutation({
    mutationFn: api.createRequirement,
    onSuccess: (data) => {
      rememberPortalToken(data.portal_token);
      navigate(`/r/${data.portal_token}`);
    },
  });

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: "" }));
  };

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (form.name.trim().length < 2) nextErrors.name = "Tell us who to address the quote to.";
    if (form.brief.trim().length < 20) {
      nextErrors.brief = "Describe the work in at least a sentence or two.";
    }
    const budgetValue = Number(form.budget);
    if (!Number.isFinite(budgetValue) || budgetValue <= 0) {
      nextErrors.budget = "Enter the budget you can actually approve.";
    }
    if (!form.deadline) nextErrors.deadline = "Pick the date you want it live.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    create.mutate({
      client_name: form.name.trim(),
      client_business: form.business.trim(),
      client_email: form.email.trim(),
      message: form.brief.trim(),
      budget_minor: Math.round(budgetValue * 100),
      deadline: form.deadline,
      assets_ready: form.assetsReady,
    });
  };

  const error = create.error instanceof ApiError ? create.error : null;

  return (
    <div>
      <PageHeader
        eyebrow="Client intake"
        title="Tell the studio what you need."
        description="Write it the way you would in an email. The desk separates budget, deadline and material conditions, then returns scopes you can actually choose between."
        meta={
          <>
            <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-faint">
              <Clock3 size={13} /> Takes about two minutes
            </span>
            <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-faint">
              <ShieldCheck size={13} /> No card details, sandbox only
            </span>
          </>
        }
      />

      <div className="grid gap-8 lg:grid-cols-[1.35fr_0.65fr]">
        <Card className="px-5 py-6 sm:px-7">
          <form onSubmit={submit} className="flex flex-col gap-5">
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Your name" htmlFor="client-name" error={errors.name}>
                <Input
                  id="client-name"
                  value={form.name}
                  onChange={(event) => update("name", event.target.value)}
                  placeholder="Maya Ortiz"
                  autoComplete="name"
                />
              </Field>
              <Field label="Business" htmlFor="client-business" hint="Optional, shown on the quote.">
                <Input
                  id="client-business"
                  value={form.business}
                  onChange={(event) => update("business", event.target.value)}
                  placeholder="Fern & Filter Coffee"
                  autoComplete="organization"
                />
              </Field>
            </div>

            <Field label="Email" htmlFor="client-email" hint="Only used on this local demo build.">
              <Input
                id="client-email"
                type="email"
                value={form.email}
                onChange={(event) => update("email", event.target.value)}
                placeholder="maya@fernandfilter.example"
                autoComplete="email"
              />
            </Field>

            <Field
              label="What do you need built?"
              htmlFor="client-brief"
              error={errors.brief}
              hint="Include the pages you have in mind, any ordering or booking features, and what already exists."
            >
              <TextArea
                id="client-brief"
                value={form.brief}
                onChange={(event) => update("brief", event.target.value)}
                placeholder="We are opening a second coffee bar and need a three page website with online ordering. Our budget is $500 and we would like it live in three weeks. We have a logo but no photos or copy yet."
                rows={6}
              />
            </Field>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field
                label="Budget (USD)"
                htmlFor="client-budget"
                error={errors.budget}
                hint="A number the studio can hold you to."
              >
                <Input
                  id="client-budget"
                  type="number"
                  min={0}
                  step="any"
                  value={form.budget}
                  onChange={(event) => update("budget", event.target.value)}
                  placeholder="500"
                />
              </Field>
              <Field label="Live by" htmlFor="client-deadline" error={errors.deadline}>
                <Input
                  id="client-deadline"
                  type="date"
                  value={form.deadline}
                  onChange={(event) => update("deadline", event.target.value)}
                />
              </Field>
            </div>

            <fieldset className="flex flex-col gap-2">
              <legend className="text-[13px] font-medium text-ink">Are your materials ready?</legend>
              <div className="flex flex-wrap gap-2">
                {[
                  { value: true, label: "Ready to hand over" },
                  { value: false, label: "Still gathering photos and copy" },
                ].map((option) => (
                  <button
                    key={String(option.value)}
                    type="button"
                    onClick={() => update("assetsReady", option.value)}
                    className={`cursor-pointer rounded-md border px-3 py-2 text-[13px] transition-colors duration-150 ${
                      form.assetsReady === option.value
                        ? "border-pine bg-pine-wash text-pine-deep"
                        : "border-line bg-paper-card text-ink-muted hover:border-ink/25 hover:text-ink"
                    }`}
                    aria-pressed={form.assetsReady === option.value}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <p className="text-[12px] leading-relaxed text-ink-faint">
                Missing assets do not block the quote, but they push the earliest delivery date.
              </p>
            </fieldset>

            {error ? (
              <p className="rounded-md border border-flag-bad/30 bg-flag-bad/5 px-3 py-2 text-[13px] text-flag-bad">
                {error.message}
              </p>
            ) : null}

            <div className="flex items-center justify-between gap-4 border-t border-line pt-4">
              <p className="max-w-[38ch] text-[12px] leading-relaxed text-ink-faint">
                You will get a private link to this brief. No account, no payment yet.
              </p>
              <Button type="submit" busy={create.isPending} icon={<ArrowRight size={15} />}>
                Send brief
              </Button>
            </div>
          </form>
        </Card>

        <aside className="flex flex-col gap-5">
          <Card className="px-5 py-5">
            <CardHeader
              eyebrow="Current price list"
              title="Studio terms"
              description="Fixed demo rates. The server applies them; nobody types the total."
            />
            <dl className="mt-4 flex flex-col divide-y divide-line">
              <div className="flex items-baseline justify-between py-2.5">
                <dt className="text-[13px] text-ink-muted">First page</dt>
                <dd className="numeric text-[13px] text-ink">
                  {rules.data ? formatMoney(rules.data.base_page_minor, rules.data.currency) : "—"}
                </dd>
              </div>
              <div className="flex items-baseline justify-between py-2.5">
                <dt className="text-[13px] text-ink-muted">Each extra page</dt>
                <dd className="numeric text-[13px] text-ink">
                  {rules.data ? formatMoney(rules.data.extra_page_minor, rules.data.currency) : "—"}
                </dd>
              </div>
              {rules.data?.addons
                .filter((addon) => addon.amount_minor > 0)
                .map((addon) => (
                  <div key={addon.code} className="flex items-baseline justify-between gap-4 py-2.5">
                    <dt className="text-[13px] text-ink-muted">{addon.label}</dt>
                    <dd className="numeric shrink-0 text-[13px] text-ink">
                      {formatMoney(addon.amount_minor, rules.data.currency)}
                    </dd>
                  </div>
                ))}
            </dl>
            <p className="mt-3 border-t border-line pt-3 text-[12px] leading-relaxed text-ink-faint">
              {rules.data
                ? `${rules.data.lead_time_days} working days from assets, ${rules.data.revisions_included} revision rounds included.`
                : "Loading terms…"}
            </p>
          </Card>

          <Card className="px-5 py-5">
            <span className="label">What happens next</span>
            <ol className="mt-3 flex flex-col gap-3">
              {[
                "The desk checks your budget, deadline and features against the studio's real capacity.",
                "You get up to two scopes side by side, including the one that cannot be met and why.",
                "The studio reviews the version you pick, you confirm that exact version, then payment opens.",
              ].map((line, index) => (
                <li key={line} className="flex gap-3">
                  <span className="mt-0.5 font-mono text-[11px] text-pine">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="text-[13px] leading-relaxed text-ink-muted">{line}</span>
                </li>
              ))}
            </ol>
          </Card>
        </aside>
      </div>
    </div>
  );
}
