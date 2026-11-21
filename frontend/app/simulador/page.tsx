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
  
  const [isLoading, setIsLoading] = useState(true);
  const [isPredicting, setIsPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    } catch (err: any) {
      setError(err.message || "Erro ao executar simulação");
    } finally {
      setIsPredicting(false);
    }
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
          {meta && <AccidentForm meta={meta} runs={runs} onSimulate={handleSimulate} isPredicting={isPredicting} />}
        </div>
        
        <div className="lg:col-span-5">
          <div className="sticky top-24">
            <ProbabilityCard prediction={prediction} />
          </div>
        </div>
      </div>
    </div>
  );
}
