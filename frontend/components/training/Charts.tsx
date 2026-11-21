"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { StreamEvent } from "@/hooks/useRunStream";

export function LiveLossChart({ data, bestEpoch }: { data: StreamEvent[], bestEpoch: number }) {
  if (!data || data.length === 0) {
    return <div className="h-48 w-full flex items-center justify-center text-muted text-sm bg-bg rounded border border-border">Aguardando dados...</div>;
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis 
            dataKey="epoch" 
            tick={{ fontSize: 10, fill: 'var(--muted)' }} 
            tickLine={false}
            axisLine={{ stroke: 'var(--border)' }}
          />
          <YAxis 
            tick={{ fontSize: 10, fill: 'var(--muted)' }} 
            tickLine={false}
            axisLine={false}
            domain={['auto', 'auto']}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: 'var(--panel)', borderColor: 'var(--border)', borderRadius: '6px', fontSize: '12px' }}
            itemStyle={{ fontSize: '12px' }}
          />
          {bestEpoch > 0 && (
            <ReferenceLine x={bestEpoch} stroke="var(--success)" strokeDasharray="3 3" label={{ position: 'top', value: 'Melhor', fill: 'var(--success)', fontSize: 10 }} />
          )}
          <Line 
            type="monotone" 
            dataKey="loss_train" 
            name="Treino" 
            stroke="var(--primary)" 
            strokeWidth={2} 
            dot={false}
            isAnimationActive={false} 
          />
          <Line 
            type="monotone" 
            dataKey="loss_val" 
            name="Validação" 
            stroke="var(--accent)" 
            strokeWidth={2} 
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MetricChart({ data }: { data: StreamEvent[] }) {
  if (!data || data.length === 0) {
    return <div className="h-48 w-full flex items-center justify-center text-muted text-sm bg-bg rounded border border-border">Aguardando dados...</div>;
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis 
            dataKey="epoch" 
            tick={{ fontSize: 10, fill: 'var(--muted)' }} 
            tickLine={false}
            axisLine={{ stroke: 'var(--border)' }}
          />
          <YAxis 
            tick={{ fontSize: 10, fill: 'var(--muted)' }} 
            tickLine={false}
            axisLine={false}
            domain={[0, 1]}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: 'var(--panel)', borderColor: 'var(--border)', borderRadius: '6px', fontSize: '12px' }}
          />
          <Line 
            type="monotone" 
            dataKey="acc_val" 
            name="Acurácia (Val)" 
            stroke="#10b981" 
            strokeWidth={2} 
            dot={false}
            isAnimationActive={false} 
          />
          <Line 
            type="monotone" 
            dataKey="f1_val" 
            name="F1 (Val)" 
            stroke="#f59e0b" 
            strokeWidth={2} 
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
