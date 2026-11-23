"use client";

import { useEffect, useState } from "react";

import { Icons } from "@/components/icons";
import { deleteRun } from "@/lib/api";

export function DeleteRunButton({
  runId,
  runName,
  disabled = false,
  disabledReason,
  onDeleted,
}: {
  runId: string;
  runName: string;
  disabled?: boolean;
  disabledReason?: string;
  onDeleted?: (runId: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !isDeleting) {
        setIsOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isDeleting]);

  async function handleDelete() {
    setIsDeleting(true);
    setError(null);
    try {
      await deleteRun(runId);
      setIsOpen(false);
      onDeleted?.(runId);
    } catch (err: any) {
      setError(err?.message || "Não foi possível apagar o run.");
    } finally {
      setIsDeleting(false);
    }
  }

  function openDialog() {
    setError(null);
    setIsOpen(true);
  }

  return (
    <>
      <button
        type="button"
        onClick={openDialog}
        disabled={disabled}
        title={disabled ? disabledReason : "Apagar run"}
        aria-label={`Apagar ${runName}`}
        className="p-2 rounded-md text-muted hover:text-danger hover:bg-danger/10 disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-muted transition-colors"
      >
        <Icons.Trash className="w-4 h-4" />
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => {
              if (!isDeleting) setIsOpen(false);
            }}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={`delete-run-title-${runId}`}
            aria-describedby={`delete-run-description-${runId}`}
            className="relative w-full max-w-md bg-panel border border-border rounded-xl shadow-xl p-6"
          >
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-11 h-11 rounded-full bg-danger/10 text-danger flex items-center justify-center">
                <Icons.Trash className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h2
                  id={`delete-run-title-${runId}`}
                  className="text-lg font-bold text-text"
                >
                  Apagar run?
                </h2>
                <p className="text-sm font-medium text-text mt-1 break-words">
                  {runName}
                </p>
              </div>
            </div>

            <p
              id={`delete-run-description-${runId}`}
              className="text-sm text-muted mt-4"
            >
              O run será removido do banco de dados e os artefatos (pesos,
              métricas e gráficos) serão apagados do disco. Esta ação não pode
              ser desfeita.
            </p>

            {error && (
              <div className="mt-4 flex items-start gap-2 bg-danger/10 text-danger border border-danger/20 p-3 rounded-md text-sm">
                <Icons.Warning className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-6">
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                disabled={isDeleting}
                autoFocus
                className="px-4 py-2 rounded-md border border-border bg-panel hover:bg-panel-2 text-sm font-medium text-text transition-colors disabled:opacity-50"
              >
                Voltar
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 rounded-md bg-danger hover:bg-danger/90 text-white text-sm font-medium transition-colors disabled:opacity-50"
              >
                {isDeleting ? "Apagando..." : "Apagar definitivamente"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
