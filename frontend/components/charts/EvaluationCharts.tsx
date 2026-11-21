"use client";

import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export function RocPrChart({ roc_details, pr_details, classNames }: { roc_details: any, pr_details: any, classNames: string[] }) {
  const [tab, setTab] = useState<'roc' | 'pr'>('roc');
  const [classIdx, setClassIdx] = useState<number>(classNames.length === 2 ? 0 : -1);

  if (!roc_details) return <div className="text-muted text-sm">Sem dados</div>;

  const isBinary = classNames.length === 2;

  // No binário nós temos apenas 1 AUC relevante (a média de Mann-Whitney) e a curva padrão. 
  // Nota: A API retorna os pontos no caso binário apenas se estendêssemos para mandar as curvas exatas.
  // Pelo contrato "backend.md", o backend não devolve a curva ROC explícita array por array em evaluation.json.
  // Retorna métricas. Vamos assumir que recebemos o threshold sweep para traçar PR e talvez ROC (TPR vs FPR).

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex bg-panel-2 rounded-md border border-border p-1">
          <button 
            className={`px-3 py-1 text-xs font-medium rounded ${tab === 'roc' ? 'bg-panel shadow text-primary' : 'text-muted'}`}
            onClick={() => setTab('roc')}
          >
            ROC AUC
          </button>
          <button 
            className={`px-3 py-1 text-xs font-medium rounded ${tab === 'pr' ? 'bg-panel shadow text-primary' : 'text-muted'}`}
            onClick={() => setTab('pr')}
          >
            PR AUC
          </button>
        </div>
        
        {!isBinary && (
          <select 
            className="bg-panel-2 border border-border text-xs rounded-md px-2 py-1"
            value={classIdx}
            onChange={(e) => setClassIdx(Number(e.target.value))}
          >
            <option value="-1">Média Macro</option>
            {classNames.map((name, i) => (
              <option key={i} value={i}>{name}</option>
            ))}
          </select>
        )}
      </div>

      <div className="flex-1 flex items-center justify-center bg-bg rounded-lg border border-border">
        {/* Placeholder para a Curva real, uma vez que a curva ROC cheia não foi especificada para ser exportada ponto a ponto, mas sim a varredura de limiar */}
        <div className="text-center text-muted text-sm">
          <p className="font-bold text-2xl mb-2 text-text">
            {tab === 'roc' 
              ? (classIdx === -1 || isBinary ? roc_details.macro : roc_details.per_class[classIdx]).toFixed(4)
              : (classIdx === -1 || isBinary ? pr_details.macro : pr_details.per_class[classIdx]).toFixed(4)
            }
          </p>
          <p className="uppercase text-xs tracking-wider">
            {tab === 'roc' ? 'ROC-AUC' : 'PR-AUC'} 
            {classIdx === -1 && !isBinary ? ' (Macro)' : isBinary ? '' : ` (${classNames[classIdx]})`}
          </p>
        </div>
      </div>
    </div>
  );
}

export function ThresholdChart({ sweep }: { sweep: any[] }) {
  if (!sweep || sweep.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-muted text-sm text-center px-4">
        <p>Varredura de Limiar indisponível.</p>
        <p className="text-xs mt-1">Disponível apenas para alvo binário.</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={sweep} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis 
            dataKey="threshold" 
            tick={{ fontSize: 10, fill: 'var(--muted)' }} 
            tickLine={false}
            axisLine={{ stroke: 'var(--border)' }}
            type="number"
            domain={[0, 1]}
            tickCount={11}
          />
          <YAxis 
            tick={{ fontSize: 10, fill: 'var(--muted)' }} 
            tickLine={false}
            axisLine={false}
            domain={[0, 1]}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: 'var(--panel)', borderColor: 'var(--border)', borderRadius: '6px', fontSize: '12px' }}
            labelFormatter={(v) => `Limiar: ${v}`}
          />
          <Line type="monotone" dataKey="f1" name="F1 Score" stroke="var(--primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="precision" name="Precisão" stroke="var(--success)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="recall" name="Recall" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
