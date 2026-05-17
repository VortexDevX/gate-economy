interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const pages: (number | "dots")[] = [];
  pages.push(1);
  if (currentPage > 3) pages.push("dots");
  for (
    let i = Math.max(2, currentPage - 1);
    i <= Math.min(totalPages - 1, currentPage + 1);
    i++
  ) {
    pages.push(i);
  }
  if (currentPage < totalPages - 2) pages.push("dots");
  if (totalPages > 1) pages.push(totalPages);

  return (
    <div className="flex items-center justify-center gap-1 mt-4">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className="px-3 py-1.5 text-sm rounded bg-gray-900 border border-gray-800
                   disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Prev
      </button>
      {pages.map((p, i) =>
        p === "dots" ? (
          <span key={`d${i}`} className="px-2 text-gray-500">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`px-3 py-1.5 text-sm rounded border ${
              p === currentPage
                ? "bg-brand-600 text-white border-transparent"
                : "bg-gray-900 border-gray-800"
            }`}
          >
            {p}
          </button>
        ),
      )}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="px-3 py-1.5 text-sm rounded bg-gray-900 border border-gray-800
                   disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Next
      </button>
    </div>
  );
}
