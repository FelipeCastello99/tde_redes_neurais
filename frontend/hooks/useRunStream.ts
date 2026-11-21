import { useState, useEffect } from 'react';
import { getRun } from '../lib/api';

export type StreamEvent = {
  epoch: number;
  epochs: number;
  loss_train: number;
  loss_val: number;
  acc_train: number;
  acc_val: number;
  f1_val: number;
  grad_norm: number;
  lr: number;
  seconds: number;
  best_epoch: number;
};

export function useRunStream(runId: string | null) {
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'done' | 'error'>('idle');
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) {
      setStatus('idle');
      setEvents([]);
      setError(null);
      return;
    }

    setStatus('connecting');
    setEvents([]);
    setError(null);

    const es = new EventSource(`/api/runs/${runId}/stream`);
    
    es.onopen = () => {
      setStatus('connected');
    };

    es.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data);
        setEvents(prev => {
          // Prevenção contra eventos duplicados
          if (prev.length > 0 && prev[prev.length - 1].epoch === data.epoch) {
            return prev;
          }
          return [...prev, data];
        });

        if (data.epoch >= data.epochs) {
          setStatus('done');
          es.close();
        }
      } catch (err) {
        console.error("Erro ao fazer parse da mensagem SSE", err);
      }
    };

    es.onerror = async () => {
      // Verifica na API REST se o run já falhou ou concluiu para decidir entre fallback ou erro definitivo
      try {
        const runData = await getRun(runId);
        if (runData.status === 'done') {
            setStatus('done');
            es.close();
            return;
        } else if (runData.status === 'failed' || runData.status === 'canceled') {
            setStatus('error');
            setError(runData.error || `Run terminou com status: ${runData.status}`);
            es.close();
            return;
        }
      } catch {
         // ignore
      }
      
      // Tentativa de reconexão transparente
      if (es.readyState === EventSource.CLOSED) {
         setStatus('error');
         setError("Conexão perdida com o servidor de stream.");
      }
    };

    return () => {
      es.close();
    };
  }, [runId]);

  return { status, events, error };
}
