import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConfusionMatrix } from "@/components/charts/ConfusionMatrix";

describe("ConfusionMatrix", () => {
  it("renderiza uma matriz 2x2 com rótulos e contagens", () => {
    render(
      <ConfusionMatrix
        matrix={[
          [40, 10],
          [5, 45],
        ]}
        classNames={["sem_vitima_fatal", "vitima_fatal"]}
      />
    );

    expect(screen.getAllByText("sem_vitima_fatal").length).toBeGreaterThan(0);
    expect(screen.getAllByText("vitima_fatal").length).toBeGreaterThan(0);
    expect(screen.getByText("45")).toBeInTheDocument();
  });

  it("renderiza uma matriz 3x3", () => {
    render(
      <ConfusionMatrix
        matrix={[
          [10, 1, 0],
          [2, 20, 3],
          [0, 4, 15],
        ]}
        classNames={["Sem Vítimas", "Com Vítimas Feridas", "Com Vítimas Fatais"]}
      />
    );

    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getAllByText("Com Vítimas Fatais").length).toBeGreaterThan(0);
  });
});
