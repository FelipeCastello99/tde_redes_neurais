"use client";

import { useFormContext } from "react-hook-form";
import { FieldWrapper } from "./SectionAccordion";

export function NumberField({ 
    name, label, tooltip, min, max, step = 1, placeholder 
}: { 
    name: string; label: string; tooltip?: string; min?: number; max?: number; step?: number | "any"; placeholder?: string 
}) {
    const { register, formState: { errors } } = useFormContext();
    const error = errors[name]?.message as string | undefined;

    return (
        <FieldWrapper label={label} tooltip={tooltip} error={error}>
            <input
                type="number"
                min={min}
                max={max}
                step={step}
                placeholder={placeholder}
                {...register(name, { valueAsNumber: true })}
                className="w-full px-3 py-2 bg-bg border border-border rounded-md text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-shadow"
            />
        </FieldWrapper>
    );
}

export function SelectField({ 
    name, label, tooltip, options 
}: { 
    name: string; label: string; tooltip?: string; options: { value: string, label: string }[] 
}) {
    const { register, formState: { errors } } = useFormContext();
    const error = errors[name]?.message as string | undefined;

    return (
        <FieldWrapper label={label} tooltip={tooltip} error={error}>
            <select
                {...register(name)}
                className="w-full px-3 py-2 bg-bg border border-border rounded-md text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary transition-shadow"
            >
                {options.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
            </select>
        </FieldWrapper>
    );
}

export function SwitchField({ 
    name, label, tooltip 
}: { 
    name: string; label: string; tooltip?: string; 
}) {
    const { register, watch, setValue } = useFormContext();
    const isChecked = watch(name);

    return (
        <div className="flex items-center justify-between py-2">
            <FieldWrapper label={label} tooltip={tooltip}>
                <span className="hidden"></span>
            </FieldWrapper>
            <button
                type="button"
                role="switch"
                aria-checked={isChecked}
                onClick={() => setValue(name, !isChecked, { shouldValidate: true, shouldDirty: true })}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-bg ${isChecked ? 'bg-primary' : 'bg-muted'}`}
            >
                <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${isChecked ? 'translate-x-4' : 'translate-x-0'}`} />
            </button>
            {/* Input oculto para o react-hook-form */}
            <input type="checkbox" {...register(name)} className="hidden" />
        </div>
    );
}
