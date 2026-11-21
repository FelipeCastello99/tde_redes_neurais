import { describe, expect, it } from "vitest";

import { getPresetConfig, presets } from "@/lib/presets";

describe("presets", () => {
  it("rapido usa no máximo 20 mil amostras e uma camada", () => {
    const { data, model } = getPresetConfig("rapido");
    expect(data.max_rows).toBe(20000);
    expect(model.hidden_layers).toBe(1);
    expect(model.neurons).toEqual([32]);
    expect(model.batch_size).toBeNull();
  });

  it("profundo usa três camadas e AdamW", () => {
    const { model } = getPresetConfig("profundo");
    expect(model.hidden_layers).toBe(3);
    expect(model.neurons).toEqual([128, 64, 32]);
    expect(model.optimizer).toBe("adamw");
    expect(model.lr_decay).toBe("cosine");
  });

  it("equilibrado mantém os defaults", () => {
    const { data, model } = getPresetConfig("equilibrado");
    expect(data.max_rows).toBeNull();
    expect(model.hidden_layers).toBe(2);
  });

  it("expõe os três presets previstos", () => {
    expect(Object.keys(presets)).toEqual(["rapido", "equilibrado", "profundo"]);
  });
});
