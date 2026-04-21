import { fetchLou, fmt } from "@/lib/api";
import { jurisdictionName } from "@/lib/jurisdictions";
import StatCard from "@/components/stat-card";
import { notFound } from "next/navigation";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function LouDetailPage({
  params,
}: {
  params: Promise<{ lei: string }>;
}) {
  const { lei } = await params;

  let lou: Awaited<ReturnType<typeof fetchLou>>;
  try {
    lou = await fetchLou(lei);
  } catch {
    notFound();
  }

  const activeRate = lou.total_leis
    ? ((lou.active_leis / lou.total_leis) * 100).toFixed(1)
    : "—";

  const firstYear = lou.first_registration
    ? new Date(lou.first_registration).getFullYear()
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">{lou.lou_name}</h1>
          <p className="text-xs text-muted mt-0.5 font-mono">{lou.lou_lei}</p>
        </div>
        <div className="flex items-center gap-2">
          {lou.country && (
            <span className="text-xs text-muted border border-edge rounded px-2 py-1">
              {jurisdictionName(lou.country)}
            </span>
          )}
          <Link
            href={`/lei/${lou.lou_lei}`}
            className="text-xs text-muted hover:text-white border border-edge rounded px-2 py-1 transition-colors"
          >
            View Entity →
          </Link>
          <span
            className={`text-xs font-medium px-2 py-1 rounded uppercase tracking-wider ${
              lou.status === "ACTIVE"
                ? "bg-teal/10 text-teal border border-teal/20"
                : "bg-danger/10 text-danger border border-danger/20"
            }`}
          >
            {lou.status}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Active LEIs"
          value={fmt(lou.active_leis)}
          sub={`${activeRate}% active rate`}
          trend="up"
        />
        <StatCard
          label="Total LEIs"
          value={fmt(lou.total_leis)}
          sub="Including inactive"
          trend="neutral"
        />
        <StatCard
          label="Inactive LEIs"
          value={fmt(lou.inactive_leis)}
          sub={`${lou.total_leis ? ((lou.inactive_leis / lou.total_leis) * 100).toFixed(1) : 0}% lapsed`}
          trend={lou.inactive_leis > lou.active_leis ? "down" : "neutral"}
        />
        <StatCard
          label="Operating Since"
          value={firstYear ? String(firstYear) : "—"}
          sub={
            lou.last_registration
              ? `Last reg. ${new Date(lou.last_registration).toLocaleDateString("en-US", { month: "short", year: "numeric" })}`
              : ""
          }
          trend="neutral"
        />
      </div>

      {/* Jurisdiction breakdown */}
      {lou.top_jurisdictions?.length > 0 && (
        <div className="bg-card border border-edge rounded-lg p-4">
          <h2 className="text-sm font-medium text-white mb-4">
            Top Jurisdictions
          </h2>
          <div className="space-y-2">
            {lou.top_jurisdictions.map(
              (j: { jurisdiction: string; count: number }) => {
                const share = lou.total_leis
                  ? (j.count / lou.total_leis) * 100
                  : 0;
                return (
                  <div key={j.jurisdiction} className="flex items-center gap-3">
                    <span className="w-36 text-xs text-white truncate">
                      {jurisdictionName(j.jurisdiction)}
                    </span>
                    <div className="flex-1 bg-edge rounded-full h-1.5 overflow-hidden">
                      <div
                        className="h-full bg-teal rounded-full"
                        style={{ width: `${Math.min(share * 2, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-white tabular-nums w-16 text-right">
                      {fmt(j.count)}
                    </span>
                    <span className="text-xs text-muted w-10 text-right">
                      {share.toFixed(1)}%
                    </span>
                  </div>
                );
              }
            )}
          </div>
        </div>
      )}
    </div>
  );
}
