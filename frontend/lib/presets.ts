import { DataConfig, ModelConfig } from "./validation";

export type PresetName = "rapido" | "equilibrado" | "profundo";

export const defaultDataConfig: DataConfig = {
  target: "fatal_binario",
  feature_groups: ["localizacao", "tempo", "via", "circunstancia", "frota"],
  max_rows: null,
  val_size: 0.2,
  test_size: 0.2,
  stratify: true,
  seed: 42,
  rare_min_count: 30,
  scaler: "standard",
  log1p_numeric: true,
  class_weight: "balanced",
  custom_weights: null,
  drop_duplicates: true,
};

export const defaultModelConfig: ModelConfig = {
  hidden_layers: 2,
  neurons: [64, 32],
  activation: "relu",
  init: "he",
  dropout: 0.0,
  l2: 0.0,
  loss: "weighted_ce",
  focal_gamma: 2.0,
  optimizer: "adam",
  lr: 0.001,
  lr_decay: "none",
  decay_rate: 0.5,
  decay_every: 50,
  batch_size: 256,
  epochs: 200,
  patience: 15,
  grad_clip: 5.0,
  threshold: 0.5,
  seed: 42,
};

export const presets: Record<PresetName, { name: string; description: string; data: Partial<DataConfig>; model: Partial<ModelConfig> }> = {
  rapido: {
    name: "Rápido (Demo)",
    description: "Treino rápido usando até 20.000 amostras com uma rede simples de 32 neurônios e Full Batch.",
    data: { max_rows: 20000 },
    model: { hidden_layers: 1, neurons: [32], batch_size: null, lr: 0.003, epochs: 80 }
  },
  equilibrado: {
    name: "Equilibrado",
    description: "Configuração padrão. Balanço ideal entre velocidade e performance (≈ 2-4 minutos).",
    data: {},
    model: {}
  },
  profundo: {
    name: "Profundo",
    description: "Rede profunda [128, 64, 32] com AdamW, regularização (Dropout/L2) e até 300 épocas.",
    data: {},
    model: { hidden_layers: 3, neurons: [128, 64, 32], dropout: 0.1, l2: 1e-4, optimizer: "adamw", lr_decay: "cosine", epochs: 300 }
  }
};

export function getPresetConfig(preset: PresetName | null): { data: DataConfig, model: ModelConfig } {
  const data = { ...defaultDataConfig };
  const model = { ...defaultModelConfig };
  
  if (preset && presets[preset]) {
    Object.assign(data, presets[preset].data);
    Object.assign(model, presets[preset].model);
  }
  
  return { data, model };
}
