import { describe, expect, it } from "vitest";

import { formatDate, formatNumber, formatPercent, formatTime } from "@/lib/format";

describe("format", () => {
  it("formata números no padrão pt-BR", () => {
    expect(formatNumber(1234.5, 1)).toBe("1.234,5");
  });

  it("formata percentuais", () => {
    expect(formatPercent(0.1234, 1)).toContain("12,3");
  });

  it("formata tempo em minutos e segundos", () => {
    expect(formatTime(65)).toBe("1 min 5 s");
    expect(formatTime(9)).toBe("9 s");
  });

  it("formata datas ISO", () => {
    expect(formatDate("2026-11-20T12:00:00Z")).toMatch(/20/);
  });
});
