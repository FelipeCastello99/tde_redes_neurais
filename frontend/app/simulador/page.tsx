"use client";

import { useState, useEffect } from "react";
import { fetchMeta, getRuns, predictAccident } from "@/lib/api";
import { PageHeader } from "@/components/layout";
import { AccidentForm } from "@/components/simulator/AccidentForm";
import { ProbabilityCard } from "@/components/simulator/ProbabilityCard";
import { Icons } from "@/components/icons";

export default function SimuladorPage() {
  const [meta, setMeta] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [prediction, setPrediction] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [initialRunId, setInitialRunId] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isPredicting, setIsPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("tde_sim_history");
      if (raw) setHistory(JSON.parse(raw));
      const params = new URLSearchParams(window.location.search);
      setInitialRunId(params.get("run"));
    } catch {
      // localStorage indisponível
    }
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const [metaData, runsData] = await Promise.all([
          fetchMeta(),
          getRuns(50) // Traz runs para popular o select
        ]);
        setMeta(metaData);
        // Filtra apenas os runs que concluíram com sucesso
        setRuns(runsData.filter(r => r.status === 'done'));
      } catch (err: any) {
        setError(err.message || "Erro ao carregar dados do simulador");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const handleSimulate = async (runId: string, features: any) => {
    setIsPredicting(true);
    setError(null);
    try {
      const result = await predictAccident(runId, features);
      setPrediction(result);

      const run = runs.find((item) => item.id === runId);
      const entry = {
        at: new Date().toISOString(),
        runId,
        runName: run?.name || runId,
        predicted_class: result.predicted_class,
        probabilities: result.probabilities,
        features,
      };
      const next = [entry, ...history].slice(0, 5);
      setHistory(next);
      window.localStorage.setItem("tde_sim_history", JSON.stringify(next));
    } catch (err: any) {
      setError(err.message || "Erro ao executar simulação");
    } finally {
      setIsPredicting(false);
    }
  };

  const reuseHistory = (item: any) => {
    setPrediction({
      predicted_class: item.predicted_class,
      probabilities: item.probabilities,
      threshold_used: null,
      predicted_class_index: 0,
    });
  };

  if (isLoading) {
    return <div className="p-8 text-center text-muted animate-pulse">Carregando contexto do simulador...</div>;
  }

  return (
    <div className="max-w-[1200px] mx-auto space-y-6">
      <PageHeader 
        title="Simulador de Acidentes" 
        description="Preveja a probabilidade de gravidade de um acidente usando qualquer um dos modelos já treinados."
      />

      {error && (
        <div className="bg-danger/10 text-danger border border-danger/20 p-4 rounded-md flex items-center gap-3">
          <Icons.Warning className="w-5 h-5" />
          <p>{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative">
        <div className="lg:col-span-7">
          {meta && <AccidentForm meta={meta} runs={runs} onSimulate={handleSimulate} isPredicting={isPredicting} initialRunId={initialRunId} />}
        </div>
        
        <div className="lg:col-span-5">
          <div className="sticky top-24 space-y-6">
            <ProbabilityCard prediction={prediction} />
            {history.length > 0 && (
              <div className="bg-panel border border-border rounded-xl p-5 shadow-sm">
                <h3 className="text-xs font-bold text-muted uppercase tracking-wider mb-3">Últimas simulações</h3>
                <div className="space-y-2">
                  {history.map((item, index) => (
                    <button
                      key={`${item.at}-${index}`}
                      type="button"
                      onClick={() => reuseHistory(item)}
                      className="w-full text-left rounded-md border border-border bg-panel-2 px-3 py-2 hover:border-primary/50 transition-colors"
                    >
                      <span className="flex items-center justify-between gap-2 text-xs">
                        <span className="truncate font-medium text-text">{item.predicted_class}</span>
                        <span className="text-muted">{new Date(item.at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
                      </span>
                      <span className="mt-0.5 block truncate text-[11px] text-muted">{item.runName}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
