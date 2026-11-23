import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DeleteRunButton } from "@/components/runs/DeleteRunButton";
import { deleteRun } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  deleteRun: vi.fn(),
}));

const mockedDeleteRun = vi.mocked(deleteRun);

afterEach(() => {
  vi.clearAllMocks();
});

describe("DeleteRunButton", () => {
  it("abre a confirmação e apaga o run", async () => {
    mockedDeleteRun.mockResolvedValue({ status: "deleted" });
    const onDeleted = vi.fn();

    render(
      <DeleteRunButton runId="run-1" runName="Meu run" onDeleted={onDeleted} />
    );

    fireEvent.click(screen.getByRole("button", { name: "Apagar Meu run" }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Meu run")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Apagar definitivamente" })
    );

    await waitFor(() => expect(mockedDeleteRun).toHaveBeenCalledWith("run-1"));
    await waitFor(() => expect(onDeleted).toHaveBeenCalledWith("run-1"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("fecha sem apagar ao clicar em Voltar", () => {
    render(<DeleteRunButton runId="run-2" runName="Outro run" />);

    fireEvent.click(screen.getByRole("button", { name: "Apagar Outro run" }));
    fireEvent.click(screen.getByRole("button", { name: "Voltar" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mockedDeleteRun).not.toHaveBeenCalled();
  });

  it("mantém o diálogo aberto e mostra o erro da API", async () => {
    mockedDeleteRun.mockRejectedValue(new Error("run já finalizado"));

    render(<DeleteRunButton runId="run-3" runName="Run ativo" />);

    fireEvent.click(screen.getByRole("button", { name: "Apagar Run ativo" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Apagar definitivamente" })
    );

    expect(await screen.findByText("run já finalizado")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("não abre o diálogo quando desabilitado", () => {
    render(
      <DeleteRunButton
        runId="run-4"
        runName="Run em execução"
        disabled
        disabledReason="Cancele o treinamento antes de apagar"
      />
    );

    const button = screen.getByRole("button", { name: "Apagar Run em execução" });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
