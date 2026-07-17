import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { Payment } from "../../api/types";

export interface DrawerPreview {
  expected_total: string;
  payment_count: number;
  period_start: string | null;
  previous_cash_up_at: string | null;
  payments: Payment[];
}

export interface CashUp {
  id: number;
  cashier_name: string;
  period_start: string;
  period_end: string;
  expected_total: string;
  counted_total: string;
  variance: string;
  notes: string;
  status: "open" | "closed";
  created_at: string;
}

export interface UnpaidInvoiceRow {
  id: number;
  number: string;
  issued_at: string;
  encounter_status: string;
  total: string;
  paid: string;
  outstanding: string;
}

export interface UnpaidEntry {
  patient: { id: number; mrn: string; full_name: string };
  outstanding: string;
  invoices: UnpaidInvoiceRow[];
}

export function useDrawer() {
  return useQuery({
    queryKey: ["billing", "cashup"],
    queryFn: () => api.get<DrawerPreview>("/billing/cashup/"),
    refetchInterval: 30_000,
  });
}

export function useCloseCashUp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { counted_total: string; notes: string }) =>
      api.post<CashUp>("/billing/cashup/", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["billing", "cashup"] });
    },
  });
}

export function useUnpaidBalances() {
  return useQuery({
    queryKey: ["billing", "unpaid"],
    queryFn: () => api.get<{ count: number; results: UnpaidEntry[] }>("/billing/unpaid/"),
  });
}
