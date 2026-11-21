"use client";

import { useState } from "react";
import { Icons } from "@/components/icons";
import { cancelRun } from "@/lib/api";

export function CancelButton({ runId, onCanceled }: { runId: string, onCanceled?: () => void }) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isCanceling, setIsCanceling] = useState(false);

  const handleCancel = async () => {
    setIsCanceling(true);
    try {
      await cancelRun(runId);
      if (onCanceled) onCanceled();
    } catch (e) {
      console.error("Falha ao cancelar", e);
    } finally {
      setIsCanceling(false);
      setIsConfirming(false);
    }
  };

  if (isConfirming) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted">Tem certeza?</span>
        <button 
          onClick={handleCancel}
          disabled={isCanceling}
          className="px-3 py-1 bg-danger hover:bg-danger/90 text-white text-xs rounded transition-colors disabled:opacity-50"
        >
          {isCanceling ? "Cancelando..." : "Sim, cancelar"}
        </button>
        <button 
          onClick={() => setIsConfirming(false)}
          disabled={isCanceling}
          className="px-3 py-1 bg-panel hover:bg-panel-2 border border-border text-xs rounded transition-colors"
        >
          Voltar
        </button>
      </div>
    );
  }

  return (
    <button 
      onClick={() => setIsConfirming(true)}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-danger hover:bg-danger/10 rounded transition-colors"
    >
      <Icons.Stop className="w-3 h-3" />
      Interromper
    </button>
  );
}
