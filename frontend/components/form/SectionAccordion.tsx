import { useState } from "react";
import { Icons } from "@/components/icons";

export function SectionAccordion({ 
  title, 
  number, 
  summary, 
  children, 
  defaultOpen = false 
}: { 
  title: string; 
  number: number; 
  summary?: string; 
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-border rounded-lg bg-panel overflow-hidden mb-4 shadow-sm">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 bg-panel hover:bg-panel-2 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-sm font-bold">
            {number}
          </span>
          <div>
            <h3 className="font-semibold text-text">{title}</h3>
            {summary && !isOpen && (
              <p className="text-xs text-muted mt-0.5 truncate max-w-md">{summary}</p>
            )}
          </div>
        </div>
        <Icons.Play className={`w-3 h-3 text-muted transition-transform duration-200 ${isOpen ? "rotate-90" : "rotate-0"}`} />
      </button>
      
      {isOpen && (
        <div className="p-4 pt-2 border-t border-border animate-in slide-in-from-top-2 duration-200">
          {children}
        </div>
      )}
    </div>
  );
}

// Field wrapper genérico com tooltip
export function FieldWrapper({ 
    label, tooltip, error, children 
}: { 
    label: string; tooltip?: string; error?: string; children: React.ReactNode 
}) {
    return (
        <div className="space-y-1.5">
            <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-text flex items-center gap-1.5">
                    {label}
                    {tooltip && (
                        <div className="group relative inline-flex items-center justify-center">
                            <Icons.Warning className="w-3.5 h-3.5 text-muted cursor-help" />
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2 bg-panel border border-border rounded shadow-lg text-xs text-muted z-10 text-center">
                                {tooltip}
                            </div>
                        </div>
                    )}
                </label>
            </div>
            {children}
            {error && <p className="text-xs text-danger font-medium">{error}</p>}
        </div>
    );
}
