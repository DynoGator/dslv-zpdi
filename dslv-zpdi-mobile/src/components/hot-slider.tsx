export function HotSlider({
  label,
  value,
  min,
  max,
  onChange,
  display,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (n: number) => void;
  display: string;
}) {
  return (
    <label className="block">
      <div className="mb-1 flex justify-between font-mono text-xs text-muted">
        <span>{label}</span>
        <span className="tabular-nums text-foreground">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
      />
    </label>
  );
}
