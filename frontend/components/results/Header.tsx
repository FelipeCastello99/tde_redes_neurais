"use client";

import { formatNumber, formatPercent, formatTime, formatDate } from "@/lib/format";
import { Icons } from "@/components/icons";

export function RunHeader({ run }: { run: any }) {
  if (!run) return null;

  return (
    <div className="bg-panel border border-border rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-text">{run.name}</h1>
          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
            run.status === 'done' ? 'bg-success/10 text-success' : 
            run.status === 'failed' ? 'bg-danger/10 text-danger' : 
            run.status === 'canceled' ? 'bg-warning/10 text-warning' : 
            'bg-primary/10 text-primary'
          }`}>
            {run.status.toUpperCase()}
          </span>
        </div>
        <p className="text-sm text-muted mt-1 flex items-center gap-4">
          <span className="flex items-center gap-1.5"><Icons.System className="w-3.5 h-3.5"/> {run.target}</span>
          <span>{formatDate(run.created_at)}</span>
        </p>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-right">
          <p className="text-xs text-muted font-medium uppercase tracking-wider">Amostras Treino</p>
          <p className="text-lg font-bold text-text">{run.n_train ? formatNumber(run.n_train, 0) : '-'}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted font-medium uppercase tracking-wider">Duração</p>
          <p className="text-lg font-bold text-text">{run.duration_s ? formatTime(run.duration_s) : '-'}</p>
        </div>
      </div>
    </div>
  );
}

export function MetricsGrid({ metrics, classNames, target }: { metrics: any, classNames: string[], target: string }) {
  if (!metrics) return null;

  const isBinary = classNames.length === 2;
  const isTargetFatal = target === 'fatal_binario';
  
  // No caso binário (fatal_binario), o índice de interesse é 1 (vitima_fatal)
  const classOfInterestIdx = isTargetFatal ? 1 : null;
  const classOfInterestStats = classOfInterestIdx !== null ? metrics.precision_recall_f1.per_class[classOfInterestIdx] : null;

  // Calculo de Baseline Majoritário (simplificado)
  // No backend a contagem de amostras está no store, aqui assumimos as métricas.
  // baseline de accuracy na classe majoritária.
  
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-panel border border-border rounded-xl p-4 shadow-sm group relative">
        <div className="text-xs text-muted font-medium uppercase tracking-wider flex items-center gap-1.5">
          Acurácia <Icons.Warning className="w-3 h-3 cursor-help text-muted/50 hover:text-text" />
          <div className="hidden group-hover:block absolute bottom-full mb-2 bg-panel-2 border border-border p-2 rounded text-xs text-text z-10 min-w-[200px] shadow-lg">
            Proporção de acertos globais. Cuidado: em datasets desbalanceados (como este), um modelo que sempre prevê a classe majoritária já teria acurácia muito alta.
          </div>
        </div>
        <p className="text-2xl font-bold text-text mt-1">{formatPercent(metrics.accuracy)}</p>
      </div>

      <div className="bg-panel border border-border rounded-xl p-4 shadow-sm group relative">
        <div className="text-xs text-muted font-medium uppercase tracking-wider flex items-center gap-1.5">
          F1 Score (Macro) <Icons.Warning className="w-3 h-3 cursor-help text-muted/50 hover:text-text" />
          <div className="hidden group-hover:block absolute bottom-full mb-2 bg-panel-2 border border-border p-2 rounded text-xs text-text z-10 min-w-[200px] shadow-lg">
            Média não ponderada do F1 Score de todas as classes. Essencial para avaliar se a classe minoritária foi bem aprendida.
          </div>
        </div>
        <p className="text-2xl font-bold text-text mt-1">{formatPercent(metrics.precision_recall_f1.macro.f1)}</p>
      </div>

      <div className="bg-panel border border-border rounded-xl p-4 shadow-sm group relative">
        <div className="text-xs text-muted font-medium uppercase tracking-wider flex items-center gap-1.5">
          {isBinary ? 'F1 Score (Fatal)' : 'ROC-AUC'} <Icons.Warning className="w-3 h-3 cursor-help text-muted/50 hover:text-text" />
          <div className="hidden group-hover:block absolute bottom-full mb-2 bg-panel-2 border border-border p-2 rounded text-xs text-text z-10 min-w-[200px] shadow-lg">
            {isBinary ? 'F1 apenas da classe vitima_fatal. O F1 combina precisão (dos que previ fatais, quantos eram) e recall (dos que eram fatais, quantos achei).' : 'Área sob a curva ROC (Macro). Quão bem o modelo separa as classes globalmente.'}
          </div>
        </div>
        <p className="text-2xl font-bold text-text mt-1 text-primary">
          {formatPercent(isBinary && classOfInterestStats ? classOfInterestStats.f1 : metrics.roc_auc)}
        </p>
      </div>

      <div className="bg-panel border border-border rounded-xl p-4 shadow-sm group relative">
        <div className="text-xs text-muted font-medium uppercase tracking-wider flex items-center gap-1.5">
          Log Loss <Icons.Warning className="w-3 h-3 cursor-help text-muted/50 hover:text-text" />
          <div className="hidden group-hover:block absolute bottom-full mb-2 bg-panel-2 border border-border p-2 rounded text-xs text-text z-10 min-w-[200px] shadow-lg">
            Entropia Cruzada no conjunto de teste. Valores menores indicam que as probabilidades previstas estão próximas da verdade.
          </div>
        </div>
        <p className="text-2xl font-bold text-text mt-1">{formatNumber(metrics.log_loss, 3)}</p>
      </div>
    </div>
  );
}
