import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, CircleAlert, Info } from "lucide-react";
import { cn } from "@/lib/cn";

type ToastTone = "success" | "error" | "info";
interface Toast {
  id: number;
  tone: ToastTone;
  message: string;
}

const ToastContext = createContext<(message: string, tone?: ToastTone) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

const icons = {
  success: <CheckCircle2 className="size-4 text-sage-700" aria-hidden />,
  error: <CircleAlert className="size-4 text-danger-600" aria-hidden />,
  info: <Info className="size-4 text-lavender-700" aria-hidden />,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string, tone: ToastTone = "success") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, tone, message }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3800);
  }, []);
  const value = useMemo(() => push, [push]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 lg:bottom-6">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              "animate-rise pointer-events-auto flex items-center gap-2 rounded-2xl border bg-white px-4 py-2.5 text-sm shadow-lift",
              t.tone === "error" ? "border-danger-200" : t.tone === "info" ? "border-lavender-200" : "border-sage-200",
            )}
          >
            {icons[t.tone]}
            <span className="text-ink-900">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
