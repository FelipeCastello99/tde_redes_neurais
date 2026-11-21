"use client";

import { useMemo } from "react";
import { formatNumber, formatPercent } from "@/lib/format";

export function MetricsGridDetailed({ per_class, macro, weighted, classNames }: { per_class: any[], macro: any, weighted: any, classNames: string[] }) {
  if (!per_class) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-muted uppercase bg-panel-2 border-b border-border">
          <tr>
            <th className="px-4 py-3 font-medium rounded-tl-lg">Classe</th>
            <th className="px-4 py-3 font-medium">Precisão</th>
            <th className="px-4 py-3 font-medium">Recall</th>
            <th className="px-4 py-3 font-medium">F1-Score</th>
            <th className="px-4 py-3 font-medium text-right rounded-tr-lg">Suporte</th>
          </tr>
        </thead>
        <tbody>
          {per_class.map((c, i) => (
            <tr key={i} className="border-b border-border bg-panel hover:bg-panel-2/50 transition-colors">
              <td className="px-4 py-3 font-medium text-text">{classNames[i]}</td>
              <td className="px-4 py-3">{formatPercent(c.precision)}</td>
              <td className="px-4 py-3">{formatPercent(c.recall)}</td>
              <td className="px-4 py-3 font-bold text-primary">{formatPercent(c.f1)}</td>
              <td className="px-4 py-3 text-right font-mono text-muted">{c.support}</td>
            </tr>
          ))}
          <tr className="bg-panel-2/30 border-b border-border">
            <td className="px-4 py-3 font-medium text-text">Média Macro</td>
            <td className="px-4 py-3">{formatPercent(macro.precision)}</td>
            <td className="px-4 py-3">{formatPercent(macro.recall)}</td>
            <td className="px-4 py-3 font-bold">{formatPercent(macro.f1)}</td>
            <td className="px-4 py-3 text-right text-muted">-</td>
          </tr>
          <tr className="bg-panel-2/30">
            <td className="px-4 py-3 font-medium text-text rounded-bl-lg">Média Ponderada</td>
            <td className="px-4 py-3">{formatPercent(weighted.precision)}</td>
            <td className="px-4 py-3">{formatPercent(weighted.recall)}</td>
            <td className="px-4 py-3 font-bold">{formatPercent(weighted.f1)}</td>
            <td className="px-4 py-3 text-right text-muted rounded-br-lg">-</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export function HyperparameterTable({ data, model }: { data: any, model: any }) {
  const allParams = [
    { cat: 'Dados', key: 'Alvo', val: data.target },
    { cat: 'Dados', key: 'Amostras Max', val: data.max_rows || 'Todas' },
    { cat: 'Dados', key: 'Split (T/V/T)', val: `${1 - data.val_size - data.test_size}/${data.val_size}/${data.test_size}` },
    { cat: 'Dados', key: 'Pesos', val: data.class_weight },
    { cat: 'Pré-processamento', key: 'Scaler', val: data.scaler },
    { cat: 'Arquitetura', key: 'Camadas Ocultas', val: model.hidden_layers },
    { cat: 'Arquitetura', key: 'Neurônios', val: JSON.stringify(model.neurons) },
    { cat: 'Arquitetura', key: 'Ativação', val: model.activation },
    { cat: 'Arquitetura', key: 'Inicialização', val: model.init },
    { cat: 'Regulari.', key: 'Dropout', val: model.dropout },
    { cat: 'Regulari.', key: 'L2', val: model.l2 },
    { cat: 'Otimização', key: 'Algoritmo', val: model.optimizer },
    { cat: 'Otimização', key: 'LR Inicial', val: model.lr },
    { cat: 'Otimização', key: 'Decay', val: model.lr_decay },
    { cat: 'Otimização', key: 'Batch Size', val: model.batch_size || 'Full Batch' },
    { cat: 'Otimização', key: 'Patience (ES)', val: model.patience },
    { cat: 'Loss', key: 'Função', val: model.loss },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {allParams.map((p, i) => (
        <div key={i} className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider text-muted font-semibold">{p.key}</span>
          <span className="text-sm font-medium text-text mt-0.5 truncate" title={String(p.val)}>{p.val}</span>
        </div>
      ))}
    </div>
  );
}
