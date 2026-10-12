import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const base =
  "w-full rounded-xl border bg-white px-3.5 text-[0.95rem] text-ink-900 placeholder:text-ink-300 transition-colors " +
  "border-ivory-300 hover:border-plum-200 focus:border-plum-400 focus:outline-none focus:shadow-ring disabled:bg-ivory-100";

function Wrapper({ id, label, hint, error, children, optional }: { id: string; label: string; hint?: ReactNode; error?: string; children: ReactNode; optional?: boolean }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="flex items-baseline justify-between text-sm font-medium text-ink-700">
        <span>{label}</span>
        {optional && <span className="text-xs font-normal text-ink-400">optional</span>}
      </label>
      {children}
      {error ? (
        <p className="text-xs text-danger-600" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-ink-400">{hint}</p>
      ) : null}
    </div>
  );
}

type Common = { label: string; hint?: ReactNode; error?: string; optional?: boolean };

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & Common>(function Input(
  { label, hint, error, optional, className, id, ...props },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <Wrapper id={fieldId} label={label} hint={hint} error={error} optional={optional}>
      <input ref={ref} id={fieldId} aria-invalid={!!error} className={cn(base, "h-11", error && "border-danger-600", className)} {...props} />
    </Wrapper>
  );
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement> & Common>(function Select(
  { label, hint, error, optional, className, id, children, ...props },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <Wrapper id={fieldId} label={label} hint={hint} error={error} optional={optional}>
      <select ref={ref} id={fieldId} aria-invalid={!!error} className={cn(base, "h-11", error && "border-danger-600", className)} {...props}>
        {children}
      </select>
    </Wrapper>
  );
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement> & Common>(function Textarea(
  { label, hint, error, optional, className, id, ...props },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <Wrapper id={fieldId} label={label} hint={hint} error={error} optional={optional}>
      <textarea ref={ref} id={fieldId} aria-invalid={!!error} className={cn(base, "py-2.5 min-h-[88px] resize-y", error && "border-danger-600", className)} {...props} />
    </Wrapper>
  );
});
