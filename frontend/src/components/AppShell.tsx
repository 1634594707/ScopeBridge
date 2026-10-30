import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { ClipboardList, FilePlus2, ReceiptText } from "lucide-react";
import { cn } from "../lib/cn";
import { useSession } from "../hooks/useSession";
import { BrandTile } from "./BrandMark";

const navItems = [
  { to: "/console", label: "Console", icon: ClipboardList },
  { to: "/start", label: "New brief", icon: FilePlus2 },
  { to: "/rules", label: "Price list", icon: ReceiptText },
];

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

function SellerRail() {
  const session = useSession();
  const seller = session.data?.seller;

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[236px] flex-col justify-between border-r border-line bg-paper/85 px-5 py-6 backdrop-blur-sm lg:flex">
      <div className="flex flex-col gap-8">
        <Link to="/" className="block">
          <Mark />
        </Link>
        <nav className="flex flex-col gap-0.5">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors duration-150",
                  isActive
                    ? "bg-pine-wash text-pine-deep"
                    : "text-ink-muted hover:bg-paper-deep hover:text-ink",
                )
              }
            >
              <Icon size={15} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="flex flex-col gap-3 border-t border-line pt-4">
        <span className="label">Signed in</span>
        {seller ? (
          <div className="flex flex-col gap-1">
            <span className="text-[13px] font-medium text-ink">{seller.display_name}</span>
            <span className="truncate font-mono text-[11px] text-ink-faint">{seller.email}</span>
            <Link
              to="/signin"
              className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint underline-offset-4 hover:text-ink hover:underline"
            >
              switch account
            </Link>
          </div>
        ) : (
          <Link to="/signin" className="text-[13px] text-ink-muted hover:text-ink">
            Sign in to the desk
          </Link>
        )}
      </div>
    </aside>
  );
}

function TopBar({ variant }: { variant: "seller" | "public" }) {
  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-paper px-4 sm:px-8",
        variant === "seller" ? "lg:hidden" : "",
      )}
    >
      <Link to="/">
        <Mark />
      </Link>
      <nav className="flex items-center gap-5 text-[12px] text-ink-muted">
        {variant === "seller" ? (
          <>
            <NavLink to="/console" className="hover:text-ink">
              Console
            </NavLink>
            <NavLink to="/start" className="hover:text-ink">
              New brief
            </NavLink>
          </>
        ) : (
          <>
            <NavLink to="/rules" className="hover:text-ink">
              Price list
            </NavLink>
            <NavLink
              to="/console"
              className="rounded-sm border border-line px-2.5 py-1.5 font-medium text-ink transition-colors duration-150 hover:border-ink/25 hover:bg-paper-deep"
            >
              Seller console
            </NavLink>
          </>
        )}
      </nav>
    </header>
  );
}

export function AppShell({ variant = "public", children }: { variant?: "seller" | "public"; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-paper">
      {variant === "seller" ? <SellerRail /> : null}
      <TopBar variant={variant} />
      <main
        className={cn(
          "pt-14 lg:pt-0",
          variant === "seller" ? "lg:pl-[236px]" : "",
        )}
      >
        <div className="mx-auto w-full max-w-[1140px] px-5 py-8 sm:px-8 lg:py-12">{children}</div>
      </main>
    </div>
  );
}
