import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  /** Side to slide from. Default: "right" */
  side?: "left" | "right";
  /** Width class. Default: "w-72" */
  width?: string;
  children: ReactNode;
}

/**
 * Slide-in panel for mobile navigation and detail views.
 */
export default function Drawer({
  open,
  onClose,
  side = "right",
  width = "w-72",
  children,
}: DrawerProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  const positionClass = side === "left" ? "left-0" : "right-0";
  const translateIn = side === "left" ? "animate-in slide-in-from-left" : "animate-in slide-in-from-right";

  return createPortal(
    <div
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      className="fixed inset-0 animate-in fade-in duration-150"
      style={{ zIndex: "var(--hms-z-drawer)", backgroundColor: "var(--hms-bg-overlay)" }}
    >
      <div
        className={`fixed top-0 ${positionClass} h-full ${width} bg-[var(--hms-bg-card)] shadow-xl ${translateIn} duration-200`}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
