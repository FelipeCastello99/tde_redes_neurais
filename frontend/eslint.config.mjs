import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // O contrato da API é dinâmico (JSON configurável); os tipos gerados
      // pelo OpenAPI refinam as partes críticas, mas o cliente aceita payloads
      // genéricos para não acoplar a UI a cada experimento.
      "@typescript-eslint/no-explicit-any": "off",
      // A sincronização inicial de localStorage/EventSource é intencional.
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/incompatible-library": "off",
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "coverage/**",
  ]),
]);
