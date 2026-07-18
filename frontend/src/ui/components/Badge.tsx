import type { ReactNode } from "react";

export type BadgeVariant =
  | "default"
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "muted";

const styles: Record<BadgeVariant, string> = {
  default: "bg-slate-100 text-slate-700",
  primary: "bg-[var(--hms-primary-light)] text-[var(--hms-primary)]",
  secondary: "bg-[var(--hms-secondary-light)] text-[var(--hms-secondary)]",
  success: "bg-[var(--hms-success-light)] text-[var(--hms-success-dark)]",
  warning: "bg-[var(--hms-warning-light)] text-[var(--hms-warning-dark)]",
  danger: "bg-[var(--hms-danger-light)] text-[var(--hms-danger-dark)]",
  info: "bg-[var(--hms-info-light)] text-[var(--hms-info-dark)]",
  muted: "bg-[var(--hms-bg-muted)] text-[var(--hms-text-muted)]",
};

export default function Badge({
  variant = "default",
  children,
  className = "",
  dot = false,
}: {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
  /** Show a small dot indicator before the text */
  dot?: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[variant]} ${className}`}
    >
      {dot && (
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      )}
      {children}
    </span>
  );
}
