import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, primeCsrf } from "../../api/client";
import type { Me } from "../../api/types";

const ME_KEY = ["auth", "me"] as const;

export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: () => api.get<Me>("/auth/me/"),
    retry: (failureCount, error) =>
      !(error instanceof ApiError && (error.status === 401 || error.status === 403)) &&
      failureCount < 1,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) => {
      await primeCsrf();
      return api.post<Me>("/auth/login/", credentials);
    },
    onSuccess: (me) => queryClient.setQueryData(ME_KEY, me),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ detail: string }>("/auth/logout/"),
    onSettled: () => queryClient.resetQueries({ queryKey: ME_KEY }),
  });
}

export function useSwitchClinic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (clinicId: number) => api.post<Me>("/auth/clinic/", { clinic_id: clinicId }),
    onSuccess: (me) => queryClient.setQueryData(ME_KEY, me),
  });
}
