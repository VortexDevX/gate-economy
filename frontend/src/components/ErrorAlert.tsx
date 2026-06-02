export default function ErrorAlert({ message }: { message: string }) {
  return (
    <div
      className="text-sm rounded-lg px-4 py-3 border"
      style={{
        background: "rgba(241, 104, 88, 0.14)",
        borderColor: "rgba(241, 104, 88, 0.48)",
        color: "var(--nm-bad)",
        boxShadow: "inset 0 1px 0 rgba(255, 232, 178, 0.1)",
      }}
    >
      {message}
    </div>
  );
}
