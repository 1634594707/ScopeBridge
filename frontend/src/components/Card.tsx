import type { ReactNode } from "react";
import { cn } from "../lib/cn";

interface CardProps {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article" | "aside";
}

export function Card({ children, className, as: Tag = "section" }: CardProps) {
  return <Tag className={cn("surface", className)}>{children}</Tag>;
}

interface CardHeaderProps {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function CardHeader({ eyebrow, title, description, action, className }: CardHeaderProps) {
  return (
    <header className={cn("flex items-start justify-between gap-4 px-5 pt-5", className)}>
      <div className="flex flex-col gap-1">
        {eyebrow ? <span className="label">{eyebrow}</span> : null}
        <h2 className="text-[17px] font-semibold tracking-[-0.015em] text-ink">{title}</h2>
        {description ? (
          <p className="max-w-prose text-[13px] leading-relaxed text-ink-muted">{description}</p>
        ) : null}
      </div>
      {action}
    </header>
  );
}
