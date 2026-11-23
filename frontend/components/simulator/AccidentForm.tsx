"use client";

import { useForm, FormProvider } from "react-hook-form";
import { FieldWrapper } from "@/components/form/SectionAccordion";
import { SelectField, NumberField } from "@/components/form/Fields";
import { Icons } from "@/components/icons";

export function AccidentForm({ 
  meta, 
  runs, 
  onSimulate, 
  isPredicting,
  initialRunId,
}: { 
  meta: any; 
  runs: any[]; 
  onSimulate: (runId: string, features: any) => void;
  isPredicting: boolean;
  initialRunId?: string | null;
}) {
  const defaultRun = initialRunId && runs.some((run) => run.id === initialRunId)
    ? initialRunId
    : runs.length > 0 ? runs[0].id : "";

  const methods = useForm<any>({
    defaultValues: {
      runId: defaultRun,
      features: {}
    }
  });

  const { handleSubmit, watch, reset } = methods;
  const watchRunId = watch("runId");
  const selectedRun = runs.find(r => r.id === watchRunId);

  // Filtra apenas os grupos de features que o modelo (run) selecionado utilizou
  // Se não tem run selecionado, mostra tudo.
  const activeGroups = selectedRun ? selectedRun.config.data.feature_groups : meta.feature_groups;

  // Organiza os campos meta pelos grupos para montar a UI
  // No caso real, a API/meta deve dizer a qual grupo cada variável pertence. 
  // Por simplicidade, faremos um fallback com base no conhecimento do domínio.
  const groupMapping: Record<string, string[]> = {
    localizacao: ['uf', 'br', 'km'],
    tempo: ['dia_semana', 'horario'],
    via: ['tipo_pista', 'tracado_via', 'uso_solo', 'sentido_via'],
    circunstancia: ['causa_acidente', 'tipo_acidente', 'fase_dia', 'condicao_metereologica'],
    frota: ['veiculos'],
    regional: ['regional', 'delegacia', 'uop']
  };

  const labelOverrides: Record<string, string> = {
    tracado_via: 'TRACADO DA VIA (1º TERMO)',
    veiculos: 'QUANTIDADE DE VEÍCULOS',
  };

  // A API expõe tracado_principal; o formulário envia tracado_via porque
  // feature_frame aplica a mesma redução (primeiro termo antes de ';').
  const categoryKey = (field: string) => (field === 'tracado_via' ? 'tracado_principal' : field);

  // Fallback para APIs antigas que ainda não expõem tracado_principal.
  const TRACADO_FALLBACK = [
    'Reta', 'Curva', 'Declive', 'Aclive', 'Interseção de Vias', 'Rotatória',
    'Retorno Regulamentado', 'Em Obras', 'Viaduto', 'Ponte', 'Desvio Temporário', 'Túnel',
  ];

  const onSubmit = (data: any) => {
    onSimulate(data.runId, data.features);
  };

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        
        <div className="bg-panel border border-border p-4 rounded-xl shadow-sm">
          <FieldWrapper label="Modelo de Inferência">
            <select 
              {...methods.register("runId")}
              className="w-full px-3 py-2 bg-bg border border-border rounded-md text-sm font-medium focus:ring-2 focus:ring-primary outline-none"
            >
              <option value="" disabled>Selecione um modelo treinado...</option>
              {runs.map(r => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.target === 'fatal_binario' ? 'Binário' : '3 Classes'})
                </option>
              ))}
            </select>
          </FieldWrapper>
          {!selectedRun && (
            <p className="text-xs text-warning mt-2 flex items-center gap-1">
              <Icons.Warning className="w-3 h-3" /> É necessário treinar um modelo primeiro.
            </p>
          )}
        </div>

        {activeGroups.map((group: string) => {
          const fields = groupMapping[group] || [];
          if (fields.length === 0) return null;
          
          return (
            <div key={group} className="bg-panel border border-border p-4 rounded-xl shadow-sm space-y-4">
              <h3 className="text-xs font-bold text-muted uppercase tracking-wider">{group}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {fields.map(field => {
                  const metaField =
                    (meta.categories && meta.categories[categoryKey(field)]) ||
                    (field === 'tracado_via' ? TRACADO_FALLBACK : null);
                  
                  if (metaField) {
                    // É categórico
                    return (
                      <SelectField 
                        key={field}
                        name={`features.${field}`}
                        label={labelOverrides[field] || field.replace('_', ' ').toUpperCase()}
                        options={[
                          { value: "", label: "Selecione..." },
                          ...metaField.map((val: string) => ({ value: val, label: val }))
                        ]}
                      />
                    );
                  } else {
                    // É numérico ou hora
                    if (field === 'horario') {
                      return (
                        <FieldWrapper key={field} label={labelOverrides[field] || "HORÁRIO"}>
                          <input type="time" step="1" {...methods.register(`features.${field}`)} className="w-full px-3 py-2 bg-bg border border-border rounded-md text-sm" />
                        </FieldWrapper>
                      );
                    }
                    return (
                      <NumberField 
                        key={field}
                        name={`features.${field}`}
                        label={labelOverrides[field] || field.replace('_', ' ').toUpperCase()}
                        min={0}
                        step="any"
                      />
                    );
                  }
                })}
              </div>
            </div>
          );
        })}

        <div className="flex gap-4 pt-2">
          <button 
            type="button" 
            onClick={() => reset({ runId: watchRunId, features: {} })}
            className="px-4 py-2 border border-border bg-panel text-muted hover:text-text rounded font-medium text-sm transition-colors"
          >
            Limpar
          </button>
          <button 
            type="submit" 
            disabled={isPredicting || !selectedRun}
            className="flex-1 px-4 py-2 bg-primary text-white rounded font-medium text-sm flex items-center justify-center gap-2 hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isPredicting ? <Icons.System className="w-4 h-4 animate-spin" /> : <Icons.Play className="w-4 h-4" />}
            Estimar Gravidade
          </button>
        </div>
      </form>
    </FormProvider>
  );
}
