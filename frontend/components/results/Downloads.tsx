"use client";

import Link from "next/link";
import { Icons } from "@/components/icons";

export function ArtifactDownloads({ runId }: { runId: string }) {
  const items = [
    { label: "model.json", href: `/api/runs/${runId}/export?format=json`, hint: "Modelo autocontido para o simulador" },
    { label: "weights.npz", href: `/api/runs/${runId}/export?format=npz`, hint: "Pesos e biases do melhor checkpoint" },
    { label: "run.json", href: `/api/runs/${runId}/export?format=manifest`, hint: "Configuração e métricas da execução" },
  ];

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <a
          key={item.label}
          href={item.href}
          download
          className="flex items-center justify-between gap-3 rounded-lg border border-border bg-panel-2 px-4 py-3 text-sm hover:border-primary/50 hover:text-primary transition-colors"
        >
          <span className="flex items-center gap-2 font-mono">
            <Icons.Download className="w-4 h-4" />
            {item.label}
          </span>
          <span className="text-xs text-muted">{item.hint}</span>
        </a>
      ))}
    </div>
  );
}

export function ResultActions({ runId }: { runId: string }) {
  return (
    <div className="flex flex-wrap gap-2">
      <Link href={`/treinar?from=${runId}`} className="px-3 py-2 rounded-md border border-border bg-panel text-sm hover:bg-panel-2 transition-colors">
        Repetir configuração
      </Link>
      <Link href={`/simulador?run=${runId}`} className="px-3 py-2 rounded-md border border-border bg-panel text-sm hover:bg-panel-2 transition-colors">
        Usar no simulador
      </Link>
      <Link href={`/comparar?ids=${runId}`} className="px-3 py-2 rounded-md border border-border bg-panel text-sm hover:bg-panel-2 transition-colors">
        Comparar
      </Link>
    </div>
  );
}
