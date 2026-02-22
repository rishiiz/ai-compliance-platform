"use client";

import * as React from "react";
import { createPortal } from "react-dom";

interface ToastContextType {
  toast: (message: string) => void;
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [message, setMessage] = React.useState<string | null>(null);
  const [mounted, setMounted] = React.useState(false);
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const toast = React.useCallback((msg: string) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setMessage(msg);
    timeoutRef.current = setTimeout(() => {
      setMessage(null);
      timeoutRef.current = null;
    }, 3000);
  }, []);

  const value = React.useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {mounted &&
        typeof document !== "undefined" &&
        message &&
        createPortal(
          <div
            className="fixed bottom-6 right-6 z-[100] rounded-lg border border-border bg-card px-4 py-3 text-sm font-medium text-card-foreground shadow-xl backdrop-blur-xl"
            style={{ animation: "toastIn 0.3s ease-out" }}
            role="status"
          >
            {message}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (context === undefined) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
