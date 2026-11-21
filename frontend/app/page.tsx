"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { getRuns } from "@/lib/api";
import { PageHeader, StatCard } from "@/components/layout";
import { Icons } from "@/components/icons";
import { formatDate, formatTime, formatPercent } from "@/lib/format";

export default function DashboardPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getRuns(50);
        setRuns(data);
      } catch (err: any) {
        setError(err.message || "Erro ao carregar runs");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  // Aggregações simples
  const stats = useMemo(() => {
    const doneRuns = runs.filter(r => r.status === 'done');
    const bestF1 = doneRuns.reduce((acc, curr) => {
      const f1 = curr.metrics?.precision_recall_f1?.macro?.f1 || 0;
      return f1 > acc ? f1 : acc;
    }, 0);
    const avgTime = doneRuns.length > 0 
      ? doneRuns.reduce((acc, curr) => acc + (curr.duration_s || 0), 0) / doneRuns.length 
      : 0;

    return {
      total: runs.length,
      done: doneRuns.length,
      bestF1,
      avgTime
    };
  }, [runs]);

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <PageHeader 
          title="Dashboard" 
          description="Visão geral e histórico de treinamentos do modelo de acidentes."
        />
        <Link 
          href="/treinar"
          className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white font-medium px-5 py-2.5 rounded-lg shadow-sm transition-colors w-fit mb-8"
        >
          <Icons.Play className="w-4 h-4" />
          Novo Treinamento
        </Link>
      </div>

      {error && (
        <div className="bg-danger/10 text-danger border border-danger/20 p-4 rounded-md flex items-center gap-3">
          <Icons.Warning className="w-5 h-5" />
          <p>{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          title="Total de Runs" 
          value={stats.total} 
          icon={Icons.History}
          description={`${stats.done} concluídos com sucesso`}
        />
        <StatCard 
          title="Melhor F1 Macro" 
          value={formatPercent(stats.bestF1)} 
          icon={Icons.Chart}
          description="Considerando todos os treinos concluídos"
        />
        <StatCard 
          title="Tempo Médio" 
          value={formatTime(stats.avgTime)} 
          icon={Icons.System}
          description="Duração média de treinamento"
        />
        <StatCard 
          title="Amostras no Dataset" 
          value="73.201" 
          icon={Icons.Dashboard}
          description="PRF DATATRAN 2024"
        />
      </div>

      <div className="bg-panel border border-border rounded-xl shadow-sm overflow-hidden mt-8">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h2 className="text-lg font-bold text-text">Histórico Recente</h2>
        </div>
        
        {isLoading ? (
          <div className="p-8 text-center text-muted animate-pulse">Carregando execuções...</div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <Icons.Dashboard className="w-12 h-12 text-muted/30 mb-4" />
            <h3 className="text-lg font-semibold text-text mb-1">Nenhum treino realizado</h3>
            <p className="text-muted text-sm max-w-sm mb-6">Comece treinando um novo modelo para testar diferentes arquiteturas e hiperparâmetros.</p>
            <Link 
              href="/treinar"
              className="bg-primary/10 text-primary hover:bg-primary/20 font-medium px-4 py-2 rounded-md transition-colors"
            >
              Começar agora
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted uppercase bg-panel-2 border-b border-border">
                <tr>
                  <th className="px-6 py-3 font-medium">Data</th>
                  <th className="px-6 py-3 font-medium">Nome & Status</th>
                  <th className="px-6 py-3 font-medium">Alvo</th>
                  <th className="px-6 py-3 font-medium text-right">Métricas (Teste)</th>
                  <th className="px-6 py-3 font-medium text-right">Épocas</th>
                  <th className="px-6 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {runs.map((r) => {
                  const isDone = r.status === 'done';
                  const metrics = r.metrics;
                  
                  return (
                    <tr key={r.id} className="hover:bg-panel-2/30 transition-colors">
                      <td className="px-6 py-4 text-muted whitespace-nowrap">
                        {formatDate(r.created_at)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-semibold text-text">{r.name}</div>
                        <div className="flex items-center gap-1.5 mt-1">
                          <span className={`inline-block w-2 h-2 rounded-full ${
                            r.status === 'done' ? 'bg-success' : 
                            r.status === 'failed' ? 'bg-danger' : 
                            r.status === 'canceled' ? 'bg-warning' : 'bg-primary animate-pulse'
                          }`}></span>
                          <span className="text-xs uppercase font-medium text-muted tracking-wide">{r.status}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-muted">
                        {r.target === 'fatal_binario' ? 'Binário' : 'Multiclasse (3)'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {isDone && metrics ? (
                          <div className="flex flex-col items-end gap-0.5">
                            <span className="font-medium text-text">F1: {formatPercent(metrics.precision_recall_f1.macro.f1)}</span>
                            <span className="text-xs text-muted">ROC: {formatPercent(metrics.roc_auc)}</span>
                          </div>
                        ) : (
                          <span className="text-muted">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right text-muted font-mono">
                        {r.best_epoch || r.config.model.epochs} / {r.config.model.epochs}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {isDone && (
                          <Link 
                            href={`/resultados/${r.id}`}
                            className="text-primary hover:text-primary/80 font-medium text-sm transition-colors"
                          >
                            Analisar →
                          </Link>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
