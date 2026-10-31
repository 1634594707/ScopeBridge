import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  ClipboardList,
  FilePlus2,
  FolderOpen,
  Menu,
  ReceiptText,
  Search,
  X,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import { cn } from "../lib/cn";
import { useSession } from "../hooks/useSession";
import type { AccountRole } from "../lib/types";
import { BrandMark, BrandTile } from "./BrandMark";
import { CommandPalette, useCommandPalette } from "./CommandPalette";

const sellerNavItems = [
  { to: "/console", label: "Console", icon: ClipboardList },
  { to: "/rules", label: "Price list", icon: ReceiptText },
];

const clientNavItems = [
  { to: "/briefs", label: "My briefs", icon: FolderOpen },
  { to: "/start", label: "New brief", icon: FilePlus2 },
  { to: "/rules", label: "Price list", icon: ReceiptText },
];

/** Section anchors on the landing page; the public header links to them from any page. */
const landingSections = [
  { hash: "how-it-works", label: "How it works" },
  { hash: "lifecycle", label: "Lifecycle" },
  { hash: "pricing", label: "Pricing" },
  { hash: "payments", label: "Payments" },
  { hash: "faq", label: "FAQ" },
];

function useSignOut() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [signOutError, setSignOutError] = useState<string | null>(null);

  const signOut = async () => {
    setSignOutError(null);
    try {
      await api.signOut();
    } catch (err) {
      // A 401 means the session was already gone server-side; signing out locally is still correct.
      const status = err instanceof ApiError ? err.status : 0;
      if (status !== 401) {
        setSignOutError("Sign out failed. Check that the API is running and try again.");
        return;
      }
    }
    queryClient.removeQueries({ queryKey: ["session"] });
    navigate("/");
  };

  return { signOut, signOutError };
}

function Mark() {
  return (
    <div className="flex items-center gap-2.5">
      <BrandTile />
      <span className="flex flex-col leading-none">
        <span className="text-[15px] font-semibold tracking-[-0.02em] text-ink">ScopeBridge</span>
        <span className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
          contract desk
        </span>
      </span>
    </div>
  );
}

function RailNav({ items }: { items: typeof sellerNavItems }) {
  return (
    <nav className="flex flex-col gap-0.5">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors duration-150",
              isActive
                ? "bg-pine-wash font-medium text-pine-deep"
                : "text-ink-muted hover:bg-paper-deep hover:text-ink",
            )
          }
        >
          <Icon size={15} strokeWidth={1.8} />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

function SearchTrigger({ onOpen, className }: { onOpen: () => void; className?: string }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        "flex cursor-pointer items-center gap-2 rounded-md border border-line bg-paper-card px-2.5 py-2 text-left text-[12px] text-ink-faint transition-colors duration-150 hover:border-ink/25 hover:text-ink",
        className,
      )}
    >
      <Search size={13} />
      <span className="flex-1">Jump to…</span>
      <kbd className="rounded-sm border border-line px-1 font-mono text-[10px]">ctrl k</kbd>
    </button>
  );
}

function Rail({
  items,
  accessLabel,
  signedOutCopy,
  allowSwitch,
  onSearch,
}: {
  items: typeof sellerNavItems;
  accessLabel: string;
  signedOutCopy: string;
  allowSwitch: boolean;
  onSearch: () => void;
}) {
  const session = useSession();
  const account = session.data?.account;
  const { signOut, signOutError } = useSignOut();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[236px] flex-col justify-between border-r border-line bg-paper/85 px-5 py-6 backdrop-blur-sm lg:flex">
      <div className="flex flex-col gap-6">
        <Link to="/" className="block">
          <Mark />
        </Link>
        {account ? <SearchTrigger onOpen={onSearch} /> : null}
        <div className="flex flex-col gap-2">
          <span className="label px-2.5">Workspace</span>
          <RailNav items={items} />
        </div>
      </div>

      <div className="flex flex-col gap-3 border-t border-line pt-4">
        <span className="label">{account ? "Signed in" : accessLabel}</span>
        {account ? (
          <div className="flex items-start gap-2.5">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-pine-wash font-mono text-[12px] font-semibold uppercase text-pine-deep">
              {account.display_name.trim().charAt(0) || "·"}
            </span>
            <div className="flex min-w-0 flex-col gap-1">
              <span className="truncate text-[13px] font-medium text-ink">{account.display_name}</span>
              <span className="truncate font-mono text-[11px] text-ink-faint">{account.email}</span>
              <div className="mt-1 flex items-center gap-3">
                {allowSwitch ? (
                  <Link
                    to="/signin"
                    className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint underline-offset-4 hover:text-ink hover:underline"
                  >
                    switch account
                  </Link>
                ) : null}
                <button
                  type="button"
                  onClick={signOut}
                  className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint underline-offset-4 hover:text-ink hover:underline"
                >
                  sign out
                </button>
              </div>
            </div>
          </div>
        ) : (
          <Link to="/signin" className="text-[13px] text-ink-muted hover:text-ink">
            {signedOutCopy}
          </Link>
        )}
        {signOutError ? <p className="text-[12px] leading-relaxed text-flag-bad">{signOutError}</p> : null}
      </div>
    </aside>
  );
}

function RoleTopBar({ items, onSearch }: { items: typeof sellerNavItems; onSearch: () => void }) {
  return (
    <header className="fixed inset-x-0 top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-paper/90 px-4 backdrop-blur-sm sm:px-8 lg:hidden">
      <Link to="/">
        <Mark />
      </Link>
      <nav className="flex items-center gap-4 text-[12px] text-ink-muted">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => cn("hidden hover:text-ink sm:inline", isActive && "text-ink")}
          >
            {item.label}
          </NavLink>
        ))}
        <button
          type="button"
          onClick={onSearch}
          aria-label="Jump to a page or brief"
          className="cursor-pointer rounded-md border border-line p-1.5 text-ink-muted hover:text-ink"
        >
          <Search size={14} />
        </button>
      </nav>
    </header>
  );
}

function sectionHref(hash: string) {
  return { pathname: "/", hash: `#${hash}` };
}

function PublicTopBar() {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname, location.hash]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-40 border-b transition-colors duration-200",
        scrolled || menuOpen
          ? "border-line bg-paper/90 backdrop-blur-md"
          : "border-transparent bg-paper/60 backdrop-blur-sm",
      )}
    >
      <div className="mx-auto flex h-14 max-w-[1140px] items-center justify-between gap-6 px-5 sm:px-8">
        <Link to="/" aria-label="ScopeBridge home">
          <Mark />
        </Link>

        <nav className="hidden items-center gap-1 text-[13px] text-ink-muted md:flex">
          {landingSections.map((section) => (
            <Link
              key={section.hash}
              to={sectionHref(section.hash)}
              className="rounded-md px-2.5 py-1.5 transition-colors duration-150 hover:bg-paper-deep hover:text-ink"
            >
              {section.label}
            </Link>
          ))}
          <NavLink
            to="/rules"
            className={({ isActive }) =>
              cn(
                "rounded-md px-2.5 py-1.5 transition-colors duration-150 hover:bg-paper-deep hover:text-ink",
                isActive && "text-ink",
              )
            }
          >
            Price list
          </NavLink>
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Link
            to="/signin"
            className="rounded-md px-3 py-1.5 text-[13px] text-ink-muted transition-colors duration-150 hover:text-ink"
          >
            Sign in
          </Link>
          <Link
            to="/start"
            className="inline-flex items-center gap-1.5 rounded-md border border-pine bg-pine px-3 py-1.5 text-[13px] font-medium text-ink-invert transition-colors duration-150 hover:bg-pine-deep"
          >
            Start a brief
            <ArrowRight size={13} />
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setMenuOpen((value) => !value)}
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          className="cursor-pointer rounded-md border border-line p-2 text-ink md:hidden"
        >
          {menuOpen ? <X size={16} /> : <Menu size={16} />}
        </button>
      </div>

      {menuOpen ? (
        <div className="border-t border-line bg-paper px-5 pb-5 pt-3 animate-fade-up md:hidden">
          <nav className="flex flex-col">
            {landingSections.map((section) => (
              <Link
                key={section.hash}
                to={sectionHref(section.hash)}
                className="border-b border-line/70 py-3 text-[14px] text-ink"
              >
                {section.label}
              </Link>
            ))}
            <Link to="/rules" className="border-b border-line/70 py-3 text-[14px] text-ink">
              Price list
            </Link>
          </nav>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Link
              to="/signin"
              className="rounded-md border border-line py-2.5 text-center text-[13px] text-ink"
            >
              Sign in
            </Link>
            <Link
              to="/start"
              className="rounded-md border border-pine bg-pine py-2.5 text-center text-[13px] font-medium text-ink-invert"
            >
              Start a brief
            </Link>
          </div>
        </div>
      ) : null}
    </header>
  );
}

const footerColumns: { title: string; links: { label: string; to: string | { pathname: string; hash: string } }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "How it works", to: sectionHref("how-it-works") },
      { label: "Quote lifecycle", to: sectionHref("lifecycle") },
      { label: "Rules-based pricing", to: sectionHref("pricing") },
      { label: "Verified payments", to: sectionHref("payments") },
    ],
  },
  {
    title: "Clients",
    links: [
      { label: "Start a brief", to: "/start" },
      { label: "My briefs", to: "/briefs" },
      { label: "Published price list", to: "/rules" },
      { label: "Common questions", to: sectionHref("faq") },
    ],
  },
  {
    title: "Studio",
    links: [
      { label: "Seller console", to: "/console" },
      { label: "Sign in", to: "/signin" },
      { label: "Guarantees", to: sectionHref("guarantees") },
      { label: "Compare workflows", to: sectionHref("compare") },
    ],
  },
];

function SiteFooter() {
  return (
    <footer className="border-t border-line bg-paper-deep/60">
      <div className="mx-auto grid max-w-[1140px] gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div className="flex flex-col gap-4">
          <Mark />
          <p className="max-w-[34ch] text-[13px] leading-relaxed text-ink-muted">
            A contract desk for small studios. The model reads the brief, the rules set the price,
            both sides confirm one version, and PayPal is checked before anything counts as paid.
          </p>
          <div className="flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
            <span className="rounded-sm border border-line px-2 py-1">Runs locally</span>
            <span className="rounded-sm border border-line px-2 py-1">PayPal sandbox</span>
            <span className="rounded-sm border border-line px-2 py-1">MIT licensed</span>
          </div>
        </div>
        {footerColumns.map((column) => (
          <div key={column.title} className="flex flex-col gap-3">
            <span className="label">{column.title}</span>
            <ul className="flex flex-col gap-2">
              {column.links.map((link) => (
                <li key={link.label}>
                  <Link to={link.to} className="text-[13px] text-ink-muted transition-colors hover:text-ink">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-[1140px] flex-col items-start justify-between gap-3 px-5 py-5 font-mono text-[11px] text-ink-faint sm:flex-row sm:items-center sm:px-8">
          <span className="flex items-center gap-2">
            <BrandMark className="h-4 w-4 text-pine" />© 2026 ScopeBridge
          </span>
          <span>Demo prices only · sandbox payments never move real money</span>
        </div>
      </div>
    </footer>
  );
}

export function AppShell({
  variant = "public",
  children,
}: {
  variant?: "seller" | "client" | "public";
  children: ReactNode;
}) {
  const session = useSession();
  const role = session.data?.account?.role;
  const palette = useCommandPalette();
  // The chrome follows the session role, not just the route: a signed-in seller
  // or client keeps their rail on every page they may open, while anonymous
  // visitors always get the client-facing top bar.
  const sellerChrome = variant === "seller" || role === "SELLER";
  const clientChrome = !sellerChrome && (variant === "client" || role === "CLIENT");
  const railChrome = sellerChrome || clientChrome;
  const paletteRole: AccountRole | null = role ?? null;
  const openPalette = () => palette.setOpen(true);

  return (
    <div className="flex min-h-screen flex-col">
      {sellerChrome ? (
        <>
          <Rail
            items={sellerNavItems}
            accessLabel="Seller access"
            signedOutCopy="Sign in to the desk"
            allowSwitch
            onSearch={openPalette}
          />
          <RoleTopBar items={sellerNavItems} onSearch={openPalette} />
        </>
      ) : clientChrome ? (
        <>
          <Rail
            items={clientNavItems}
            accessLabel="Client access"
            signedOutCopy="Sign in to your briefs"
            allowSwitch={false}
            onSearch={openPalette}
          />
          <RoleTopBar items={clientNavItems} onSearch={openPalette} />
        </>
      ) : (
        <PublicTopBar />
      )}
      <main className={cn("flex-1 pt-14", railChrome ? "lg:pl-[236px] lg:pt-0" : "")}>
        <div className="mx-auto w-full max-w-[1140px] px-5 py-8 sm:px-8 lg:py-12">{children}</div>
      </main>
      {railChrome ? null : <SiteFooter />}
      {paletteRole ? (
        <CommandPalette role={paletteRole} open={palette.open} onClose={() => palette.setOpen(false)} />
      ) : null}
    </div>
  );
}
