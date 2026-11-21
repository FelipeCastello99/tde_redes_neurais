import { describe, expect, it } from "vitest";

// Tokens do design system (app/globals.css) — mantidos aquí para validar WCAG.
const LIGHT = {
  bg: "#f7f9fc",
  panel: "#ffffff",
  text: "#0f172a",
  muted: "#526581",
  primary: "#0e7490",
  accent: "#be185d",
  success: "#047857",
  warning: "#b45309",
  danger: "#dc2626",
};

const DARK = {
  bg: "#0b0f14",
  panel: "#111823",
  text: "#e6edf7",
  muted: "#8fa3bf",
  primary: "#22d3ee",
  accent: "#f472b6",
  success: "#34d399",
  warning: "#fbbf24",
  danger: "#f87171",
};

function luminance(hex: string): number {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16) / 255);
  return channels
    .map((channel) => (channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4))
    .reduce((acc, channel, index) => acc + channel * [0.2126, 0.7152, 0.0722][index], 0);
}

function contrast(a: string, b: string): number {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (high + 0.05) / (low + 0.05);
}

describe("contraste WCAG", () => {
  it.each(Object.entries({ light: LIGHT, dark: DARK }))(
    "texto e cores semânticas atingem 4.5:1 no tema %s",
    (_name, tokens) => {
      for (const key of ["text", "muted", "primary", "accent", "success", "warning", "danger"] as const) {
        const ratio = contrast(tokens[key], tokens.bg);
        expect(ratio, `${key} sobre bg`).toBeGreaterThanOrEqual(4.5);
      }
    }
  );

  it("texto principal sobre painel atinge 4.5:1", () => {
    expect(contrast(LIGHT.text, LIGHT.panel)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(DARK.text, DARK.panel)).toBeGreaterThanOrEqual(4.5);
  });
});
