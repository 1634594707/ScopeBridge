import { useQuery } from "@tanstack/react-query";
import { Link, Outlet } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import type { SessionResponse } from "../lib/types";
import { Button } from "../components/Button";

export function useSession() {
  return useQuery<SessionResponse>({
    queryKey: ["session"],
    queryFn: api.session,
    retry: false,
    staleTime: 30_000,
  });
}

export function RequireSeller() {
  const session = useSession();

  if (session.isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <span className="h-4 w-4 animate-spin rounded-full border border-pine border-t-transparent" />
      </div>
    );
  }

  if (session.error) {
    const status = session.error instanceof ApiError ? session.error.status : 0;
    if (status === 401) {
      return (
        <div className="mx-auto flex max-w-md flex-col items-start gap-4 py-20">
          <span className="label">Restricted</span>
          <h2 className="text-2xl font-semibold tracking-[-0.02em]">The desk is locked</h2>
          <p className="text-sm leading-relaxed text-ink-muted">
            Sign in with the seller account to review briefs, price scopes and issue quotes.
          </p>
          <Link to="/signin">
            <Button>Sign in</Button>
          </Link>
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-md py-20 text-sm text-flag-bad">
        The seller console could not be loaded. Check that the API is running.
      </div>
    );
  }

  return <Outlet />;
}
