export default function EmptyState({
  message = "Nothing to show yet",
}: {
  message?: string;
}) {
  return (
    <div className="text-sm text-center py-12 px-4 rounded-lg bg-gray-900 border border-gray-800 nm-soft-note">
      {message}
    </div>
  );
}

