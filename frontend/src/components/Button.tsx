import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "../lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  busy?: boolean;
  icon?: ReactNode;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-pine text-ink-invert border border-pine hover:bg-pine-deep hover:border-pine-deep active:translate-y-px",
  secondary:
    "bg-paper-card text-ink border border-line hover:border-ink/25 hover:bg-paper active:translate-y-px",
  ghost: "bg-transparent text-ink-muted border border-transparent hover:text-ink hover:bg-paper-deep",
  danger:
    "bg-transparent text-flag-bad border border-flag-bad/30 hover:bg-flag-bad/5 active:translate-y-px",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-[13px]",
  md: "h-10 px-4 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  busy = false,
  icon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || busy}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium tracking-[-0.01em] transition-colors duration-150",
        "disabled:cursor-not-allowed disabled:border-line disabled:bg-paper-deep disabled:text-ink-faint disabled:shadow-none",
        variants[variant],
        sizes[size],
        className,
      )}
    >
      {busy ? (
        <span className="h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}
