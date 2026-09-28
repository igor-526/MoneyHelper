import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/shared/api";

export interface HealthResponse {
  status: string;
}

export const HEALTH_QUERY_KEY = ["health"] as const;

export function useHealth() {
  const api = useApiClient();
  return useQuery({
    queryKey: HEALTH_QUERY_KEY,
    queryFn: ({ signal }) => api.get<HealthResponse>("/health", { signal }),
  });
}
