import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  toast: (type: ToastType, message: string) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let nextId = 0;

const DURATION = 4000;

const typeStyles: Record<ToastType, { bg: string; border: string; icon: string }> = {
  success: {
    bg: "bg-[var(--hms-success-light)]",
    border: "border-[var(--hms-success)]",
    icon: "✓",
  },
  error: {
    bg: "bg-[var(--hms-danger-light)]",
    border: "border-[var(--hms-danger)]",
    icon: "✕",
  },
  warning: {
    bg: "bg-[var(--hms-warning-light)]",
    border: "border-[var(--hms-warning)]",
    icon: "⚠",
  },
  info: {
    bg: "bg-[var(--hms-info-light)]",
    border: "border-[var(--hms-info)]",
    icon: "ℹ",
  },
};

const textColors: Record<ToastType, string> = {
  success: "text-[var(--hms-success-dark)]",
  error: "text-[var(--hms-danger-dark)]",
  warning: "text-[var(--hms-warning-dark)]",
  info: "text-[var(--hms-info-dark)]",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = ++nextId;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, DURATION);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const value: ToastContextValue = {
    toast: addToast,
    success: (msg) => addToast("success", msg),
    error: (msg) => addToast("error", msg),
    warning: (msg) => addToast("warning", msg),
    info: (msg) => addToast("info", msg),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}

      {/* Toast stack */}
      <div
        className="pointer-events-none fixed bottom-0 right-0 flex flex-col gap-2 p-4"
        style={{ zIndex: "var(--hms-z-toast)" }}
        aria-live="polite"
      >
        {toasts.map((t) => {
          const style = typeStyles[t.type];
          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex items-start gap-3 rounded-lg border-l-4 px-4 py-3 shadow-lg animate-in slide-in-from-right duration-200 ${style.bg} ${style.border}`}
              role="alert"
            >
              <span className={`text-lg leading-none ${textColors[t.type]}`} aria-hidden>
                {style.icon}
              </span>
              <p className={`text-sm font-medium ${textColors[t.type]}`}>{t.message}</p>
              <button
                onClick={() => dismiss(t.id)}
                className={`ml-auto -mr-1 rounded p-0.5 opacity-60 transition-opacity hover:opacity-100 ${textColors[t.type]}`}
                aria-label="Dismiss"
              >
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}
