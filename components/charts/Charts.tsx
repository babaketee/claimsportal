"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
  Legend,
} from "recharts";

const COLORWAY = ["#0f4f48", "#eb2229", "#3e756f", "#f17075", "#a8c7c4", "#1a8f87", "#c41e24", "#e5f0ef"];

export function StatusBarChart({ data }: { data: { status: string; n: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: -18, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis
          dataKey="status"
          angle={-35}
          textAnchor="end"
          interval={0}
          height={70}
          tick={{ fontSize: 11, fill: "#555" }}
        />
        <YAxis tick={{ fontSize: 11, fill: "#555" }} allowDecimals={false} />
        <Tooltip
          contentStyle={{ borderRadius: 10, borderColor: "#e0e0e0", fontSize: 12 }}
          labelStyle={{ fontWeight: 700, color: "#0f4f48" }}
        />
        <Bar dataKey="n" name="Claims" radius={[6, 6, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORWAY[i % COLORWAY.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CategoryPieChart({ data }: { data: { name: string; value: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORWAY[i % COLORWAY.length]} />
          ))}
        </Pie>
        <Legend
          verticalAlign="bottom"
          height={36}
          formatter={(v) => <span style={{ fontSize: 12, color: "#333" }}>{v}</span>}
        />
        <Tooltip contentStyle={{ borderRadius: 10, borderColor: "#e0e0e0", fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function ClaimTypeBarChart({ data }: { data: { claim_type: string; n: number; total: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: "#555" }} allowDecimals={false} />
        <YAxis
          type="category"
          dataKey="claim_type"
          width={150}
          tick={{ fontSize: 11, fill: "#555" }}
        />
        <Tooltip contentStyle={{ borderRadius: 10, borderColor: "#e0e0e0", fontSize: 12 }} />
        <Bar dataKey="n" name="Claims" fill="#0f4f48" radius={[0, 6, 6, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
