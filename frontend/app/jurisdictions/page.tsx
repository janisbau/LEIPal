import { fetchJurisdictions, fmt } from "@/lib/api";
import { jurisdictionName } from "@/lib/jurisdictions";

export const dynamic = "force-dynamic";

export default async function JurisdictionsPage() {
  const jurisdictions = await fetchJurisdictions();

  const maxCount = jurisdictions[0]?.count ?? 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-white">Jurisdictions</h1>
        <p className="text-xs text-muted mt-0.5">
          Active LEIs by jurisdiction · Top {jurisdictions.length} markets
        </p>
      </div>

      {/* Bar chart table */}
      <div className="bg-card border border-edge rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-edge text-left">
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium w-8">
                #
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium w-16">
                Code
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                Jurisdiction
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium">
                Distribution
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium text-right">
                Active LEIs
              </th>
              <th className="px-4 py-3 text-[11px] uppercase tracking-widest text-muted font-medium text-right">
                Share
              </th>
            </tr>
          </thead>
          <tbody>
            {jurisdictions.map((j, i) => (
              <tr
                key={j.jurisdiction}
                className="border-b border-edge/50 hover:bg-white/[0.02] transition-colors"
              >
                <td className="px-4 py-3 text-muted text-xs tabular-nums">
                  {i + 1}
                </td>
                <td className="px-4 py-3 font-mono text-muted text-xs">
                  {j.jurisdiction}
                </td>
                <td className="px-4 py-3 text-white text-sm">
                  {jurisdictionName(j.jurisdiction)}
                </td>
                <td className="px-4 py-3">
                  <div className="w-full bg-edge rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-full bg-teal rounded-full"
                      style={{
                        width: `${(j.count / maxCount) * 100}%`,
                      }}
                    />
                  </div>
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-white">
                  {fmt(j.count)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-muted">
                  {j.share.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
