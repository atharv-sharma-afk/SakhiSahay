import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { Button } from "./Button";

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handleCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };
    el.addEventListener("cancel", handleCancel);
    return () => el.removeEventListener("cancel", handleCancel);
  }, [onClose]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="dialog-title"
      className="m-auto w-[min(92vw,30rem)] rounded-3xl border border-ivory-300 bg-white p-0 shadow-lift backdrop:bg-plum-900/40 backdrop:backdrop-blur-[2px]"
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="dialog-title" className="text-xl font-semibold text-ink-900">
              {title}
            </h2>
            {description && <p className="mt-1 text-sm text-ink-500 leading-relaxed">{description}</p>}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close dialog" className="-mr-2 -mt-1 px-2">
            <X className="size-4" />
          </Button>
        </div>
        {children && <div className="mt-4">{children}</div>}
        {footer && <div className="mt-6 flex flex-wrap justify-end gap-2">{footer}</div>}
      </div>
    </dialog>
  );
}
