import type { ReactNode } from "react";
import { AlertTriangle, Info, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/cn";

type Tone = "info" | "advisory" | "urgent";

const styles: Record<Tone, { box: string; icon: ReactNode; label: string }> = {
  info: { box: "border-lavender-200 bg-lavender-100/60 text-ink-700", icon: <Info className="size-4 text-lavender-700" aria-hidden />, label: "Note" },
  advisory: { box: "border-amber-200 bg-amber-100/70 text-amber-800", icon: <AlertTriangle className="size-4" aria-hidden />, label: "Please note" },
  urgent: { box: "border-danger-200 bg-danger-100/80 text-danger-800", icon: <ShieldAlert className="size-4" aria-hidden />, label: "Urgent" },
};

export function Notice({ tone = "info", title, children, className }: { tone?: Tone; title?: string; children: ReactNode; className?: string }) {
  const s = styles[tone];
  return (
    <div role={tone === "urgent" ? "alert" : "note"} className={cn("flex gap-3 rounded-2xl border px-4 py-3 text-sm leading-relaxed", s.box, className)}>
      <span className="mt-0.5 shrink-0">{s.icon}</span>
      <div className="min-w-0">
        <p className="font-semibold">
          <span className="sr-only">{s.label}: </span>
          {title}
        </p>
        <div className={cn(title && "mt-0.5")}>{children}</div>
      </div>
    </div>
  );
}
