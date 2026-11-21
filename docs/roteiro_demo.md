# Roteiro de demonstração (10 minutos)

## Antes da apresentação

```bash
make install       # apenas se o .venv ainda não existir
make up            # data + db + api + web
make seed          # run Demo — PRF 2024
```

Abrir **http://localhost:3000** e deixar as abas preparadas:
Dashboard, Resultados do Demo, Comparar e Simulador.

## Roteiro

| Tempo | Ação |
|---|---|
| 0:00–0:45 | Apresentar o problema e o dataset (7,1% fatais). |
| 0:45–2:00 | Mostrar `/dados` e explicar o vazamento removido. |
| 2:00–3:30 | Abrir o notebook: EDA, split e `inspect.getsource(NnModel)`. |
| 3:30–5:00 | Mostrar `/treinar` e as curvas de loss/F1 ao vivo. |
| 5:00–6:30 | Abrir `/resultados`: matriz, F1 fatal, ROC/PR, calibração. |
| 6:30–7:30 | Comparar binário × 3 classes. |
| 7:30–9:00 | Simulador: preencher um cenário e explicar as contribuições. |
| 9:00–10:00 | Limitações, conclusão e perguntas. |

## Plano B (sem internet)

1. `make seed` já deixa o run Demo no banco e em `backend/artifacts/`.
2. Se o Docker falhar, abrir o notebook executado e os prints em `docs/screenshots/`.
3. Se a API falhar, mostrar `docs/TDE_documento_explicativo.pdf` e o notebook.
4. Não depender de baixar o CSV durante a demo; ele já está em `backend/data/raw/`.

## Perguntas prováveis

- Por que não usar acurácia? Porque o baseline majoritário já acerta ~93%.
- Por que a rede é pequena? O sinal disponível é limitado; redes maiores não resolvem falta de variáveis.
- Por que o ROC-AUC não é 0,95? Faltam velocidade, cinto, veículo e tempo de socorro.
- O simulador é uma ferramenta de decisão? Não; é protótipo acadêmico.
