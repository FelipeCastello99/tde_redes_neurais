import { describe, expect, it } from "vitest";

import { defaultDataConfig, defaultModelConfig } from "@/lib/presets";
import { RunCreateSchema } from "@/lib/validation";

function validPayload() {
  return {
    name: "Teste",
    data: { ...defaultDataConfig },
    model: { ...defaultModelConfig, neurons: [...defaultModelConfig.neurons] },
  };
}

describe("RunCreateSchema", () => {
  it("aceita a configuração padrão", () => {
    const result = RunCreateSchema.safeParse(validPayload());
    expect(result.success).toBe(true);
  });

  it("rejeita neurons incompatível com hidden_layers", () => {
    const payload = validPayload();
    payload.model = { ...payload.model, hidden_layers: 3, neurons: [32, 16] };
    const result = RunCreateSchema.safeParse(payload);
    expect(result.success).toBe(false);
  });

  it("rejeita class_weight custom sem pesos", () => {
    const payload = validPayload();
    payload.data = { ...payload.data, class_weight: "custom", custom_weights: null };
    const result = RunCreateSchema.safeParse(payload);
    expect(result.success).toBe(false);
  });

  it("rejeita nome vazio", () => {
    const payload = validPayload();
    payload.name = "";
    expect(RunCreateSchema.safeParse(payload).success).toBe(false);
  });
});
