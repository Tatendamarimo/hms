import type { EncounterStatus, InvoiceStatus } from "../api/types";
import Badge, { type BadgeVariant } from "./components/Badge";
import Alert from "./components/Alert";

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

const STATUS_VARIANTS: Record<EncounterStatus, BadgeVariant> = {
  waiting: "warning",
  in_triage: "info",
  awaiting_doctor: "primary",
  in_consultation: "success",
  at_lab: "muted",
  at_pharmacy: "muted",
  awaiting_payment: "warning",
  closed: "default",
  left_without_being_seen: "danger",
};

export function EncounterStatusBadge({ status }: { status: EncounterStatus }) {
  return (
    <Badge variant={STATUS_VARIANTS[status]} dot>
      {STATUS_LABELS[status]}
    </Badge>
  );
}

const INVOICE_VARIANTS: Record<InvoiceStatus, BadgeVariant> = {
  unpaid: "danger",
  part_paid: "warning",
  paid: "success",
};

const INVOICE_LABELS: Record<InvoiceStatus, string> = {
  unpaid: "Unpaid",
  part_paid: "Part-paid",
  paid: "Paid",
};

export function InvoiceStatusBadge({ status }: { status: InvoiceStatus }) {
  return (
    <Badge variant={INVOICE_VARIANTS[status]}>
      {INVOICE_LABELS[status]}
    </Badge>
  );
}

export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return <Alert variant="danger">{message}</Alert>;
}
