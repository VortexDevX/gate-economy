export default function ErrorAlert({ message }: { message: string }) {
  return (
    <div
      className="text-sm rounded-lg px-4 py-3 border"
      style={{
        background: "linear-gradient(145deg, #ffe6e6, #ffdada)",
        borderColor: "#f3b1b1",
        color: "#9b2c2c",
        boxShadow:
          "8px 8px 16px rgba(202, 161, 161, 0.32), -8px -8px 16px rgba(255,255,255,0.92)",
      }}
    >
      {message}
    </div>
  );
}
