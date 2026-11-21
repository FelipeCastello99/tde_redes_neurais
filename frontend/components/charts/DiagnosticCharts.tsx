"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function PredictedProbHistogram({ histogram }: { histogram?: { counts: number[]; bin_edges: number[] } }) {
  if (!histogram || !histogram.counts?.length) {
    return <div className="h-full flex items-center justify-center text-sm text-muted">Histograma indisponível.</div>;
  }

  const data = histogram.counts.map((count, index) => ({
    bin: `${histogram.bin_edges[index].toFixed(1)}–${histogram.bin_edges[index + 1].toFixed(1)}`,
    count,
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="bin" tick={{ fontSize: 9, fill: "var(--muted)" }} interval={2} angle={-30} textAnchor="end" height={45} />
        <YAxis tick={{ fontSize: 10, fill: "var(--muted)" }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip contentStyle={{ backgroundColor: "var(--panel)", borderColor: "var(--border)", borderRadius: 6, fontSize: 12 }} />
        <Bar dataKey="count" name="Ocorrências" fill="var(--primary)" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CalibrationChart({ bins }: { bins?: { confidence: number; accuracy: number; count: number }[] }) {
  if (!bins || !bins.length) {
    return <div className="h-full flex items-center justify-center text-sm text-muted">Calibração indisponível.</div>;
  }

  const data = bins.map((bin) => ({
    ...bin,
    ideal: bin.confidence,
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="confidence" type="number" domain={[0, 1]} tick={{ fontSize: 10, fill: "var(--muted)" }} tickLine={false} axisLine={{ stroke: "var(--border)" }} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "var(--muted)" }} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={{ backgroundColor: "var(--panel)", borderColor: "var(--border)", borderRadius: 6, fontSize: 12 }} />
        <Line type="monotone" dataKey="ideal" name="Perfeito" stroke="var(--muted)" strokeDasharray="4 4" dot={false} isAnimationActive={false} />
        <Line type="monotone" dataKey="accuracy" name="Observado" stroke="var(--success)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
