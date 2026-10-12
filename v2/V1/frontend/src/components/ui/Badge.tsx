import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "plum" | "lavender" | "rose" | "sage" | "amber" | "danger" | "neutral";

const tones: Record<Tone, string> = {
  plum: "bg-plum-100 text-plum-800",
  lavender: "bg-lavender-100 text-lavender-700",
  rose: "bg-rose-100 text-rose-700",
  sage: "bg-sage-100 text-sage-700",
  amber: "bg-amber-100 text-amber-800",
  danger: "bg-danger-100 text-danger-800",
  neutral: "bg-ivory-200 text-ink-700",
};

export function Badge({
  tone = "neutral",
  icon,
  className,
  children,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone; icon?: ReactNode }) {
  return (
    <span
      className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium leading-5", tones[tone], className)}
      {...props}
    >
      {icon}
      {children}
    </span>
  );
}
