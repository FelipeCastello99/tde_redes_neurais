import { useEffect, useState } from 'react';
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

type RawEvent = Partial<StreamEvent> & {
  type?: string;
  status?: string;
  error?: string;
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
        const data: RawEvent = JSON.parse(event.data);

        if (data.type === 'status') {
          setStatus(data.status === 'running' ? 'connected' : 'connecting');
          return;
        }

        if (data.type === 'done') {
          setStatus('done');
          es.close();
          return;
        }

        if (data.type === 'failed' || data.type === 'canceled') {
          setStatus('error');
          setError(data.error || `Treinamento ${data.status || data.type}.`);
          es.close();
          return;
        }

        // Eventos de época incluem epoch numérico. Ignora mensagens auxiliares.
        if (typeof data.epoch !== 'number') return;

        const epochEvent = data as StreamEvent;
        setEvents((prev) => {
          if (prev.length > 0 && prev[prev.length - 1].epoch === epochEvent.epoch) {
            return prev;
          }
          return [...prev, epochEvent];
        });
      } catch (err) {
        console.error('Erro ao interpretar evento SSE', err);
      }
    };

    es.onerror = async () => {
      try {
        const runData = await getRun(runId);
        if (runData.status === 'done') {
          setStatus('done');
          es.close();
          return;
        }
        if (runData.status === 'failed' || runData.status === 'canceled') {
          setStatus('error');
          setError(runData.error || `Run terminou com status: ${runData.status}`);
          es.close();
          return;
        }
      } catch {
        // mantém a tentativa de reconexão do EventSource
      }

      if (es.readyState === EventSource.CLOSED) {
        setStatus('error');
        setError('Conexão perdida com o servidor de stream.');
      }
    };

    return () => {
      es.close();
    };
  }, [runId]);

  return { status, events, error };
}
