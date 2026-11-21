"use client";

import { formatPercent } from "@/lib/format";

export type Contribution = {
  feature: string;
  delta: number;
  value?: string;
};

export function ContributionBars({ contributions }: { contributions?: Contribution[] }) {
  if (!contributions || contributions.length === 0) {
    return (
      <p className="text-xs text-muted">
        Contribuições por campo ainda não foram retornadas pelo backend para este modelo.
      </p>
    );
  }

  const maxAbs = Math.max(...contributions.map((item) => Math.abs(item.delta)), 1e-9);

  return (
    <div className="space-y-2">
      {contributions.slice(0, 6).map((item) => {
        const width = Math.max(3, (Math.abs(item.delta) / maxAbs) * 100);
        const positive = item.delta >= 0;
        return (
          <div key={item.feature} className="space-y-1">
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate text-text" title={item.feature}>{item.feature}</span>
              <span className={`font-mono ${positive ? "text-danger" : "text-success"}`}>
                {positive ? "+" : ""}{formatPercent(item.delta, 2)}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-panel-2 overflow-hidden">
              <div
                className={`h-full rounded-full ${positive ? "bg-danger" : "bg-success"}`}
                style={{ width: `${width}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
