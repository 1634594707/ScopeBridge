import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions, meta }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-5 pb-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex max-w-[62ch] flex-col gap-2">
          <span className="label">{eyebrow}</span>
          <h1 className="text-[30px] font-semibold leading-[1.15] tracking-[-0.025em] text-ink sm:text-[34px]">
            {title}
          </h1>
          {description ? (
            <p className="text-[14px] leading-relaxed text-ink-muted">{description}</p>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </div>
      {meta ? <div className="flex flex-wrap items-center gap-x-6 gap-y-2">{meta}</div> : null}
      <div className="hairline animate-rule-in origin-left" />
    </div>
  );
}

export function MetaItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="label">{label}</span>
      <span className="text-[13px] font-medium text-ink">{value}</span>
    </div>
  );
}
