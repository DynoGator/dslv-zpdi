export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect x="1" y="1" width="30" height="30" rx="6" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="16" cy="16" r="2.2" fill="currentColor" />
      <path
        d="M16 6.5 A9.5 9.5 0 0 1 25.5 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="M16 9.2 A6.8 6.8 0 0 1 22.8 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity="0.7"
      />
      <path
        d="M16 25.5 A9.5 9.5 0 0 1 6.5 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity="0.55"
      />
    </svg>
  );
}
