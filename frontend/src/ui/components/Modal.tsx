import { useCallback, useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  /** Maximum width class (Tailwind). Defaults to max-w-lg. */
  maxWidth?: string;
  children: ReactNode;
}

/**
 * Production modal: portal-rendered, focus-trapped, escape-to-close,
 * backdrop-click-to-close, entrance/exit animation.
 */
export default function Modal({
  open,
  onClose,
  title,
  maxWidth = "max-w-lg",
  children,
}: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // Trap focus inside the modal
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key === "Tab" && contentRef.current) {
        const focusable = contentRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    // Prevent body scroll while modal is open
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  // Auto-focus first focusable element
  useEffect(() => {
    if (open && contentRef.current) {
      const first = contentRef.current.querySelector<HTMLElement>(
        'input, select, textarea, button:not([data-modal-close])',
      );
      first?.focus();
    }
  }, [open]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === overlayRef.current) onClose();
    },
    [onClose],
  );

  if (!open) return null;

  return createPortal(
    <div
      ref={overlayRef}
      onClick={handleBackdropClick}
      className="fixed inset-0 flex items-center justify-center p-4 animate-in fade-in duration-150"
      style={{ zIndex: "var(--hms-z-modal)", backgroundColor: "var(--hms-bg-overlay)" }}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        ref={contentRef}
        className={`w-full ${maxWidth} rounded-xl bg-[var(--hms-bg-card)] shadow-xl animate-in zoom-in-95 duration-150`}
        style={{ maxHeight: "calc(100vh - 2rem)" }}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-[var(--hms-border)] px-6 py-4">
            <h3 className="text-lg font-semibold text-[var(--hms-text)]">{title}</h3>
            <button
              data-modal-close
              onClick={onClose}
              className="rounded-lg p-1 text-[var(--hms-text-muted)] transition-colors hover:bg-[var(--hms-bg-muted)] hover:text-[var(--hms-text)]"
              aria-label="Close"
            >
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        )}
        <div className="overflow-y-auto px-6 py-5" style={{ maxHeight: "calc(100vh - 10rem)" }}>
          {children}
        </div>
      </div>
    </div>,
    document.body,
  );
}
