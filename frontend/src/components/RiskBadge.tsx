export default function RiskBadge({ level }: { level: "Safe" | "Low" | "Medium" | "High" | string }) {
  const styles =
    level === "High"
      ? "bg-red-100 text-red-700"
      : level === "Medium"
        ? "bg-amber-100 text-amber-700"
        : level === "Low"
          ? "bg-lime-100 text-lime-700"
          : "bg-emerald-100 text-emerald-700";

  return <span className={`rounded-full px-3 py-1 text-sm font-semibold ${styles}`}>{level}</span>;
}
