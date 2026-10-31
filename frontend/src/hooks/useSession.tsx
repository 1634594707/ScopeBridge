import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { SessionResponse } from "../lib/types";

export function useSession() {
  return useQuery<SessionResponse>({
    queryKey: ["session"],
    queryFn: api.session,
    retry: false,
    staleTime: 30_000,
  });
}
