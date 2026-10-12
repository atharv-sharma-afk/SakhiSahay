import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("card p-5 sm:p-6", className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({
  eyebrow,
  title,
  description,
  action,
  as: Heading = "h2",
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  as?: "h1" | "h2" | "h3";
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-4">
      <div className="min-w-0">
        {eyebrow && <p className="eyebrow mb-1">{eyebrow}</p>}
        <Heading className="text-lg sm:text-xl font-semibold text-ink-900 leading-snug">{title}</Heading>
        {description && <p className="text-sm text-ink-500 mt-1 leading-relaxed">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
