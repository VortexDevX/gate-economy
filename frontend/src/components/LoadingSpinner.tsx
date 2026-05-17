export default function LoadingSpinner({
  className = "",
}: {
  className?: string;
}) {
  return (
    <div className={`flex items-center justify-center py-12 ${className}`}>
      <div className="rounded-full p-3 bg-gray-900 border border-gray-800">
        <div className="animate-spin rounded-full h-7 w-7 border-2 border-brand-500 border-t-transparent" />
      </div>
    </div>
  );
}
