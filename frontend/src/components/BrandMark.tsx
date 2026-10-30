import { cn } from "../lib/cn";

/**
 * ScopeBridge brand mark: a drafting scope frame, a ruled agreement line and
 * one solid block where the line is locked. The frame is the agreed scope, the
 * line is the priced agreement, the block is the single confirmed version.
 *
 * Geometry lives in a 48-unit space and is scaled into a 32-unit box so the
 * mark, the favicon and the UI tile share one proportion.
 */
const MARK_TRANSFORM = "translate(16 16) scale(0.56) translate(-24 -24)";

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" focusable="false">
      <g transform={MARK_TRANSFORM}>
        <g fill="none" stroke="currentColor" strokeLinecap="butt">
          <g strokeWidth="5">
            <path d="M7 19V7h12" />
            <path d="M29 7h12v12" />
            <path d="M7 29v12h12" />
            <path d="M29 41h12V29" />
          </g>
          <path d="M7 24h22" strokeWidth="3" />
        </g>
        <rect x="29" y="20" width="8" height="8" fill="currentColor" />
      </g>
    </svg>
  );
}

export function BrandTile({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-[5px] bg-pine text-ink-invert",
        className,
      )}
    >
      <BrandMark className="h-8 w-8" />
    </span>
  );
}
