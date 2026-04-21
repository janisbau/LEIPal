"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DataPoint {
  month: string;
  cumulative: number;
  new_leis: number;
}

function fmtY(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return n.toString();
}

function fmtMonth(iso: string) {
  const [year, month] = iso.split("-");
  const d = new Date(Number(year), Number(month) - 1);
  return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

interface TooltipProps {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-edge rounded px-3 py-2 text-xs">
      <p className="text-muted mb-1">{label}</p>
      <p className="text-white font-semibold">{fmtY(payload[0].value)} total LEIs</p>
    </div>
  );
}

export default function GrowthChart({ data }: { data: DataPoint[] }) {
  // Show every 6th month label to avoid crowding
  const ticks = data
    .filter((_, i) => i % 6 === 0)
    .map((d) => d.month);

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <defs>
          <linearGradient id="tealGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#00D4AA" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#00D4AA" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="month"
          ticks={ticks}
          tickFormatter={fmtMonth}
          tick={{ fill: "#8B949E", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={fmtY}
          tick={{ fill: "#8B949E", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={45}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: "#21262D" }} />
        <Area
          type="monotone"
          dataKey="cumulative"
          stroke="#00D4AA"
          strokeWidth={2}
          fill="url(#tealGrad)"
          dot={false}
          activeDot={{ r: 4, fill: "#00D4AA" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
