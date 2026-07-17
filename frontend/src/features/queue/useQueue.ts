import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { CatalogService, Encounter, EncounterStatus } from "../../api/types";

export const QUEUE_KEY = ["encounters", "queue"] as const;

export function useQueue() {
  return useQuery({
    queryKey: QUEUE_KEY,
    queryFn: () => api.get<Encounter[]>("/encounters/queue/"),
    refetchInterval: 10_000, // design §5: live queue polls every 10s
  });
}

function useInvalidateQueue() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["encounters"] });
  };
}

export function useTransition() {
  const invalidate = useInvalidateQueue();
  return useMutation({
    mutationFn: ({
      encounterId,
      to,
      reason,
    }: {
      encounterId: number;
      to: EncounterStatus;
      reason?: string;
    }) =>
      api.post<Encounter>(`/encounters/${encounterId}/transition/`, {
        to,
        reason: reason ?? "",
      }),
    onSuccess: invalidate,
  });
}

export function useCheckIn() {
  const invalidate = useInvalidateQueue();
  return useMutation({
    mutationFn: (body: {
      patient: number;
      type: string;
      notes?: string;
      checkin_service?: number | null;
    }) => api.post<Encounter>("/encounters/", body),
    onSuccess: invalidate,
  });
}

export function useConsultationServices() {
  return useQuery({
    queryKey: ["billing", "catalog", "consultation"],
    queryFn: () => api.get<CatalogService[]>("/billing/catalog/"),
    select: (services) =>
      services.filter(
        (service) =>
          service.type === "consultation" &&
          service.is_active &&
          service.current_price !== null,
      ),
    staleTime: 5 * 60 * 1000,
  });
}
