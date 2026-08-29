import { cn } from "@/lib/utils";

export function Switch({
  checked,
  onCheckedChange,
  disabled,
  label,
}: {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-label={label}
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className="flex min-h-11 w-full items-center justify-between gap-3 rounded-md px-1 text-left transition-[opacity,transform] duration-150 ease-out active:scale-[0.96] disabled:opacity-40"
    >
      <span className="text-sm font-medium text-foreground">{label}</span>
      <span
        className={cn(
          "relative h-7 w-12 shrink-0 rounded-full transition-[background-color] duration-150 ease-out",
          checked ? "bg-hot" : "bg-elevated shadow-[var(--shadow-border)]",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 size-6 rounded-full bg-foreground transition-transform duration-150 ease-out",
            checked ? "translate-x-5" : "translate-x-0.5",
          )}
        />
      </span>
    </button>
  );
}
