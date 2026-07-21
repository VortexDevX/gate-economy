import { AlertTriangle } from "lucide-react";

export default function ErrorAlert({ message }: { message: string }) {
  return (
    <div className="game-error-alert" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <div><strong>Signal disrupted</strong><span>{message}</span></div>
    </div>
  );
}
