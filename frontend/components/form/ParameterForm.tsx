"use client";

import { useForm, FormProvider } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { RunCreateSchema, RunCreate } from "@/lib/validation";
import { defaultDataConfig, defaultModelConfig, presets, PresetName, getPresetConfig } from "@/lib/presets";
import { SectionAccordion } from "./SectionAccordion";
import { NumberField, SelectField, SwitchField } from "./Fields";
import { MultiCheckbox, NeuronsEditor } from "./ComplexFields";
import { useState, useEffect } from "react";
import { Icons } from "@/components/icons";

export function ParameterForm({ 
  onSubmit, 
  isSubmitting 
}: { 
  onSubmit: (data: RunCreate) => void,
  isSubmitting: boolean 
}) {
  const methods = useForm<RunCreate>({
    resolver: zodResolver(RunCreateSchema),
    defaultValues: {
      name: "Novo Treinamento",
      data: defaultDataConfig,
      model: defaultModelConfig,
    }
  });

  const { handleSubmit, watch, reset, setValue } = methods;
  const watchAll = watch();

  const applyPreset = (preset: PresetName) => {
    const { data, model } = getPresetConfig(preset);
    reset({ name: presets[preset].name, data, model });
  };

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        
        <SectionAccordion title="1. Objetivo" number={1} defaultOpen summary={watchAll.name}>
          <div className="space-y-4">
            <FieldWrapper label="Nome do Run">
              <input type="text" {...methods.register("name")} className="w-full px-3 py-2 bg-bg border border-border rounded-md text-sm text-text" />
            </FieldWrapper>
            
            <SelectField 
              name="data.target" 
              label="Alvo" 
              options={[
                { value: "fatal_binario", label: "Binário (Com Vítima Fatal vs Sem Vítima Fatal)" },
                { value: "gravidade_3_classes", label: "3 Classes (Sem Vítimas, Com Feridos, Com Fatais)" }
              ]} 
            />

            <div className="pt-4 border-t border-border">
              <p className="text-sm font-medium mb-2">Predefinições (Presets)</p>
              <div className="flex gap-2">
                {(Object.keys(presets) as PresetName[]).map(p => (
                  <button key={p} type="button" onClick={() => applyPreset(p)} className="px-3 py-1.5 bg-panel-2 hover:bg-primary/10 hover:text-primary text-sm rounded transition-colors">
                    {presets[p].name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </SectionAccordion>

        <SectionAccordion title="2. Dados" number={2}>
          <div className="space-y-4">
            <MultiCheckbox name="data.feature_groups" label="Grupos de Features" />
            <div className="grid grid-cols-2 gap-4">
              <NumberField name="data.max_rows" label="Amostras (max_rows)" min={100} placeholder="73202 (Todos)" tooltip="Útil para testes rápidos. Mantém a estratificação." />
              <NumberField name="data.seed" label="Semente Aleatória" min={0} />
              <SwitchField name="data.stratify" label="Estratificar Splits" />
              <SwitchField name="data.drop_duplicates" label="Remover Duplicadas" />
            </div>
          </div>
        </SectionAccordion>

        <SectionAccordion title="3. Pré-processamento" number={3}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <SelectField name="data.scaler" label="Escala (Numéricos)" options={[
                { value: "standard", label: "Standard (Z-Score)" },
                { value: "minmax", label: "MinMax (0-1)" },
                { value: "none", label: "Nenhuma" }
              ]} />
              <NumberField name="data.rare_min_count" label="Mínimo p/ Categoria" min={0} tooltip="Agrupa categorias raras em __OUTROS__" />
            </div>
            <SwitchField name="data.log1p_numeric" label="Aplicar log1p em contagens" tooltip="Aplica log(x+1) em km, br e veículos" />
            <SelectField name="data.class_weight" label="Pesos de Classe" options={[
                { value: "balanced", label: "Balanceado (inversamente proporcional)" },
                { value: "none", label: "Nenhum (peso igual)" },
                { value: "custom", label: "Personalizado" }
            ]} />
          </div>
        </SectionAccordion>

        <SectionAccordion title="4. Arquitetura" number={4}>
          <div className="space-y-4">
            <NumberField name="model.hidden_layers" label="Camadas Ocultas" min={1} max={4} />
            <NeuronsEditor name="model.neurons" sourceField="model.hidden_layers" />
            <div className="grid grid-cols-2 gap-4">
              <SelectField name="model.activation" label="Ativação" options={[
                { value: "relu", label: "ReLU" },
                { value: "tanh", label: "Tanh" },
                { value: "sigmoid", label: "Sigmoid" },
                { value: "leaky_relu", label: "Leaky ReLU" }
              ]} />
              <SelectField name="model.init" label="Inicialização" options={[
                { value: "he", label: "He Normal (ideal p/ ReLU)" },
                { value: "xavier", label: "Xavier Normal (ideal p/ Tanh)" },
                { value: "normal", label: "Normal (0.01)" }
              ]} />
              <NumberField name="model.dropout" label="Dropout" step="any" min={0} max={0.5} />
              <NumberField name="model.l2" label="Regularização L2" step="any" min={0} max={0.1} />
            </div>
          </div>
        </SectionAccordion>

        <SectionAccordion title="5. Otimização" number={5}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <SelectField name="model.optimizer" label="Otimizador" options={[
                { value: "adam", label: "Adam" },
                { value: "adamw", label: "AdamW" },
                { value: "momentum", label: "Momentum" },
                { value: "sgd", label: "SGD" }
              ]} />
              <NumberField name="model.lr" label="Taxa de Aprendizado (LR)" step="any" min={0.0001} max={1} />
              
              <SelectField name="model.lr_decay" label="Decaimento de LR" options={[
                { value: "none", label: "Nenhum" },
                { value: "step", label: "Step (Degrau)" },
                { value: "cosine", label: "Cosseno (Cosine Annealing)" }
              ]} />
              <NumberField name="model.epochs" label="Épocas Máximas" min={1} max={2000} />
              
              <NumberField name="model.batch_size" label="Tamanho do Lote (Batch)" min={1} placeholder="Completo" tooltip="Vazio para Full-Batch" />
              <NumberField name="model.patience" label="Paciência (Early Stopping)" min={0} tooltip="0 para desligar" />
              <NumberField name="model.grad_clip" label="Gradient Clipping (Norma)" step="any" min={0} tooltip="0 para desligar" />
            </div>
          </div>
        </SectionAccordion>

        <SectionAccordion title="6. Avaliação" number={6}>
          <div className="space-y-4">
            <SelectField name="model.loss" label="Função de Perda" options={[
              { value: "weighted_ce", label: "Cross-Entropy Ponderada" },
              { value: "ce", label: "Cross-Entropy Padrão" },
              { value: "focal", label: "Focal Loss" }
            ]} />
            {watchAll.model.loss === "focal" && (
              <NumberField name="model.focal_gamma" label="Focal Gamma (γ)" step="any" min={0} />
            )}
            <NumberField name="model.threshold" label="Limiar de Decisão (Binário)" step="any" min={0.05} max={0.95} />
          </div>
        </SectionAccordion>

        <div className="sticky bottom-0 bg-panel border-t border-border p-4 shadow-lg -mx-6 rounded-b-xl flex items-center justify-between z-20">
          <button type="button" onClick={() => reset()} className="text-sm text-muted hover:text-text px-3 py-2">
            Resetar
          </button>
          
          <button 
            type="submit" 
            disabled={isSubmitting}
            className="flex items-center gap-2 bg-primary text-white font-medium px-6 py-2.5 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isSubmitting ? (
              <Icons.System className="w-5 h-5 animate-spin" />
            ) : (
              <Icons.Play className="w-4 h-4" />
            )}
            Iniciar Treinamento
          </button>
        </div>
      </form>
    </FormProvider>
  );
}

// Recriar field wrapper aqui já que foi omitido export
function FieldWrapper({ label, tooltip, error, children }: any) {
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
