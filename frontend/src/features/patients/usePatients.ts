import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { Encounter, Patient } from "../../api/types";

export function usePatientSearch(query: string) {
  return useQuery({
    queryKey: ["patients", "search", query],
    queryFn: () => api.get<Patient[]>(`/patients/search/?q=${encodeURIComponent(query)}`),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
  });
}

export function usePatient(id: number) {
  return useQuery({
    queryKey: ["patients", id],
    queryFn: () => api.get<Patient>(`/patients/${id}/`),
  });
}

export interface RegistrationInput {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: string;
  national_id: string;
  phone: string;
  address: string;
  next_of_kin_name: string;
  next_of_kin_phone: string;
  blood_group: string;
  medical_aid_provider: string;
  medical_aid_number: string;
  consent_confirmed: boolean;
  create_anyway?: boolean;
}

export function useRegisterPatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RegistrationInput) => api.post<Patient>("/patients/", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });
}

export function useUpdatePatient(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<RegistrationInput>) =>
      api.patch<Patient>(`/patients/${id}/`, body),
    onSuccess: (patient) => {
      queryClient.setQueryData(["patients", id], patient);
      void queryClient.invalidateQueries({ queryKey: ["patients", "search"] });
    },
  });
}

export function useTimeline(patientId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["patients", patientId, "timeline"],
    queryFn: () => api.get<Encounter[]>(`/patients/${patientId}/timeline/`),
    enabled,
  });
}
