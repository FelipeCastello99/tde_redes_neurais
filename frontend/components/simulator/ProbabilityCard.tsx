"use client";

import { formatPercent } from "@/lib/format";
import { Icons } from "@/components/icons";
import { ContributionBars } from "./ContributionBars";

export function ProbabilityCard({ prediction }: { prediction: any }) {
  if (!prediction) {
    return (
      <div className="bg-panel border border-border p-8 rounded-xl shadow-sm text-center text-muted flex flex-col items-center gap-3">
        <Icons.Chart className="w-12 h-12 opacity-20" />
        <p>Preencha os dados do acidente ao lado e clique em Estimar para ver as probabilidades reais calculadas pela rede.</p>
      </div>
    );
  }

  const { predicted_class_index, predicted_class, probabilities, threshold_used } = prediction;
  const isBinary = threshold_used !== null;
  const classNames = Object.keys(probabilities);

  const getRiskLevel = (prob: number) => {
    if (prob < 0.05) return { label: 'Baixo Risco', color: 'text-success', bg: 'bg-success' };
    if (prob < 0.15) return { label: 'Risco Médio', color: 'text-warning', bg: 'bg-warning' };
    return { label: 'Alto Risco', color: 'text-danger', bg: 'bg-danger' };
  };

  return (
    <div className="bg-panel border border-border rounded-xl shadow-sm overflow-hidden animate-in fade-in zoom-in-95 duration-300">
      <div className="p-6 border-b border-border bg-panel-2/50 text-center">
        <p className="text-xs font-bold text-muted uppercase tracking-wider mb-2">Previsão do Modelo</p>
        <h2 className="text-3xl font-bold text-text mb-1">{predicted_class}</h2>
        {isBinary && (
          <p className="text-sm text-muted">Limiar de decisão utilizado: {threshold_used}</p>
        )}
      </div>

      <div className="p-6 space-y-6">
        {isBinary ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-48 h-48 relative">
              {/* Gauge Simples (Half Donut CSS Trick) */}
              <div className="w-full h-full rounded-full border-[16px] border-panel-2 relative overflow-hidden">
                <div 
                  className={`absolute top-0 left-0 w-full h-full rounded-full border-[16px] border-transparent transition-transform duration-1000 ease-out origin-center`}
                  style={{ 
                    borderColor: 'currentColor',
                    color: `var(--${getRiskLevel(probabilities['vitima_fatal']).bg.split('-')[1]})`,
                    clipPath: 'polygon(0 50%, 100% 50%, 100% 100%, 0 100%)',
                    transform: `rotate(${probabilities['vitima_fatal'] * 180}deg)`
                  }}
                />
              </div>
              <div className="absolute inset-0 flex flex-col items-center justify-center pt-8">
                <span className="text-4xl font-bold font-mono tracking-tighter text-text">
                  {formatPercent(probabilities['vitima_fatal'], 1)}
                </span>
                <span className="text-xs text-muted uppercase font-semibold mt-1">Vítima Fatal</span>
              </div>
            </div>
            <p className={`font-medium ${getRiskLevel(probabilities['vitima_fatal']).color}`}>
              {getRiskLevel(probabilities['vitima_fatal']).label}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {classNames.map((name, i) => {
              const prob = probabilities[name];
              const isMax = i === predicted_class_index;
              return (
                <div key={name} className="space-y-1.5">
                  <div className="flex justify-between text-sm">
                    <span className={isMax ? "font-bold text-text" : "text-muted"}>{name}</span>
                    <span className="font-mono font-medium">{formatPercent(prob)}</span>
                  </div>
                  <div className="h-2.5 w-full bg-panel-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-1000 ease-out ${
                        i === 0 ? 'bg-success' : i === 1 ? 'bg-warning' : 'bg-danger'
                      }`}
                      style={{ width: `${prob * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="bg-warning/10 border border-warning/20 rounded-md p-3 text-xs text-warning flex gap-2 items-start mt-6">
          <Icons.Warning className="w-4 h-4 shrink-0 mt-0.5" />
          <p><strong>Aviso:</strong> Este simulador é um protótipo acadêmico. A base de dados (DATATRAN) não contém velocidade no impacto ou uso do cinto de segurança, fatores determinantes para a letalidade. O modelo estima probabilidades estatísticas globais, não desfechos físicos garantidos.</p>
        </div>

        <div className="border-t border-border pt-4 space-y-2">
          <h3 className="text-xs font-bold text-muted uppercase tracking-wider">Contribuição dos Campos</h3>
          <ContributionBars contributions={prediction.contributions} />
        </div>
      </div>
    </div>
  );
}
