"use client";

import { useFormContext } from "react-hook-form";
import { FieldWrapper } from "./SectionAccordion";

export function NeuronsEditor({ name, sourceField }: { name: string; sourceField: string }) {
    const { register, watch, setValue, formState: { errors } } = useFormContext();
    const hiddenLayers = watch(sourceField) as number;
    const currentNeurons = watch(name) as number[] || [];
    const error = errors[name]?.message as string | undefined;

    // Sincroniza o array de neurônios quando o número de camadas mudar
    if (currentNeurons.length !== hiddenLayers) {
        const newNeurons = [...currentNeurons];
        if (hiddenLayers > currentNeurons.length) {
            // Adiciona camadas (copiando a última ou usando 32)
            const last = currentNeurons.length > 0 ? currentNeurons[currentNeurons.length - 1] : 32;
            while (newNeurons.length < hiddenLayers) newNeurons.push(Math.max(8, Math.floor(last / 2)));
        } else {
            // Remove camadas
            newNeurons.splice(hiddenLayers);
        }
        // Timeout zero para evitar update no render
        setTimeout(() => setValue(name, newNeurons, { shouldValidate: true }), 0);
    }

    return (
        <FieldWrapper label="Neurônios por Camada" tooltip="Lista de neurônios, da primeira camada oculta até a última." error={error}>
            <div className="flex flex-wrap gap-2">
                {currentNeurons.map((val, idx) => (
                    <div key={idx} className="flex flex-col gap-1 w-24">
                        <span className="text-xs text-muted font-mono text-center">L{idx+1}</span>
                        <input
                            type="number"
                            min={1}
                            {...register(`${name}.${idx}`, { valueAsNumber: true })}
                            className="w-full px-2 py-1.5 bg-bg border border-border rounded-md text-sm text-center text-text font-mono focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                    </div>
                ))}
            </div>
        </FieldWrapper>
    );
}

const AVAILABLE_GROUPS = [
    { id: "localizacao", label: "Localização" },
    { id: "tempo", label: "Tempo" },
    { id: "via", label: "Via e Pista" },
    { id: "circunstancia", label: "Circunstância" },
    { id: "frota", label: "Frota" },
    { id: "regional", label: "Regional/Delegacia" },
];

export function MultiCheckbox({ name, label, tooltip }: { name: string; label: string; tooltip?: string }) {
    const { register, watch, setValue, formState: { errors } } = useFormContext();
    const selected = watch(name) as string[] || [];
    const error = errors[name]?.message as string | undefined;

    const toggle = (id: string) => {
        const next = selected.includes(id) ? selected.filter(x => x !== id) : [...selected, id];
        setValue(name, next, { shouldValidate: true, shouldDirty: true });
    };

    return (
        <FieldWrapper label={label} tooltip={tooltip} error={error}>
            <div className="grid grid-cols-2 gap-2 mt-2">
                {AVAILABLE_GROUPS.map(group => (
                    <label key={group.id} className="flex items-center gap-2 text-sm text-text cursor-pointer group">
                        <input 
                            type="checkbox" 
                            checked={selected.includes(group.id)}
                            onChange={() => toggle(group.id)}
                            className="w-4 h-4 rounded border-border text-primary focus:ring-primary bg-bg"
                        />
                        <span className="group-hover:text-primary transition-colors">{group.label}</span>
                    </label>
                ))}
            </div>
        </FieldWrapper>
    );
}
