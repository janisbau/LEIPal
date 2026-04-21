import { fetchSummary, fetchGrowth, fmt } from "@/lib/api";
import { jurisdictionName } from "@/lib/jurisdictions";
import StatCard from "@/components/stat-card";
import GrowthChart from "@/components/growth-chart";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const [summary, growth] = await Promise.all([fetchSummary(), fetchGrowth()]);

  const activeCount = summary.by_status?.ACTIVE ?? 0;
  const inactiveCount = summary.by_status?.INACTIVE ?? 0;
  const activeRate = summary.total_leis
    ? ((activeCount / summary.total_leis) * 100).toFixed(1)
    : "—";

  // Most recent month's new LEIs
  const lastMonth = growth.at(-1);
  const prevMonth = growth.at(-2);
  const newThisMonth = lastMonth?.new_leis ?? 0;
  const newLastMonth = prevMonth?.new_leis ?? 0;
  const momDelta = newLastMonth
    ? (((newThisMonth - newLastMonth) / newLastMonth) * 100).toFixed(1)
    : null;

  const lastRunIso = summary.last_pipeline_run?.applied_at ?? null;
  const lastRun = lastRunIso
    ? new Date(lastRunIso).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "—";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Market Overview</h1>
          <p className="text-xs text-muted mt-0.5">
            Global LEI ecosystem · Last updated {lastRun}
          </p>
        </div>
        <span className="text-[11px] uppercase tracking-widest text-muted border border-edge rounded px-2 py-1">
          GLEIF Golden Copy
        </span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total LEIs"
          value={fmt(summary.total_leis)}
          sub="All registered entities"
          trend="neutral"
        />
        <StatCard
          label="Active LEIs"
          value={fmt(activeCount)}
          sub={`${activeRate}% of total`}
          trend="up"
        />
        <StatCard
          label="New This Month"
          value={fmt(newThisMonth)}
          sub={
            momDelta !== null
              ? `${Number(momDelta) >= 0 ? "+" : ""}${momDelta}% vs last month`
              : "—"
          }
          trend={
            momDelta !== null
              ? Number(momDelta) >= 0
                ? "up"
                : "down"
              : "neutral"
          }
        />
        <StatCard
          label="Active LOUs"
          value={String(summary.lous_count)}
          sub="Local Operating Units"
          trend="neutral"
        />
      </div>

      {/* Growth chart */}
      <div className="bg-card border border-edge rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-medium text-white">Cumulative LEI Growth</h2>
            <p className="text-xs text-muted mt-0.5">Total registered LEIs over time</p>
          </div>
        </div>
        <GrowthChart data={growth} />
      </div>

      {/* Top jurisdictions */}
      <div className="bg-card border border-edge rounded-lg p-4">
        <h2 className="text-sm font-medium text-white mb-4">Top Jurisdictions</h2>
        <div className="space-y-2">
          {(summary.top_jurisdictions ?? []).slice(0, 10).map(
            (j: { jurisdiction: string; count: number; share?: number }) => {
              const share =
                j.share !== undefined
                  ? j.share
                  : summary.total_leis
                  ? (j.count / summary.total_leis) * 100
                  : 0;
              return (
                <div key={j.jurisdiction} className="flex items-center gap-3">
                  <span className="w-36 text-xs text-white truncate">
                    {jurisdictionName(j.jurisdiction)}
                  </span>
                  <div className="flex-1 bg-edge rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-full bg-teal rounded-full"
                      style={{ width: `${Math.min(share * 4, 100)}%` }}
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
    </div>
  );
}
