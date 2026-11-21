"use client";

import { useState } from "react";
import { ParameterForm } from "@/components/form/ParameterForm";
import { RunCreate } from "@/lib/validation";
import { PageHeader } from "@/components/layout";
import { createRun } from "@/lib/api";
import { Icons } from "@/components/icons";

import { RunProgress } from "@/components/training/RunProgress";

export default function TreinarPage() {
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (data: RunCreate) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await createRun(data.name, data.data, data.model);
      setActiveRunId(res.run_id);
    } catch (err: any) {
      setError(err.message || "Erro desconhecido ao iniciar treino");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <PageHeader 
        title="Treinamento de Rede Neural" 
        description="Configure os hiperparâmetros ou use uma predefinição para iniciar."
      />
      
      {error && (
        <div className="bg-danger/10 text-danger border border-danger/20 p-4 rounded-md flex items-center gap-3">
          <Icons.Warning className="w-5 h-5" />
          <p>{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative">
        <div className="lg:col-span-6 xl:col-span-5">
          <ParameterForm onSubmit={onSubmit} isSubmitting={isSubmitting} />
        </div>
        
        <div className="lg:col-span-6 xl:col-span-7">
          <div className="sticky top-24 bg-panel border border-border rounded-xl p-6 min-h-[400px] shadow-sm flex flex-col">
            <h2 className="text-xl font-bold text-text mb-4">Progresso do Treinamento</h2>
            
            {!activeRunId ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted gap-4">
                <Icons.Dashboard className="w-12 h-12 opacity-20" />
                <p>Nenhum treinamento em andamento.</p>
                <p className="text-sm max-w-xs text-center">Configure os parâmetros ao lado e clique em Iniciar para acompanhar ao vivo.</p>
              </div>
            ) : (
              <div className="flex-1">
                <RunProgress runId={activeRunId} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
