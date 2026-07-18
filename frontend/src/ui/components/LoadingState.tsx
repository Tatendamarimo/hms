import Spinner from "./Spinner";

export default function LoadingState({
  message = "Loading…",
  className = "",
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 py-16 ${className}`}>
      <Spinner size="lg" />
      <p className="text-sm text-[var(--hms-text-muted)]">{message}</p>
    </div>
  );
}
