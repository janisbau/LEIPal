import { fetchLous, fmt } from "@/lib/api";
import { jurisdictionName } from "@/lib/jurisdictions";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function LousPage() {
  const lous = await fetchLous();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-white">LOU Explorer</h1>
        <p className="text-xs text-muted mt-0.5">
          {lous.length} Local Operating Units · ranked by active LEIs managed
        </p>
      </div>

      {/* Table */}
      <div className="bg-card border border-edge rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-edge text-left">
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                LOU
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                Country
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium text-right">
                Active LEIs
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium text-right">
                Total LEIs
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium text-right">
                Market Share
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {lous.map((lou, i) => (
              <tr
                key={lou.lou_lei}
                className="border-b border-edge/50 hover:bg-white/[0.02] transition-colors"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/lous/${lou.lou_lei}`}
                    className="group flex flex-col"
                  >
                    <span className="text-white group-hover:text-teal transition-colors font-medium truncate max-w-[220px]">
                      {lou.lou_name || "—"}
                    </span>
                    <span className="text-[11px] text-muted font-mono">
                      {lou.lou_lei}
                    </span>
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted">
                  {lou.country ? jurisdictionName(lou.country) : "—"}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-white">
                  {fmt(lou.active_leis)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-muted">
                  {fmt(lou.total_leis)}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-16 bg-edge rounded-full h-1 overflow-hidden">
                      <div
                        className="h-full bg-teal rounded-full"
                        style={{ width: `${Math.min(lou.market_share * 3, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs tabular-nums text-white w-10 text-right">
                      {lou.market_share.toFixed(1)}%
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`text-[11px] font-medium px-2 py-0.5 rounded uppercase tracking-wider ${
                      lou.status === "ACTIVE"
                        ? "bg-teal/10 text-teal"
                        : "bg-danger/10 text-danger"
                    }`}
                  >
                    {lou.status || "—"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
