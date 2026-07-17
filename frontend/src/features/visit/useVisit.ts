import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type {
  CatalogService,
  Consultation,
  Diagnosis,
  Encounter,
  InvoiceDetail,
  LabOrder,
  Medication,
  PatientSummary,
  Prescription,
  Referral,
  SickNote,
  Vitals,
} from "../../api/types";

export function useEncounter(id: number) {
  return useQuery({
    queryKey: ["encounters", id],
    queryFn: () => api.get<Encounter>(`/encounters/${id}/`),
    refetchInterval: 15_000, // status can move from another station
  });
}

export function usePatientSummary(patientId: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["patients", patientId, "summary"],
    queryFn: () => api.get<PatientSummary>(`/patients/${patientId}/summary/`),
    enabled: enabled && patientId !== undefined,
  });
}

export function useVitals(encounterId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["encounters", encounterId, "vitals"],
    queryFn: () => api.get<Vitals[]>(`/encounters/${encounterId}/vitals/`),
    enabled,
  });
}

export function useRecordVitals(encounterId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<Vitals>(`/encounters/${encounterId}/vitals/`, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["encounters"] });
    },
  });
}

export function useConsultations(encounterId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["encounters", encounterId, "consultations"],
    queryFn: () => api.get<Consultation[]>(`/encounters/${encounterId}/consultation/`),
    enabled,
  });
}

function useInvalidateConsultations(encounterId: number) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({
      queryKey: ["encounters", encounterId, "consultations"],
    });
    void queryClient.invalidateQueries({ queryKey: ["encounters", encounterId] });
  };
}

export function useCreateDraft(encounterId: number) {
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: () => api.post<Consultation>(`/encounters/${encounterId}/consultation/`),
    onSuccess: invalidate,
  });
}

export function useEditConsultation(encounterId: number) {
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: number;
      presenting_complaint: string;
      clinical_notes: string;
      treatment_plan: string;
    }) => api.patch<Consultation>(`/consultations/${id}/`, body),
    onSuccess: invalidate,
  });
}

export function useConsultationAction(encounterId: number) {
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({
      id,
      action,
      body,
    }: {
      id: number;
      action: "sign" | "amend";
      body?: Record<string, unknown>;
    }) => api.post<Consultation>(`/consultations/${id}/${action}/`, body),
    onSuccess: invalidate,
  });
}

export function useAddDiagnosis(encounterId: number) {
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({
      consultationId,
      diagnosis,
      free_text,
    }: {
      consultationId: number;
      diagnosis: number | null;
      free_text: string;
    }) =>
      api.post(`/consultations/${consultationId}/diagnoses/`, { diagnosis, free_text }),
    onSuccess: invalidate,
  });
}

export function useDiagnosisSearch(query: string) {
  return useQuery({
    queryKey: ["diagnoses", query],
    queryFn: () => api.get<Diagnosis[]>(`/diagnoses/?q=${encodeURIComponent(query)}`),
    enabled: query.trim().length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMedications(query: string) {
  return useQuery({
    queryKey: ["medications", query],
    queryFn: () => api.get<Medication[]>(`/medications/?q=${encodeURIComponent(query)}`),
    enabled: query.trim().length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}

export interface PrescriptionItemInput {
  medication: number | null;
  medication_note: string;
  dose: string;
  frequency: string;
  duration_days: number;
  quantity: number;
  instructions: string;
}

export function usePrescribe(encounterId: number) {
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({
      consultationId,
      items,
      acknowledged_allergy_ids,
    }: {
      consultationId: number;
      items: PrescriptionItemInput[];
      acknowledged_allergy_ids: number[];
    }) =>
      api.post<Prescription>(`/consultations/${consultationId}/prescriptions/`, {
        items,
        acknowledged_allergy_ids,
      }),
    onSuccess: invalidate,
  });
}

export function useCreateSickNote(encounterId: number) {
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({
      consultationId,
      ...body
    }: {
      consultationId: number;
      unfit_from: string;
      unfit_to: string;
      remarks: string;
    }) => api.post<SickNote>(`/consultations/${consultationId}/sick-notes/`, body),
    onSuccess: invalidate,
  });
}

export function useCreateReferral(encounterId: number) {
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({
      consultationId,
      ...body
    }: {
      consultationId: number;
      destination_facility: string;
      reason: string;
    }) => api.post<Referral>(`/consultations/${consultationId}/referrals/`, body),
    onSuccess: invalidate,
  });
}

export function useOrderableServices() {
  return useQuery({
    queryKey: ["billing", "catalog", "orderable"],
    queryFn: () => api.list<CatalogService>("/billing/catalog/"),
    select: (services) =>
      services.filter(
        (service) =>
          (service.type === "lab" || service.type === "imaging") &&
          service.is_active &&
          service.current_price !== null,
      ),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateLabOrder(encounterId: number) {
  const queryClient = useQueryClient();
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({
      consultationId,
      service_items,
      instructions,
    }: {
      consultationId: number;
      service_items: number[];
      instructions: string;
    }) =>
      api.post<LabOrder>(`/consultations/${consultationId}/lab-orders/`, {
        service_items,
        instructions,
      }),
    onSuccess: () => {
      invalidate();
      void queryClient.invalidateQueries({ queryKey: ["billing", "invoices"] });
      void queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
    },
  });
}

export function useLabOrders(consultationId: number | undefined) {
  return useQuery({
    queryKey: ["lab-orders", consultationId],
    queryFn: () => api.list<LabOrder>(`/lab-orders/?consultation=${consultationId}`),
    enabled: consultationId !== undefined,
  });
}

export function useCancelLabOrder(encounterId: number) {
  const queryClient = useQueryClient();
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({ orderId, reason }: { orderId: number; reason: string }) =>
      api.post<LabOrder>(`/lab-orders/${orderId}/cancel/`, { reason }),
    onSuccess: () => {
      invalidate();
      void queryClient.invalidateQueries({ queryKey: ["billing", "invoices"] });
      void queryClient.invalidateQueries({ queryKey: ["lab-orders"] });
    },
  });
}

export function useCancelPrescription(encounterId: number) {
  const invalidate = useInvalidateConsultations(encounterId);
  return useMutation({
    mutationFn: ({ prescriptionId, reason }: { prescriptionId: number; reason: string }) =>
      api.post<Prescription>(`/prescriptions/${prescriptionId}/cancel/`, { reason }),
    onSuccess: invalidate,
  });
}

// --- invoice panel ---

export function useInvoice(invoiceId: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["billing", "invoices", invoiceId],
    queryFn: () => api.get<InvoiceDetail>(`/billing/invoices/${invoiceId}/`),
    enabled: enabled && invoiceId !== undefined,
  });
}

function useInvalidateInvoice() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["billing", "invoices"] });
    void queryClient.invalidateQueries({ queryKey: ["encounters"] });
  };
}

export function useAddInvoiceItem(invoiceId: number | undefined) {
  const invalidate = useInvalidateInvoice();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post(`/billing/invoices/${invoiceId}/items/`, body),
    onSuccess: invalidate,
  });
}

export function useVoidInvoiceItem(invoiceId: number | undefined) {
  const invalidate = useInvalidateInvoice();
  return useMutation({
    mutationFn: ({ itemId, reason }: { itemId: number; reason: string }) =>
      api.post(`/billing/invoices/${invoiceId}/items/${itemId}/void/`, { reason }),
    onSuccess: invalidate,
  });
}

export function useRecordPayment(invoiceId: number | undefined) {
  const invalidate = useInvalidateInvoice();
  return useMutation({
    mutationFn: (body: { amount: string; method: string; reference?: string }) =>
      api.post(`/billing/invoices/${invoiceId}/payments/`, body),
    onSuccess: invalidate,
  });
}

export function useReversePayment() {
  const invalidate = useInvalidateInvoice();
  return useMutation({
    mutationFn: ({ paymentId, reason }: { paymentId: number; reason: string }) =>
      api.post(`/billing/payments/${paymentId}/reverse/`, { reason }),
    onSuccess: invalidate,
  });
}

export function useBillableServices() {
  return useQuery({
    queryKey: ["billing", "catalog", "billable"],
    queryFn: () => api.list<CatalogService>("/billing/catalog/"),
    select: (services) =>
      services.filter((service) => service.is_active && service.current_price !== null),
    staleTime: 5 * 60 * 1000,
  });
}
