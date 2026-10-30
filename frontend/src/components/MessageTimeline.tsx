import type { Message } from "../lib/types";
import { formatDateTime } from "../lib/format";
import { cn } from "../lib/cn";

export function MessageTimeline({ messages, compact = false }: { messages: Message[]; compact?: boolean }) {
  return (
    <ol className="flex flex-col">
      {messages.map((message, index) => (
        <li
          key={message.id}
          className={cn(
            "relative flex flex-col gap-2 pb-5 pl-6",
            index === messages.length - 1 ? "pb-0" : "",
          )}
        >
          <span
            className={cn(
              "absolute left-0 top-1.5 h-2 w-2 rounded-full ring-4 ring-paper-card",
              message.author === "CLIENT" ? "bg-pine" : "bg-flag-warn",
            )}
          />
          {index !== messages.length - 1 ? (
            <span className="absolute bottom-0 left-[3.5px] top-4 w-px bg-line" />
          ) : null}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-[12px] font-semibold tracking-[-0.01em] text-ink">
              {message.author === "CLIENT" ? "Client" : "Studio"}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
              rev {message.revision}
            </span>
            <span className="font-mono text-[10px] text-ink-faint">
              {formatDateTime(message.created_at)}
            </span>
          </div>
          <p
            className={cn(
              "whitespace-pre-line text-[13px] leading-relaxed text-ink-muted",
              compact ? "line-clamp-3" : "",
            )}
          >
            {message.body}
          </p>
          {message.budget_minor !== null || message.deadline ? (
            <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10px] uppercase tracking-[0.1em] text-ink-faint">
              {message.budget_minor !== null ? (
                <span>budget {(message.budget_minor / 100).toFixed(2)} usd</span>
              ) : null}
              {message.deadline ? <span>live by {message.deadline}</span> : null}
              {message.assets_ready === false ? <span>assets pending</span> : null}
            </div>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
