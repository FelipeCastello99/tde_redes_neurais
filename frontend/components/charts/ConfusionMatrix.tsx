"use client";

import { formatPercent } from "@/lib/format";

export function ConfusionMatrix({ matrix, classNames }: { matrix: number[][], classNames: string[] }) {
  if (!matrix || matrix.length === 0) return <div className="text-muted text-sm">Sem dados</div>;

  const total = matrix.flat().reduce((a, b) => a + b, 0);
  const K = classNames.length;

  const maxValue = Math.max(...matrix.flat());

  // Para gerar as cores (azul no fundo, texto contrastante)
  const getCellColor = (value: number) => {
    const intensity = value / (maxValue || 1);
    // Cores usando os tokens de Tailwind + opacidade
    return `rgba(8, 145, 178, ${0.1 + intensity * 0.9})`; // primary-ish
  };

  const getTextColor = (value: number) => {
    const intensity = value / (maxValue || 1);
    return intensity > 0.5 ? '#ffffff' : 'var(--text)';
  };

  return (
    <div className="flex flex-col h-full w-full relative pt-6 pl-6">
      <div className="absolute top-0 left-0 right-0 text-center text-xs font-semibold text-muted uppercase tracking-wider">Previsto</div>
      <div className="absolute top-0 bottom-0 left-0 w-6 flex items-center justify-center -rotate-90 origin-center text-xs font-semibold text-muted uppercase tracking-wider">Real</div>
      
      <div className="flex-1 grid gap-1" style={{ gridTemplateColumns: `auto repeat(${K}, minmax(0, 1fr))` }}>
        {/* Header Cols (Previsto) */}
        <div></div>
        {classNames.map((name, i) => (
          <div key={`header-col-${i}`} className="flex items-end justify-center pb-2 px-1 text-center">
            <span className="text-xs text-muted leading-tight truncate max-w-[80px]" title={name}>{name}</span>
          </div>
        ))}
        
        {/* Rows */}
        {matrix.map((row, i) => (
          <div key={`row-${i}`} className="contents">
            <div className="flex items-center justify-end pr-2 text-right">
              <span className="text-xs text-muted leading-tight truncate max-w-[80px]" title={classNames[i]}>{classNames[i]}</span>
            </div>
            {row.map((val, j) => {
              const isDiagonal = i === j;
              return (
                <div 
                  key={`cell-${i}-${j}`} 
                  className={`flex flex-col items-center justify-center rounded-md p-2 border transition-all hover:scale-[1.02] ${isDiagonal ? 'border-primary/50' : 'border-transparent'}`}
                  style={{ backgroundColor: getCellColor(val), color: getTextColor(val) }}
                  title={`Real: ${classNames[i]}\nPrevisto: ${classNames[j]}\nQtde: ${val} (${formatPercent(val/total)})`}
                >
                  <span className="text-lg font-bold font-mono">{val}</span>
                  <span className="text-[10px] opacity-80">{formatPercent(val/total)}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
