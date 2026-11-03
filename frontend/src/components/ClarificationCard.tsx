import { useState } from "react";
import type { Clarification } from "../lib/types";
import { formatDateTime } from "../lib/format";
import { Button } from "./Button";
import { Card, CardHeader } from "./Card";
import { Field, TextArea } from "./Field";
import { Tag } from "./Tag";

type ManualReason =
  | "model_not_configured"
  | "model_unavailable"
  | "model_output_invalid";

interface ClarificationCardProps {
  clarification: Clarification | null;
  mode: "seller" | "client";
  busy?: boolean;
  error?: string;
  onConfirm?: (
    answers: string,
    acknowledged: boolean,
    acknowledgedUnsupported: boolean,
  ) => void;
  onManual?: (note: string, reason: ManualReason) => void;
}

const reasonLabels: Record<ManualReason, string> = {
  model_not_configured: "Model is not configured",
  model_unavailable: "Model call failed",
  model_output_invalid: "Model output was rejected",
};

export function ClarificationCard({
  clarification,
  mode,
  busy,
  error,
  onConfirm,
  onManual,
}: ClarificationCardProps) {
  const [answers, setAnswers] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [acknowledgedUnsupported, setAcknowledgedUnsupported] = useState(false);
  const [note, setNote] = useState("");
  const [reason, setReason] = useState<ManualReason>("model_not_configured");

  return (
    <Card className="px-5 py-5">
      <CardHeader
        eyebrow="Clarification"
        title="What the studio needs to clarify"
        description="The model extracts facts and questions; it never sets a price. A quote needs a confirmed clarification for this exact revision."
      />

      {clarification ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Tag tone={clarification.kind === "MANUAL" ? "warn" : "neutral"}>
            {clarification.kind === "AI" ? "AI-assisted" : "Manual, not AI-assisted"}
          </Tag>
          <Tag tone={clarification.status === "CONFIRMED" ? "good" : "warn"}>
            {clarification.status === "CONFIRMED" ? "Confirmed" : "Awaiting client"}
          </Tag>
          <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">
            rev {clarification.source_revision}
          </span>
        </div>
      ) : null}

      {clarification?.kind === "MANUAL" ? (
        <p className="mt-3 rounded-md border border-flag-warn/30 bg-flag-warn/5 px-3 py-2 text-[12px] leading-relaxed text-flag-warn">
          Manual clarification, not AI-assisted. Reason:{" "}
          {clarification.reason_code ?? "unknown"}. {clarification.note}
        </p>
      ) : null}

      {clarification?.questions.length ? (
        <div className="mt-4 flex flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            Questions
          </span>
          <ul className="flex flex-col gap-1">
            {clarification.questions.map((question) => (
              <li key={question} className="text-[12px] leading-relaxed text-ink-muted">
                — {question}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {clarification?.unsupported_requests.length ? (
        <div className="mt-4 flex flex-col gap-1.5">
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            Asked for but not offered
          </span>
          <div className="flex flex-wrap gap-1.5">
            {clarification.unsupported_requests.map((request) => (
              <Tag key={request} tone="warn">
                {request.replace(/_/g, " ")}
              </Tag>
            ))}
          </div>
        </div>
      ) : null}

      {clarification?.status === "CONFIRMED" && clarification.answers ? (
        <p className="mt-4 rounded-md border border-line bg-paper px-3 py-2 text-[12px] leading-relaxed text-ink-muted">
          Client answer: {clarification.answers}
        </p>
      ) : null}

      {clarification?.confirmed_at ? (
        <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">
          confirmed {formatDateTime(clarification.confirmed_at)}
        </p>
      ) : null}

      {mode === "client" && clarification?.kind === "AI" && clarification.status === "PENDING" ? (
        <div className="mt-4 flex flex-col gap-3 border-t border-line pt-4">
          <Field
            label="Your answers"
            htmlFor="clarification-answers"
            hint="Answer the questions above; if there are none, confirm that you reviewed the model facts."
          >
            <TextArea
              id="clarification-answers"
              value={answers}
              onChange={(event) => setAnswers(event.target.value)}
              rows={3}
              placeholder="Photos will be ready next week; the menu link is correct."
            />
          </Field>
          <label className="flex items-start gap-2 text-[12px] leading-relaxed text-ink-muted">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
              className="mt-0.5 h-4 w-4 accent-pine"
            />
            I reviewed the model facts and the questions for this revision.
          </label>
          {clarification.unsupported_requests.length ? (
            <label className="flex items-start gap-2 text-[12px] leading-relaxed text-ink-muted">
              <input
                type="checkbox"
                checked={acknowledgedUnsupported}
                onChange={(event) => setAcknowledgedUnsupported(event.target.checked)}
                className="mt-0.5 h-4 w-4 accent-pine"
              />
              I acknowledge the capabilities the studio does not offer.
            </label>
          ) : null}
          <Button
            type="button"
            busy={busy}
            disabled={
              !acknowledged ||
              (clarification.questions.length > 0 && answers.trim().length === 0) ||
              (clarification.unsupported_requests.length > 0 && !acknowledgedUnsupported)
            }
            onClick={() => onConfirm?.(answers, acknowledged, acknowledgedUnsupported)}
          >
            Confirm clarification
          </Button>
        </div>
      ) : null}

      {mode === "seller" && clarification?.status === "PENDING" ? (
        <p className="mt-4 text-[12px] leading-relaxed text-flag-warn">
          Waiting for the client to answer/confirm. You cannot issue a quote until this revision is
          clarified.
        </p>
      ) : null}

      {mode === "client" && !clarification ? (
        <p className="mt-4 text-[12px] leading-relaxed text-ink-muted">
          The studio has not recorded a clarification for this revision yet. A quote cannot be
          issued until it does.
        </p>
      ) : null}

      {mode === "seller" && !clarification ? (
        <div className="mt-4 flex flex-col gap-3 border-t border-line pt-4">
          <p className="rounded-md border border-flag-warn/30 bg-flag-warn/5 px-3 py-2 text-[12px] leading-relaxed text-flag-warn">
            No clarification for this revision. Run the model draft first. Manual clarification is
            only for an unavailable or failed model and is marked “manual, not AI-assisted”.
          </p>
          <Field label="What did you check?" htmlFor="manual-clarification-note">
            <TextArea
              id="manual-clarification-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              placeholder="Model is not configured; I checked budget, deadline and features by hand."
            />
          </Field>
          <Field label="Why manual?" htmlFor="manual-clarification-reason">
            <select
              id="manual-clarification-reason"
              value={reason}
              onChange={(event) => setReason(event.target.value as ManualReason)}
              className="h-10 w-full rounded-md border border-line bg-paper-card px-3 text-[13px] text-ink"
            >
              {Object.entries(reasonLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Button
            type="button"
            variant="secondary"
            busy={busy}
            disabled={note.trim().length < 10}
            onClick={() => onManual?.(note.trim(), reason)}
          >
            Record manual clarification
          </Button>
        </div>
      ) : null}

      {error ? (
        <p className="mt-3 text-[12px] leading-relaxed text-flag-bad">{error}</p>
      ) : null}
    </Card>
  );
}
