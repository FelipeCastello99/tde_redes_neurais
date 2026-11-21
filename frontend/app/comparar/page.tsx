"use client";

import { useEffect, useState } from "react";
import { getRuns } from "@/lib/api";
import { PageHeader } from "@/components/layout";
import { formatPercent, formatTime } from "@/lib/format";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

export default function CompararPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getRuns(50);
        // Permite comparar apenas runs finalizados
        setRuns(data.filter(r => r.status === 'done'));
      } catch (err: any) {
        setError(err.message || "Erro ao carregar runs");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (runs.length === 0) return;
    try {
      const raw = new URLSearchParams(window.location.search).get("ids");
      if (!raw) return;
      const valid = raw.split(",").filter((id) => runs.some((run) => run.id === id));
      if (valid.length > 0) setSelectedIds(valid.slice(0, 4));
    } catch {
      // URL indisponível
    }
  }, [runs]);

  const toggleRun = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(x => x !== id));
    } else {
      if (selectedIds.length >= 4) return; // Limita a 4 runs p/ comparação
      setSelectedIds([...selectedIds, id]);
    }
  };

  const selectedRuns = runs.filter(r => selectedIds.includes(r.id));

  // Dados para o gráfico comparativo
  const chartData = selectedRuns.map(r => ({
    name: r.name.substring(0, 15) + (r.name.length > 15 ? '...' : ''),
    f1_macro: (r.metrics?.precision_recall_f1?.macro?.f1 || 0) * 100,
    roc_auc: (r.metrics?.roc_auc || 0) * 100,
    acc: (r.metrics?.accuracy || 0) * 100,
  }));

  return (
    <div className="max-w-[1400px] mx-auto space-y-8 pb-12">
      <PageHeader 
        title="Comparar Treinamentos" 
        description="Selecione até 4 execuções concluídas para comparar hiperparâmetros e desempenho lado a lado."
      />

      {error && (
        <div className="bg-danger/10 text-danger border border-danger/20 p-4 rounded-md">
          {error}
        </div>
      )}

      {/* Seletor */}
      <div className="bg-panel border border-border p-5 rounded-xl shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-text uppercase tracking-wider">Selecionar (Máx 4)</h3>
        {isLoading ? (
          <div className="animate-pulse h-10 bg-panel-2 rounded"></div>
        ) : runs.length === 0 ? (
          <div className="text-sm text-muted">Não há execuções concluídas para comparar.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-60 overflow-y-auto pr-2">
            {runs.map(r => {
              const isSelected = selectedIds.includes(r.id);
              const disabled = !isSelected && selectedIds.length >= 4;
              return (
                <label 
                  key={r.id} 
                  className={`flex items-start gap-3 p-3 rounded-lg border transition-colors cursor-pointer ${
                    isSelected ? 'border-primary bg-primary/5' : disabled ? 'border-border opacity-50 cursor-not-allowed' : 'border-border hover:bg-panel-2'
                  }`}
                >
                  <input 
                    type="checkbox" 
                    checked={isSelected}
                    onChange={() => toggleRun(r.id)}
                    disabled={disabled}
                    className="mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-text truncate">{r.name}</p>
                    <p className="text-xs text-muted mt-0.5">F1: {formatPercent(r.metrics?.precision_recall_f1?.macro?.f1 || 0)}</p>
                  </div>
                </label>
              );
            })}
          </div>
        )}
      </div>

      {selectedRuns.length > 0 && (
        <div className="space-y-8 animate-in fade-in duration-300">
          
          {/* Gráfico de Barras */}
          <div className="bg-panel border border-border p-5 rounded-xl shadow-sm h-80">
            <h3 className="text-sm font-bold text-text uppercase tracking-wider mb-4">Desempenho Geral (%)</h3>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--border)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: 'var(--panel-2)' }} contentStyle={{ backgroundColor: 'var(--panel)', borderColor: 'var(--border)', borderRadius: '6px' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="f1_macro" name="F1 Macro" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="roc_auc" name="ROC AUC" fill="var(--accent)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="acc" name="Acurácia" fill="var(--success)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Tabela Comparativa de Hiperparâmetros */}
          <div className="bg-panel border border-border rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted uppercase bg-panel-2 border-b border-border">
                  <tr>
                    <th className="px-4 py-3 font-medium">Parâmetro / Métrica</th>
                    {selectedRuns.map(r => (
                      <th key={r.id} className="px-4 py-3 font-bold text-text truncate max-w-[150px]" title={r.name}>{r.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {/* Métricas */}
                  <tr className="bg-primary/5">
                    <td className="px-4 py-3 font-bold text-primary">F1-Score (Macro)</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3 font-bold">{formatPercent(r.metrics?.precision_recall_f1?.macro?.f1 || 0)}</td>)}
                  </tr>
                  <tr className="bg-primary/5">
                    <td className="px-4 py-3 font-bold text-primary">ROC AUC</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3 font-bold">{formatPercent(r.metrics?.roc_auc || 0)}</td>)}
                  </tr>
                  
                  {/* Arquitetura */}
                  <tr>
                    <td className="px-4 py-3 font-medium text-muted">Alvo</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3">{r.target === 'fatal_binario' ? 'Binário' : '3 Classes'}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-muted">Camadas Ocultas</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3">{r.config.model.hidden_layers}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-muted">Neurônios</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3 font-mono">{JSON.stringify(r.config.model.neurons)}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-muted">Otimizador</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3 uppercase">{r.config.model.optimizer}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-muted">Learning Rate</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3">{r.config.model.lr}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-muted">Função Loss</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3">{r.config.model.loss}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-muted">Épocas Percorridas</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3">{r.best_epoch || r.config.model.epochs} / {r.config.model.epochs}</td>)}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-muted">Duração</td>
                    {selectedRuns.map(r => <td key={r.id} className="px-4 py-3">{formatTime(r.duration_s || 0)}</td>)}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
