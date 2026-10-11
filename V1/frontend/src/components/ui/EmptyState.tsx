import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-2xl border border-dashed border-plum-200 bg-plum-50/50 px-6 py-9 text-center", className)}>
      {icon && <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full bg-white text-plum-600 shadow-soft">{icon}</div>}
      <h3 className="font-sans text-base font-semibold text-ink-900">{title}</h3>
      {description && <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-ink-500">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-ivory-200", className)} aria-hidden />;
}
