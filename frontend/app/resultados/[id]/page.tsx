"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { getRun } from "@/lib/api";
import { RunHeader, MetricsGrid } from "@/components/results/Header";
import { ConfusionMatrix } from "@/components/charts/ConfusionMatrix";
import { RocPrChart, ThresholdChart } from "@/components/charts/EvaluationCharts";
import { PredictedProbHistogram, CalibrationChart } from "@/components/charts/DiagnosticCharts";
import { MetricsGridDetailed, HyperparameterTable } from "@/components/results/Details";
import { ArtifactDownloads, ResultActions } from "@/components/results/Downloads";
import { Icons } from "@/components/icons";

export default function ResultadosPage() {
  const { id } = useParams() as { id: string };
  const [run, setRun] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getRun(id);
        setRun(data);
      } catch (err: any) {
        setError(err.message || "Erro ao carregar resultados");
      }
    }
    load();
  }, [id]);

  if (error) {
    return (
      <div className="bg-danger/10 text-danger border border-danger/20 p-4 rounded flex items-center gap-3">
        <Icons.Warning className="w-5 h-5" />
        <p>{error}</p>
      </div>
    );
  }

  if (!run) {
    return <div className="animate-pulse space-y-4">
      <div className="h-24 bg-panel-2 rounded-xl border border-border"></div>
      <div className="grid grid-cols-4 gap-4"><div className="h-24 bg-panel-2 rounded-xl border border-border"></div></div>
    </div>;
  }

  const { metrics, config, target } = run;
  const isBinary = target === 'fatal_binario';
  // O class_names no metadata seria o ideal, mas sabemos pelo target
  const classNames = isBinary ? ['sem_vitima_fatal', 'vitima_fatal'] : ['Sem Vítimas', 'Com Vítimas Feridas', 'Com Vítimas Fatais'];

  return (
    <div className="max-w-[1400px] mx-auto space-y-6 pb-12">
      <RunHeader run={run} />
      
      {metrics ? (
        <>
          <MetricsGrid metrics={metrics} classNames={classNames} target={target} />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Matriz de Confusão */}
            <div className="lg:col-span-4 bg-panel border border-border rounded-xl p-5 shadow-sm flex flex-col min-h-[350px]">
              <h3 className="text-sm font-bold text-text mb-4 uppercase tracking-wider">Matriz de Confusão</h3>
              <div className="flex-1 min-h-0">
                <ConfusionMatrix matrix={metrics.confusion_matrix} classNames={classNames} />
              </div>
            </div>

            {/* ROC e PR */}
            <div className="lg:col-span-4 bg-panel border border-border rounded-xl p-5 shadow-sm flex flex-col min-h-[350px]">
              <h3 className="text-sm font-bold text-text mb-4 uppercase tracking-wider">Áreas (ROC/PR)</h3>
              <div className="flex-1 min-h-0">
                <RocPrChart 
                  roc_details={metrics.roc_auc_details} 
                  pr_details={metrics.pr_auc_details} 
                  classNames={classNames} 
                />
              </div>
            </div>

            {/* Threshold Sweep */}
            <div className="lg:col-span-4 bg-panel border border-border rounded-xl p-5 shadow-sm flex flex-col min-h-[350px]">
              <h3 className="text-sm font-bold text-text mb-4 uppercase tracking-wider">
                {isBinary ? 'Varredura de Limiar' : 'Métricas'}
              </h3>
              <div className="flex-1 min-h-0">
                <ThresholdChart sweep={metrics.threshold_sweep} />
              </div>
            </div>

          </div>

          <div className="bg-panel border border-border rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-text mb-4 uppercase tracking-wider">Métricas Detalhadas por Classe</h3>
            <MetricsGridDetailed 
              per_class={metrics.precision_recall_f1.per_class}
              macro={metrics.precision_recall_f1.macro}
              weighted={metrics.precision_recall_f1.weighted}
              classNames={classNames}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-panel border border-border rounded-xl p-5 shadow-sm h-[300px]">
              <h3 className="text-sm font-bold text-text mb-4 uppercase tracking-wider">Histograma de Probabilidades</h3>
              <div className="h-[230px]">
                <PredictedProbHistogram histogram={metrics.prediction_histogram} />
              </div>
            </div>
            <div className="bg-panel border border-border rounded-xl p-5 shadow-sm h-[300px]">
              <h3 className="text-sm font-bold text-text mb-4 uppercase tracking-wider">Calibração (ECE {metrics.ece?.toFixed(3)})</h3>
              <div className="h-[230px]">
                <CalibrationChart bins={metrics.calibration_bins} />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-panel border border-border rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-bold text-text mb-4 uppercase tracking-wider">Hiperparâmetros</h3>
              <HyperparameterTable data={config.data} model={config.model} />
            </div>
            <div className="bg-panel border border-border rounded-xl p-5 shadow-sm space-y-5">
              <div>
                <h3 className="text-sm font-bold text-text mb-3 uppercase tracking-wider">Ações</h3>
                <ResultActions runId={run.id} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-text mb-3 uppercase tracking-wider">Downloads</h3>
                <ArtifactDownloads runId={run.id} />
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="bg-panel border border-border p-8 rounded-xl text-center text-muted flex flex-col items-center gap-2">
          <Icons.Dashboard className="w-8 h-8 opacity-20" />
          <p>Métricas não disponíveis.</p>
          <p className="text-sm">O treinamento não foi concluído com sucesso ou os resultados foram apagados.</p>
        </div>
      )}
    </div>
  );
}
