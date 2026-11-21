import { z } from "zod";

// Valores aceitáveis para as opções da interface baseadas na spec
export const TargetEnum = z.enum(["fatal_binario", "gravidade_3_classes"]);
export const ScalerEnum = z.enum(["standard", "minmax", "none"]);
export const ClassWeightEnum = z.enum(["none", "balanced", "custom"]);
export const ActivationEnum = z.enum(["relu", "tanh", "sigmoid", "leaky_relu"]);
export const InitEnum = z.enum(["he", "xavier", "normal"]);
export const LossEnum = z.enum(["ce", "weighted_ce", "focal"]);
export const OptimizerEnum = z.enum(["sgd", "momentum", "adam", "adamw"]);
export const LrDecayEnum = z.enum(["none", "step", "cosine"]);

export const DataConfigSchema = z.object({
  target: TargetEnum,
  feature_groups: z.array(z.string()).min(1, "Selecione pelo menos um grupo de features"),
  max_rows: z.number().min(100, "Mínimo de 100 linhas").nullable().optional(),
  val_size: z.number().min(0).max(0.4),
  test_size: z.number().min(0.01).max(0.4),
  stratify: z.boolean(),
  seed: z.number().int().min(0),
  rare_min_count: z.number().int().min(0),
  scaler: ScalerEnum,
  log1p_numeric: z.boolean(),
  class_weight: ClassWeightEnum,
  custom_weights: z.array(z.number().positive()).nullable().optional(),
  drop_duplicates: z.boolean(),
});

export const ModelConfigSchema = z.object({
  hidden_layers: z.number().int().min(1).max(4),
  neurons: z.array(z.number().int().min(1)).min(1).max(4),
  activation: ActivationEnum,
  init: InitEnum,
  dropout: z.number().min(0).max(0.5),
  l2: z.number().min(0).max(0.1),
  loss: LossEnum,
  focal_gamma: z.number().min(0),
  optimizer: OptimizerEnum,
  lr: z.number().gt(0).lte(1),
  lr_decay: LrDecayEnum,
  decay_rate: z.number().gt(0).lt(1),
  decay_every: z.number().int().min(1),
  batch_size: z.number().int().min(1).nullable().optional(),
  epochs: z.number().int().min(1).max(2000),
  patience: z.number().int().min(0),
  grad_clip: z.number().min(0),
  threshold: z.number().min(0.05).max(0.95),
  seed: z.number().int().min(0),
});

export const RunCreateSchema = z.object({
  name: z.string().min(1, "Nome é obrigatório").max(80, "Máximo de 80 caracteres"),
  data: DataConfigSchema,
  model: ModelConfigSchema,
}).superRefine((val, ctx) => {
  if (val.model.neurons.length !== val.model.hidden_layers) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["model", "neurons"],
      message: `A lista de neurônios deve ter tamanho igual a hidden_layers (${val.model.hidden_layers})`,
    });
  }
  if (val.data.class_weight === "custom" && (!val.data.custom_weights || val.data.custom_weights.length === 0)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["data", "custom_weights"],
      message: "Pesos personalizados são obrigatórios quando class_weight é 'custom'",
    });
  }
});

export type DataConfig = z.infer<typeof DataConfigSchema>;
export type ModelConfig = z.infer<typeof ModelConfigSchema>;
export type RunCreate = z.infer<typeof RunCreateSchema>;
