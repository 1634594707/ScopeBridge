import { useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CornerDownLeft, FileText, Search } from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/cn";
import type { AccountRole } from "../lib/types";

interface PaletteItem {
  id: string;
  label: string;
  hint: string;
  to: string;
  group: "Pages" | "Briefs";
}

const pages: Record<AccountRole, PaletteItem[]> = {
  SELLER: [
    { id: "p-console", label: "Console", hint: "Every brief on the desk", to: "/console", group: "Pages" },
    { id: "p-rules", label: "Price list", hint: "Published rule version", to: "/rules", group: "Pages" },
    { id: "p-home", label: "Overview", hint: "Product introduction", to: "/", group: "Pages" },
  ],
  CLIENT: [
    { id: "p-briefs", label: "My briefs", hint: "Everything you submitted", to: "/briefs", group: "Pages" },
    { id: "p-start", label: "New brief", hint: "Describe the work", to: "/start", group: "Pages" },
    { id: "p-rules", label: "Price list", hint: "Published rule version", to: "/rules", group: "Pages" },
    { id: "p-home", label: "Overview", hint: "Product introduction", to: "/", group: "Pages" },
  ],
};

/**
 * Keyboard jump list for signed-in accounts (Ctrl/⌘ + K). It only reads the
 * brief list the role already has access to; it never fetches anything new.
 */
export function useCommandPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return { open, setOpen };
}

export function CommandPalette({
  role,
  open,
  onClose,
}: {
  role: AccountRole;
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);

  const briefs = useQuery({
    queryKey: role === "SELLER" ? ["requirements"] : ["briefs"],
    queryFn: role === "SELLER" ? api.requirements : api.clientBriefs,
    enabled: open,
  });

  const items = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const briefItems: PaletteItem[] = (briefs.data ?? []).map((brief) => ({
      id: brief.id,
      label: brief.client_business || brief.client_name,
      hint: `${brief.client_name} · rev ${brief.revision} · ${brief.status.toLowerCase()}`,
      to: role === "SELLER" ? `/requirements/${brief.id}` : `/briefs/${brief.id}`,
      group: "Briefs",
    }));
    const all = [...pages[role], ...briefItems];
    if (!needle) return all;
    return all.filter((item) => `${item.label} ${item.hint}`.toLowerCase().includes(needle));
  }, [briefs.data, query, role]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setCursor(0);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    setCursor(0);
  }, [query]);

  if (!open) return null;

  const go = (item: PaletteItem | undefined) => {
    if (!item) return;
    onClose();
    navigate(item.to);
  };

  const onKeyDown = (event: ReactKeyboardEvent) => {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setCursor((value) => Math.min(value + 1, Math.max(items.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setCursor((value) => Math.max(value - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      go(items[cursor]);
    }
  };

  let lastGroup: string | null = null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-ink/25 px-4 pt-[12vh] backdrop-blur-[2px] animate-in fade-in duration-150"
      onMouseDown={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Jump to"
        className="w-full max-w-[560px] overflow-hidden rounded-xl border border-line bg-paper-card shadow-float animate-in fade-in slide-in-from-top-2 duration-200"
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Search size={16} className="text-ink-faint" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Jump to a page or a brief…"
            className="h-12 flex-1 bg-transparent text-[14px] text-ink placeholder:text-ink-faint focus:outline-none"
            aria-label="Search pages and briefs"
          />
          <kbd className="rounded-sm border border-line px-1.5 py-0.5 font-mono text-[10px] text-ink-faint">
            esc
          </kbd>
        </div>

        <div className="max-h-[52vh] overflow-y-auto p-2">
          {briefs.error ? (
            <p className="px-3 py-2 text-[12px] text-flag-bad">
              Briefs could not be loaded, so only pages are listed.
            </p>
          ) : null}
          {items.length === 0 ? (
            <p className="px-3 py-6 text-center text-[13px] text-ink-faint">Nothing matches “{query}”.</p>
          ) : (
            items.map((item, index) => {
              const header = item.group !== lastGroup ? item.group : null;
              lastGroup = item.group;
              return (
                <div key={item.id}>
                  {header ? <div className="label px-3 pb-1 pt-3">{header}</div> : null}
                  <button
                    type="button"
                    onMouseEnter={() => setCursor(index)}
                    onClick={() => go(item)}
                    className={cn(
                      "flex w-full cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors duration-100",
                      index === cursor ? "bg-pine-wash" : "hover:bg-paper",
                    )}
                  >
                    <FileText
                      size={15}
                      className={index === cursor ? "text-pine" : "text-ink-faint"}
                    />
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate text-[13px] font-medium text-ink">{item.label}</span>
                      <span className="truncate font-mono text-[10.5px] text-ink-faint">{item.hint}</span>
                    </span>
                    {index === cursor ? <CornerDownLeft size={13} className="text-pine" /> : null}
                  </button>
                </div>
              );
            })
          )}
          {briefs.isLoading ? (
            <p className="px-3 py-2 font-mono text-[11px] text-ink-faint">Loading briefs…</p>
          ) : null}
        </div>

        <div className="flex items-center gap-4 border-t border-line bg-paper px-4 py-2 font-mono text-[10px] text-ink-faint">
          <span>↑ ↓ move</span>
          <span>↵ open</span>
          <span>ctrl / ⌘ k toggle</span>
        </div>
      </div>
    </div>
  );
}
