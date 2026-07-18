import type { ReactNode } from "react";

export interface CardProps {
  variant?: "default" | "outlined" | "elevated";
  padding?: "none" | "sm" | "md" | "lg";
  className?: string;
  children: ReactNode;
}

const variantStyles: Record<NonNullable<CardProps["variant"]>, string> = {
  default: "border border-[var(--hms-border)] bg-[var(--hms-bg-card)] shadow-[var(--hms-shadow-sm)]",
  outlined: "border border-[var(--hms-border)] bg-[var(--hms-bg-card)]",
  elevated: "bg-[var(--hms-bg-card)] shadow-[var(--hms-shadow-md)]",
};

const paddingStyles: Record<NonNullable<CardProps["padding"]>, string> = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export default function Card({
  variant = "default",
  padding = "md",
  className = "",
  children,
}: CardProps) {
  return (
    <div className={`rounded-xl ${variantStyles[variant]} ${paddingStyles[padding]} ${className}`}>
      {children}
    </div>
  );
}

/** Section header inside a card — for consistent heading + optional action layout. */
export function CardHeader({
  title,
  action,
  className = "",
}: {
  title: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex items-center justify-between ${className}`}>
      <h2 className="font-semibold text-[var(--hms-text)]">{title}</h2>
      {action}
    </div>
  );
}
