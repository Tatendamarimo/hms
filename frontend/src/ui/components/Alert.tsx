import type { ReactNode } from "react";

type AlertVariant = "info" | "success" | "warning" | "danger";

const styles: Record<AlertVariant, { bg: string; border: string; text: string; icon: string }> = {
  info: {
    bg: "bg-[var(--hms-info-light)]",
    border: "border-[var(--hms-info)]",
    text: "text-[var(--hms-info-dark)]",
    icon: "ℹ",
  },
  success: {
    bg: "bg-[var(--hms-success-light)]",
    border: "border-[var(--hms-success)]",
    text: "text-[var(--hms-success-dark)]",
    icon: "✓",
  },
  warning: {
    bg: "bg-[var(--hms-warning-light)]",
    border: "border-[var(--hms-warning)]",
    text: "text-[var(--hms-warning-dark)]",
    icon: "⚠",
  },
  danger: {
    bg: "bg-[var(--hms-danger-light)]",
    border: "border-[var(--hms-danger)]",
    text: "text-[var(--hms-danger-dark)]",
    icon: "✕",
  },
};

export default function Alert({
  variant = "info",
  children,
  className = "",
}: {
  variant?: AlertVariant;
  children: ReactNode;
  className?: string;
}) {
  const s = styles[variant];
  return (
    <div
      role="alert"
      className={`flex items-start gap-2.5 rounded-lg border-l-4 px-4 py-3 text-sm ${s.bg} ${s.border} ${s.text} ${className}`}
    >
      <span className="text-base leading-none" aria-hidden>{s.icon}</span>
      <div className="flex-1">{children}</div>
    </div>
  );
}
