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
    <nav className="game-pagination" aria-label="Pagination">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className="game-page-button"
      >
        Prev
      </button>
      {pages.map((p, i) =>
        p === "dots" ? (
          <span key={`d${i}`} className="game-page-dots">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`game-page-button ${p === currentPage ? "is-current" : ""}`}
            aria-current={p === currentPage ? "page" : undefined}
          >
            {p}
          </button>
        ),
      )}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="game-page-button"
      >
        Next
      </button>
    </nav>
  );
}
