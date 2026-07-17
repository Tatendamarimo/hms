import type { EncounterStatus, InvoiceStatus } from "../api/types";

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString();
}

const STATUS_LABELS: Record<EncounterStatus, string> = {
  waiting: "Waiting",
  in_triage: "In triage",
  awaiting_doctor: "Awaiting doctor",
  in_consultation: "In consultation",
  at_lab: "At lab",
  at_pharmacy: "At pharmacy",
  awaiting_payment: "Awaiting payment",
  closed: "Closed",
  left_without_being_seen: "LWBS",
};

const STATUS_STYLES: Record<EncounterStatus, string> = {
  waiting: "bg-amber-100 text-amber-800",
  in_triage: "bg-sky-100 text-sky-800",
  awaiting_doctor: "bg-violet-100 text-violet-800",
  in_consultation: "bg-emerald-100 text-emerald-800",
  at_lab: "bg-slate-100 text-slate-600",
  at_pharmacy: "bg-slate-100 text-slate-600",
  awaiting_payment: "bg-orange-100 text-orange-800",
  closed: "bg-slate-200 text-slate-600",
  left_without_being_seen: "bg-rose-100 text-rose-800",
};

export function EncounterStatusBadge({ status }: { status: EncounterStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

const INVOICE_STYLES: Record<InvoiceStatus, string> = {
  unpaid: "bg-rose-100 text-rose-800",
  part_paid: "bg-amber-100 text-amber-800",
  paid: "bg-emerald-100 text-emerald-800",
};

const INVOICE_LABELS: Record<InvoiceStatus, string> = {
  unpaid: "Unpaid",
  part_paid: "Part-paid",
  paid: "Paid",
};

export function InvoiceStatusBadge({ status }: { status: InvoiceStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${INVOICE_STYLES[status]}`}
    >
      {INVOICE_LABELS[status]}
    </span>
  );
}

export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
      {message}
    </div>
  );
}
