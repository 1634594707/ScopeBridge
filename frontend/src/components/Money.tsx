import { cn } from "../lib/cn";
import { formatMoney } from "../lib/format";

interface MoneyProps {
  amountMinor: number;
  currency?: string;
  size?: "sm" | "md" | "lg" | "xl";
  tone?: "default" | "muted" | "positive" | "negative";
  className?: string;
}

const sizes = {
  sm: "text-[13px]",
  md: "text-[15px]",
  lg: "text-[22px]",
  xl: "text-[32px]",
};

const tones = {
  default: "text-ink",
  muted: "text-ink-muted",
  positive: "text-flag-good",
  negative: "text-flag-bad",
};

export function Money({ amountMinor, currency = "USD", size = "md", tone = "default", className }: MoneyProps) {
  return (
    <span
      className={cn(
        "numeric whitespace-nowrap tracking-[-0.01em]",
        sizes[size],
        tones[tone],
        className,
      )}
    >
      {formatMoney(amountMinor, currency)}
    </span>
  );
}
