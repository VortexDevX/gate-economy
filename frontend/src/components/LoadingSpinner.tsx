export default function LoadingSpinner({
  className = "",
}: {
  className?: string;
}) {
  return (
    <div className={`game-loading ${className}`} role="status" aria-live="polite">
      <span className="game-loading-rune" aria-hidden="true"><i /><i /><i /></span>
      <span>Reading the world state…</span>
    </div>
  );
}
