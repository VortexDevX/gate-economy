export default function EmptyState({
  message = "Nothing to show yet",
}: {
  message?: string;
}) {
  return (
    <div className="game-empty-compact">
      <Sparkles size={21} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

import { Sparkles } from "lucide-react";
