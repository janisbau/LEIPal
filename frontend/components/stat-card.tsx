import { clsx } from "clsx";

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  trend?: "up" | "down" | "neutral";
}

export default function StatCard({ label, value, sub, trend }: StatCardProps) {
  return (
    <div className="bg-card border border-edge rounded-lg p-4 flex flex-col gap-2">
      <span className="text-[11px] uppercase tracking-widest text-muted">{label}</span>
      <span className="text-3xl font-semibold text-white tabular-nums">{value}</span>
      {sub && (
        <span
          className={clsx(
            "text-xs",
            trend === "up" && "text-teal",
            trend === "down" && "text-danger",
            trend === "neutral" && "text-muted",
            !trend && "text-muted"
          )}
        >
          {sub}
        </span>
      )}
    </div>
  );
}
