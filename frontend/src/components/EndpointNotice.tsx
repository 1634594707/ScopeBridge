import { PlugZap } from "lucide-react";
import { ApiError } from "../lib/api";

/**
 * Explicit state for a feature whose backend endpoint may not exist yet. A 404 or
 * 405 from the API means the route is missing; anything else is a real failure.
 * Neither case is replaced by placeholder data.
 */
export function EndpointNotice({
  error,
  endpoint,
  feature,
}: {
  error: unknown;
  endpoint: string;
  feature: string;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const missing = apiError !== null && (apiError.status === 404 || apiError.status === 405);

  if (missing) {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-dashed border-flag-info/40 bg-flag-info/5 px-4 py-4">
        <PlugZap size={16} className="mt-0.5 shrink-0 text-flag-info" />
        <div className="flex flex-col gap-1">
          <span className="text-[13px] font-medium text-ink">{feature} is not available on this server yet.</span>
          <span className="text-[12px] leading-relaxed text-ink-muted">
            The interface is ready; the API does not expose{" "}
            <code className="rounded-sm bg-paper-deep px-1 font-mono text-[11px]">{endpoint}</code> yet.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 rounded-lg border border-flag-bad/30 bg-flag-bad/5 px-4 py-4">
      <span className="text-[13px] font-medium text-flag-bad">{feature} could not be loaded.</span>
      <span className="text-[12px] text-ink-muted">
        {apiError ? apiError.message : "Check that the API is running and try again."}
      </span>
      {apiError ? <span className="font-mono text-[11px] text-ink-faint">code · {apiError.code}</span> : null}
    </div>
  );
}
