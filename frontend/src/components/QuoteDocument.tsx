import { useState, type ReactNode } from "react";
import type { Message, Quote } from "../lib/types";
import { formatDate, formatDateTime } from "../lib/format";
import { Money } from "./Money";
import { RuleChip, SourceChip } from "./Tag";
import { StatusPill } from "./StatusPill";
import { cn } from "../lib/cn";

interface QuoteDocumentProps {
  quote: Quote;
  messages: Message[];
  actions?: ReactNode;
  clientName?: string;
  clientBusiness?: string;
}

export function QuoteDocument({ quote, messages, actions, clientName, clientBusiness }: QuoteDocumentProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const messageById = new Map(messages.map((message) => [message.id, message]));

  return (
    <article className="surface overflow-hidden">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <span className="label">Quote · v{quote.quote_number}</span>
            <StatusPill status={quote.status} />
          </div>
          <h2 className="text-[20px] font-semibold tracking-[-0.02em] text-ink">
            {clientBusiness || clientName || "Client agreement"}
          </h2>
          <p className="max-w-prose text-[13px] leading-relaxed text-ink-muted">{quote.scope_summary}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Money amountMinor={quote.total_minor} currency={quote.currency} size="xl" />
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
            total, this version
          </span>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-x-6 gap-y-2 border-b border-line px-5 py-3 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint sm:px-6">
        <span className="whitespace-nowrap">Issued {formatDate(quote.created_at)}</span>
        <span className="whitespace-nowrap">Brief at rev {quote.source_revision}</span>
        <span className="whitespace-nowrap">Reviewed {formatDateTime(quote.reviewed_at)}</span>
        <span className="whitespace-nowrap">Valid until {formatDate(quote.expires_at)}</span>
      </div>

      <div className="px-5 py-2 sm:px-6">
        <ul className="flex flex-col">
          {quote.items.map((item) => {
            const source = item.source_message_id ? messageById.get(item.source_message_id) : undefined;
            const isOpen = expanded === item.id;
            return (
              <li
                key={item.id}
                className={cn(
                  "border-b border-line/70 py-3 last:border-b-0",
                  item.included ? "" : "opacity-80",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex min-w-0 flex-col gap-1.5">
                    <span
                      className={cn(
                        "text-[14px] leading-snug",
                        item.included ? "text-ink" : "text-ink-faint line-through decoration-line",
                      )}
                    >
                      {item.label}
                    </span>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <RuleChip ruleRef={item.rule_ref} />
                      {item.included ? (
                        <SourceChip
                          revision={source ? source.revision : null}
                          expanded={isOpen}
                          onClick={() => setExpanded(isOpen ? null : item.id)}
                        />
                      ) : (
                        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
                          excluded by scope
                        </span>
                      )}
                    </div>
                  </div>
                  <Money
                    amountMinor={item.amount_minor}
                    currency={quote.currency}
                    size="sm"
                    tone={item.included ? "default" : "muted"}
                  />
                </div>

                {isOpen && source ? (
                  <div className="mt-3 rounded-md border border-pine/20 bg-pine-wash/50 px-3 py-2.5">
                    <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-pine-deep">
                      client message · rev {source.revision}
                    </span>
                    <p className="mt-1 whitespace-pre-line text-[12px] leading-relaxed text-pine-deep/85">
                      {source.body}
                    </p>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>

      {actions ? (
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-paper px-5 py-4 sm:px-6">
          {actions}
        </footer>
      ) : null}
    </article>
  );
}
