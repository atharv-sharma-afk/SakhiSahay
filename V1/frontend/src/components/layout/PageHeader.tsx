import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: ReactNode; description?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        {eyebrow && <p className="eyebrow mb-1.5">{eyebrow}</p>}
        <h1 className="text-3xl font-semibold leading-tight text-ink-900 sm:text-4xl">{title}</h1>
        {description && <p className="mt-2 text-[0.95rem] leading-relaxed text-ink-500">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
