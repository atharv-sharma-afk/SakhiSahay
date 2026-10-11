import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "soft";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary: "bg-plum-700 text-white hover:bg-plum-800 active:bg-plum-900 shadow-soft",
  secondary: "bg-white text-plum-800 border border-plum-200 hover:border-plum-300 hover:bg-plum-50",
  soft: "bg-plum-50 text-plum-800 hover:bg-plum-100",
  ghost: "text-plum-700 hover:bg-plum-50",
  danger: "bg-white text-danger-800 border border-danger-200 hover:bg-danger-100",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-3.5 text-sm gap-1.5 rounded-xl",
  md: "h-11 px-5 text-sm gap-2 rounded-xl",
  lg: "h-12 px-6 text-base gap-2 rounded-2xl",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "primary", size = "md", loading = false, disabled, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center font-medium transition-colors select-none",
        "disabled:opacity-55 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});
