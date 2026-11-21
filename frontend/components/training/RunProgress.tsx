"use client";

import { useRunStream } from "@/hooks/useRunStream";
import { LiveLossChart, MetricChart } from "./Charts";
import { LogConsole } from "./LogConsole";
import { CancelButton } from "./CancelButton";
import { Icons } from "@/components/icons";
import Link from "next/link";
import { formatTime } from "@/lib/format";

export function RunProgress({ runId }: { runId: string }) {
  const { status, events, error } = useRunStream(runId);

  const isFinished = status === 'done' || status === 'error';
  const lastEvent = events.length > 0 ? events[events.length - 1] : null;
  
  const pct = lastEvent ? Math.min(100, Math.round((lastEvent.epoch / lastEvent.epochs) * 100)) : 0;

  return (
    <div className="flex flex-col h-full space-y-6 animate-in fade-in duration-500">
      
      {/* Header com Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-full bg-panel-2 border border-border">
            {!isFinished && <div className="absolute inset-0 border-2 border-primary rounded-full animate-ping opacity-20" />}
            <Icons.System className={`w-5 h-5 ${!isFinished ? 'text-primary animate-pulse' : 'text-muted'}`} />
          </div>
          <div>
            <h3 className="font-semibold text-text">
              {status === 'connecting' ? 'Iniciando pipeline...' : 
               status === 'connected' ? 'Treinamento em andamento' : 
               status === 'done' ? 'Treinamento Concluído' : 'Erro/Cancelado'}
            </h3>
            <p className="text-xs text-muted">
              {lastEvent ? `Época ${lastEvent.epoch} de ${lastEvent.epochs}` : 'Aguardando primeira época...'}
            </p>
          </div>
        </div>

        {!isFinished && <CancelButton runId={runId} />}
        {isFinished && (
          <Link href={`/resultados/${runId}`} className="px-4 py-2 bg-primary hover:bg-primary/90 text-white text-sm font-medium rounded shadow transition-colors">
            Ver Resultados Completos
          </Link>
        )}
      </div>

      {error && (
        <div className="bg-danger/10 text-danger border border-danger/20 p-3 rounded text-sm flex gap-2">
          <Icons.Warning className="w-4 h-4 shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs font-medium text-muted">
          <span>{pct}% concluído</span>
          {lastEvent && <span>Decorridos: {formatTime(lastEvent.seconds)}</span>}
        </div>
        <div className="w-full h-2 bg-panel-2 rounded-full overflow-hidden">
          <div 
            className={`h-full bg-primary transition-all duration-500 ease-out ${isFinished && status !== 'error' ? 'bg-success' : ''}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Gráficos em Grid */}
      <div className="grid grid-cols-1 gap-4 flex-1">
        <div className="bg-panel border border-border rounded-lg p-4 space-y-2 shadow-sm">
          <h4 className="text-xs font-semibold text-muted uppercase tracking-wider">Curvas de Loss (Cross-Entropy)</h4>
          <LiveLossChart data={events} bestEpoch={lastEvent?.best_epoch || 0} />
        </div>
        
        <div className="bg-panel border border-border rounded-lg p-4 space-y-2 shadow-sm">
          <h4 className="text-xs font-semibold text-muted uppercase tracking-wider">Acurácia & F1 Score</h4>
          <MetricChart data={events} />
        </div>
      </div>

      {/* Console */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-muted uppercase tracking-wider">Console de Épocas</h4>
        <LogConsole events={events} />
      </div>

    </div>
  );
}
