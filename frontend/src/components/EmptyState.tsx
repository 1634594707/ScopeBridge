import type { ReactNode } from "react";

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-lg border border-dashed border-line bg-paper-card/60 px-5 py-8">
      <span className="label">Nothing here yet</span>
      <h3 className="text-[15px] font-semibold text-ink">{title}</h3>
      <p className="max-w-prose text-[13px] leading-relaxed text-ink-muted">{body}</p>
      {action ? <div className="pt-2">{action}</div> : null}
    </div>
  );
}
