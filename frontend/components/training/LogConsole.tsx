import { useEffect, useRef } from "react";
import { StreamEvent } from "@/hooks/useRunStream";

export function LogConsole({ events }: { events: StreamEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  if (!events || events.length === 0) {
    return <div className="h-32 bg-bg border border-border rounded font-mono text-xs p-3 text-muted">Aguardando logs...</div>;
  }

  // Pega apenas as últimas 100 linhas para não pesar
  const displayEvents = events.slice(-100);

  return (
    <div 
        ref={scrollRef}
        className="h-32 bg-[#0b0f14] border border-border rounded font-mono text-xs p-3 overflow-y-auto"
    >
      {displayEvents.map((ev) => (
        <div key={ev.epoch} className="text-gray-300 py-0.5 border-b border-gray-800/50 hover:bg-gray-800/30 flex gap-4">
          <span className="text-gray-500 w-16 shrink-0">Ep {ev.epoch.toString().padStart(3, '0')}</span>
          <span className="text-blue-400 w-24 shrink-0">loss: {ev.loss_train.toFixed(4)}</span>
          <span className="text-pink-400 w-24 shrink-0">val: {ev.loss_val.toFixed(4)}</span>
          <span className="text-emerald-400 w-24 shrink-0">f1: {ev.f1_val.toFixed(4)}</span>
          <span className="text-amber-400 hidden sm:inline">lr: {ev.lr.toExponential(2)}</span>
        </div>
      ))}
    </div>
  );
}
