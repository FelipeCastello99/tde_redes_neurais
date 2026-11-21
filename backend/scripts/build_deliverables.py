#!/usr/bin/env python3
"""Gera DOCX, PDF, slides e backup dos artefatos da entrega."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import qrcode
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from PIL import Image as PILImage
from pptx import Presentation
from pptx.util import Inches as PptInches
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as PdfImage,
)
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
SHOTS = DOCS / "screenshots"
RUNS = ROOT / "backend" / "artifacts" / "runs"
BACKUP = DOCS / "backup_run"

IDENTITY = (
    "Felipe Medeiros Castello Branco · Herbeth Lucas de Sousa Pereira · "
    "Samuel Pereira da Silva Varão"
)
COURSE = "[CURSO] · [INSTITUIÇÃO] · [SEMESTRE]"
PROFESSOR = "Prof. Edilson Carlos Silva Lima"


def find_demo_run() -> tuple[Path, dict, dict]:
    candidates = sorted(
        (path for path in RUNS.glob("*/run.json")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("name", "").startswith("Demo"):
            evaluation_path = path.parent / "evaluation.json"
            evaluation = (
                json.loads(evaluation_path.read_text(encoding="utf-8"))
                if evaluation_path.exists()
                else {}
            )
            return path.parent, manifest, evaluation
    raise SystemExit("Nenhum run Demo encontrado. Rode `make seed` antes.")


def backup_artifacts(run_dir: Path) -> None:
    if BACKUP.exists():
        shutil.rmtree(BACKUP)
    BACKUP.mkdir(parents=True)
    for name in (
        "run.json",
        "evaluation.json",
        "curves.json",
        "preprocessor.json",
        "model.json",
        "weights.npz",
        "log.txt",
    ):
        source = run_dir / name
        if source.exists():
            shutil.copy2(source, BACKUP / name)


def metric_rows(manifest: dict, evaluation: dict) -> list[tuple[str, str]]:
    metrics = manifest.get("metrics") or evaluation
    per_class = metrics.get("precision_recall_f1", {}).get("per_class", [])
    fatal_f1 = per_class[1]["f1"] if len(per_class) > 1 else float("nan")
    return [
        ("Acurácia", f"{metrics.get('accuracy', 0):.4f}"),
        ("F1 macro", f"{metrics.get('precision_recall_f1', {}).get('macro', {}).get('f1', 0):.4f}"),
        ("F1 da classe fatal", f"{fatal_f1:.4f}"),
        ("ROC-AUC", f"{metrics.get('roc_auc', 0):.4f}"),
        ("PR-AUC", f"{metrics.get('pr_auc', 0):.4f}"),
        ("Log-loss", f"{metrics.get('log_loss', 0):.4f}"),
        ("Brier", f"{metrics.get('brier_score', 0):.4f}"),
        ("ECE", f"{metrics.get('ece', 0):.4f}"),
    ]


def build_qrcode() -> Path:
    path = DOCS / "qrcode.png"
    image = qrcode.make("http://localhost:3000")
    image.save(path)
    return path


def build_docx(manifest: dict, evaluation: dict) -> Path:
    path = DOCS / "TDE_documento_explicativo.docx"
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    title = document.add_heading("TDE — Rede Neural aplicada a acidentes em rodovias federais", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph("Documento explicativo")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].bold = True
    subtitle.runs[0].font.size = Pt(14)

    document.add_paragraph(f"Integrantes: {IDENTITY}")
    document.add_paragraph(f"Professor: {PROFESSOR}")
    document.add_paragraph(f"Curso / Instituição / Semestre: {COURSE}")
    document.add_paragraph("Dataset: PRF DATATRAN 2024")
    document.add_paragraph("")

    def heading(text: str) -> None:
        document.add_heading(text, level=1)

    def bullets(items: list[str]) -> None:
        for item in items:
            document.add_paragraph(item, style="List Bullet")

    heading("1. Introdução")
    document.add_paragraph(
        "Este trabalho aplica uma Rede Neural Multicamadas (MLP) implementada do zero "
        "em NumPy para estimar a gravidade de acidentes em rodovias federais brasileiras. "
        "O projeto integra notebook acadêmico, API FastAPI, PostgreSQL, interface Next.js "
        "e um simulador de cenários."
    )
    document.add_paragraph(
        "A implementação não usa frameworks de aprendizado profundo: forward, loss, "
        "backpropagation, otimizadores, dropout e early stopping estão no código do projeto "
        "e podem ser inspecionados no notebook."
    )

    heading("2. Problema, objetivos e justificativa")
    document.add_paragraph(
        "A gravidade de um acidente é um fenômeno raro e desbalanceado: cerca de 7,1% "
        "das ocorrências de 2024 tiveram vítima fatal. O objetivo é estimar a probabilidade "
        "de fatalidade a partir do cenário registrado, apoiando análise de risco e discussão "
        "de políticas de segurança viária."
    )
    bullets(
        [
            "Objetivo geral: classificar ocorrências em sem vítima fatal ou com vítima fatal.",
            "Objetivo secundário: comparar a formulação binária com a classificação de 3 classes.",
            "Objetivo aplicado: expor o modelo em uma interface com treino configurável e simulador.",
        ]
    )

    heading("3. Dataset")
    document.add_paragraph(
        "Fonte: Polícia Rodoviária Federal (PRF), DATATRAN 2024, visão agrupada por ocorrência. "
        "O arquivo usa latin-1, separador ponto e vírgula e vírgula decimal em km/latitude/longitude."
    )
    table = document.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    table.rows[0].cells[0].text = "Indicador"
    table.rows[0].cells[1].text = "Valor"
    for label, value in [
        ("Registros no arquivo", "73.202"),
        ("Registros usados", "73.201 (1 alvo NA)"),
        ("Colunas", "30"),
        ("Vítimas fatais", "5.225 (7,1%)"),
        ("SHA-256 do CSV", "7d26e6f4…4366d"),
    ]:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
    document.add_paragraph(
        "Colunas de vazamento (mortos, feridos, pessoas, classificação) e identificadores "
        "foram excluídos. O modelo usa apenas informações disponíveis no cenário."
    )

    heading("4. Metodologia e preparação")
    bullets(
        [
            "Limpeza: remoção do único registro com alvo NA.",
            "Split estratificado 60/20/20 com seed 42.",
            "Features: br, km, veículos, hora sin/cos, fim de semana, UF, dia, via, clima, causa e tipo.",
            "Categorias raras agrupadas em __OUTROS__ (rare_min_count=30).",
            "Padronização e fit do preprocessor somente no treino.",
            "Pesos de classe balanceados: n / (k × bincount).",
        ]
    )

    heading("5. Arquitetura e implementação da MLP")
    document.add_paragraph(
        "A rede padrão possui uma camada oculta com 32 neurônios ReLU e saída softmax. "
        "A loss é cross-entropy ponderada; o otimizador é Adam; há gradient clipping por "
        "norma global, early stopping na loss de validação e restauração do melhor checkpoint."
    )
    config = manifest.get("config", {}).get("model", {})
    table = document.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    table.rows[0].cells[0].text = "Hiperparâmetro"
    table.rows[0].cells[1].text = "Valor"
    for key in (
        "hidden_layers",
        "neurons",
        "activation",
        "init",
        "dropout",
        "l2",
        "loss",
        "optimizer",
        "lr",
        "batch_size",
        "epochs",
        "patience",
    ):
        cells = table.add_row().cells
        cells[0].text = key
        cells[1].text = str(config.get(key))
    document.add_paragraph(
        "Derivadas: ReLU usa máscara z > 0; softmax é calculada com subtração do máximo; "
        "o gradiente da cross-entropy em relação às logits é (p − y), ponderado pelas classes. "
        "O backward aplica a regra da cadeia camada a camada."
    )

    heading("6. Treinamento e resultados")
    document.add_paragraph(
        "O treinamento acompanha loss de treino/validação, acurácia, F1 e norma do gradiente. "
        "O conjunto de teste é avaliado uma única vez com o melhor checkpoint."
    )
    table = document.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    table.rows[0].cells[0].text = "Métrica (teste)"
    table.rows[0].cells[1].text = "Valor"
    for label, value in metric_rows(manifest, evaluation):
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
    document.add_paragraph(
        "A acurácia é alta, mas insuficiente: o baseline majoritário já acerta cerca de 93%. "
        "Por isso, o F1 da classe fatal, o PR-AUC e a calibração são as métricas centrais."
    )
    for name, caption in (
        ("03-resultados.png", "Resultados do run Demo: métricas, matriz, curvas e calibração."),
        ("06-simulador.png", "Simulador com probabilidade e contribuições por campo."),
    ):
        image_path = SHOTS / name
        if image_path.exists():
            document.add_picture(str(image_path), width=Inches(6.4))
            document.add_paragraph(caption).alignment = WD_ALIGN_PARAGRAPH.CENTER

    heading("7. Aplicação demonstrativa")
    document.add_paragraph(
        "A aplicação sobe com `make up`: serviços data (download do CSV), db (PostgreSQL 16), "
        "api (FastAPI) e web (Next.js standalone). O frontend conversa com a API por proxy "
        "runtime, incluindo SSE para acompanhar o treino em tempo real."
    )
    bullets(
        [
            "Dashboard com histórico e métricas.",
            "Treino configurável com presets e formulário completo de hiperparâmetros.",
            "Resultados com matriz de confusão, ROC/PR, calibração e varredura de limiar.",
            "Comparação de até 4 runs.",
            "Simulador com gauge/binário ou barras multiclasse e contribuições.",
        ]
    )
    document.add_paragraph("Endereço local: http://localhost:3000")
    qr_path = DOCS / "qrcode.png"
    if qr_path.exists():
        document.add_picture(str(qr_path), width=Inches(1.5))
    for name, caption in (
        ("01-dashboard.png", "Dashboard com o run Demo."),
        ("04-comparar.png", "Comparação de runs."),
        ("05-dados.png", "Página do dataset e vazamento de dados."),
    ):
        image_path = SHOTS / name
        if image_path.exists():
            document.add_picture(str(image_path), width=Inches(6.2))
            document.add_paragraph(caption).alignment = WD_ALIGN_PARAGRAPH.CENTER

    heading("8. Conclusão, limitações e trabalhos futuros")
    document.add_paragraph(
        "A MLP do zero é viável e didática. O teto de desempenho é limitado pela base: "
        "velocidade, cinto, tipo de veículo e tempo de socorro não estão disponíveis. "
        "O modelo deve ser tratado como protótipo acadêmico, não como ferramenta de decisão."
    )
    bullets(
        [
            "Limitações: subnotificação, causa provável atribuída, recorte de um ano e granularidade por ocorrência.",
            "Melhorias: calibração, validação temporal/por UF, baselines de boosting e explicabilidade local.",
            "Próximos passos: substituir [CURSO]/[INSTITUIÇÃO]/[SEMESTRE], revisar ortografia e ensaiar a demo offline.",
        ]
    )

    document.save(path)
    return path


def build_pdf(manifest: dict, evaluation: dict, qr_path: Path) -> Path:
    path = DOCS / "TDE_documento_explicativo.pdf"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Body2", parent=styles["BodyText"], leading=15, spaceAfter=6))
    styles.add(ParagraphStyle(name="Small2", parent=styles["BodyText"], fontSize=8, leading=10))
    story: list = []

    story.append(Paragraph("TDE — Rede Neural aplicada a acidentes em rodovias federais", styles["Title"]))
    story.append(Paragraph("Documento explicativo", styles["Heading2"]))
    story.append(Paragraph(f"<b>Integrantes:</b> {IDENTITY}", styles["Body2"]))
    story.append(Paragraph(f"<b>Professor:</b> {PROFESSOR}", styles["Body2"]))
    story.append(Paragraph(f"<b>Curso / Instituição / Semestre:</b> {COURSE}", styles["Body2"]))
    story.append(Spacer(1, 0.4 * cm))

    sections = [
        (
            "1. Introdução",
            "Este trabalho aplica uma MLP implementada do zero em NumPy para estimar a gravidade de acidentes "
            "em rodovias federais. O projeto integra notebook, API FastAPI, PostgreSQL, interface Next.js e simulador. "
            "Forward, loss, backpropagation, otimizadores e early stopping são implementados no código do projeto.",
        ),
        (
            "2. Problema e objetivos",
            "A base é desbalanceada: cerca de 7,1% das ocorrências têm vítima fatal. O objetivo é estimar a probabilidade "
            "de fatalidade a partir do cenário e comparar a formulação binária com a de três classes.",
        ),
        (
            "3. Dataset",
            "PRF DATATRAN 2024, 73.202 registros e 30 colunas; 73.201 usados após remover o único alvo NA. "
            "A leitura é latin-1, separador ';' e vírgula decimal. Colunas de vazamento foram excluídas.",
        ),
        (
            "4. Metodologia",
            "Split estratificado 60/20/20 com seed 42; features de localização, tempo, via, circunstância e frota; "
            "categorias raras agrupadas em __OUTROS__; padronização ajustada somente no treino; pesos de classe balanceados.",
        ),
        (
            "5. Arquitetura",
            "A rede padrão usa uma camada oculta de 32 neurônios ReLU e saída softmax. A loss é cross-entropy ponderada, "
            "o otimizador é Adam e há gradient clipping, early stopping e restauração do melhor checkpoint.",
        ),
        (
            "6. Resultados",
            "O teste é avaliado uma única vez. A acurácia é alta, mas o baseline majoritário já acerta cerca de 93%; "
            "por isso F1 da classe fatal, PR-AUC, log-loss, Brier e calibração são as métricas centrais.",
        ),
        (
            "7. Aplicação demonstrativa",
            "A aplicação sobe com `make up`: data (download do CSV), db (PostgreSQL 16), api (FastAPI) e web (Next.js). "
            "O frontend usa proxy runtime e SSE para acompanhar o treino. Endereço local: http://localhost:3000.",
        ),
        (
            "8. Conclusão e limitações",
            "O teto de desempenho é limitado pela base: velocidade, cinto, tipo de veículo e tempo de socorro não estão "
            "disponíveis. O modelo é um protótipo acadêmico. Melhorias incluem calibração, validação temporal/por UF, "
            "baselines de boosting e explicabilidade local.",
        ),
    ]
    for title, text in sections:
        story.append(Paragraph(title, styles["Heading1"]))
        story.append(Paragraph(text, styles["Body2"]))
        if title == "6. Resultados":
            table_data = [["Métrica", "Valor"]] + [list(row) for row in metric_rows(manifest, evaluation)]
            table = Table(table_data, colWidths=[8 * cm, 5 * cm])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e7490")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.3 * cm))

    for image_name, caption in (
        ("03-resultados.png", "Resultados do run Demo."),
        ("06-simulador.png", "Simulador com probabilidade e contribuições."),
        ("01-dashboard.png", "Dashboard da aplicação."),
    ):
        image_path = SHOTS / image_name
        if image_path.exists():
            reader = PILImage.open(image_path)
            width = 17 * cm
            height = width * reader.height / reader.width
            story.append(PdfImage(str(image_path), width=width, height=height))
            story.append(Paragraph(caption, styles["Small2"]))

    story.append(Paragraph("Aplicação demonstrativa: http://localhost:3000", styles["Body2"]))
    if qr_path.exists():
        story.append(PdfImage(str(qr_path), width=3 * cm, height=3 * cm))

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="TDE — Rede Neural aplicada a acidentes",
    )
    doc.build(story)
    return path


def build_slides(manifest: dict, evaluation: dict) -> Path:
    path = DOCS / "TDE_apresentacao.pptx"
    presentation = Presentation()
    presentation.slide_width = PptInches(13.333)
    presentation.slide_height = PptInches(7.5)

    def add_slide(title: str, bullets: list[str], notes: str, image: str | None = None) -> None:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = title
        body = slide.placeholders[1]
        text_frame = body.text_frame
        text_frame.text = bullets[0]
        for bullet in bullets[1:]:
            paragraph = text_frame.add_paragraph()
            paragraph.text = bullet
            paragraph.level = 0
        if image and (SHOTS / image).exists():
            slide.shapes.add_picture(str(SHOTS / image), PptInches(7.1), PptInches(1.4), width=PptInches(5.6))
        slide.notes_slide.notes_text_frame.text = notes

    add_slide(
        "TDE — Rede Neural aplicada a acidentes",
        [
            "MLP do zero em NumPy",
            "PRF DATATRAN 2024",
            IDENTITY,
            PROFESSOR,
            COURSE,
        ],
        "Abertura (30 s). Apresentar o grupo, o tema e o objetivo: estimar gravidade de acidentes.",
    )
    add_slide(
        "Problema",
        [
            "Acidentes em rodovias federais: saúde pública e política pública",
            "7,1% das ocorrências têm vítima fatal",
            "Base não contém velocidade, cinto, tipo de veículo ou tempo de socorro",
            "Objetivo: probabilidade de fatalidade a partir do cenário registrado",
        ],
        "Contextualizar (1 min). Destacar o desbalanceamento e a limitação dos dados abertos.",
    )
    add_slide(
        "Dataset",
        [
            "PRF DATATRAN 2024 — 73.202 registros, 30 colunas",
            "73.201 usados (1 alvo NA)",
            "latin-1, separador ';', decimal com vírgula",
            "Vazamento removido: mortos, feridos, pessoas, classificação, id",
        ],
        "Mostrar a página /dados (1 min). Explicar por que as colunas pós-evento foram removidas.",
        "05-dados.png",
    )
    add_slide(
        "Análise exploratória",
        [
            "Classe majoritária: Com Vítimas Feridas (76,8%)",
            "Sem vítimas: 16,1% · Fatais: 7,1%",
            "Causas e tipos de acidente concentram a informação",
            "Horário e km ajudam, mas não explicam tudo",
        ],
        "EDA (1 min). Mostrar o gráfico de distribuição e reforçar o desbalanceamento.",
    )
    add_slide(
        "Metodologia",
        [
            "Split estratificado 60/20/20",
            "Features numéricas + one-hot de categóricas",
            "__OUTROS__ para categorias raras",
            "Preprocessor ajustado só no treino",
            "Pesos de classe balanceados",
        ],
        "Metodologia (1 min). Enfatizar prevenção de vazamento e reprodutibilidade.",
    )
    add_slide(
        "MLP do zero em NumPy",
        [
            "Entrada (features) → 32 ReLU → softmax",
            "Forward com cache, softmax estável",
            "Backward manual e regra da cadeia",
            "Adam, gradient clipping, dropout e early stopping",
            "Cross-entropy ponderada",
        ],
        "Arquitetura (1,5 min). Se possível, abrir o notebook na célula de inspect.getsource.",
    )
    add_slide(
        "Treinamento",
        [
            "Seed 42 em dados, split e inicialização",
            "Loss de treino × validação por época",
            "Early stopping restaura o melhor checkpoint",
            "Histórico e artefatos por run",
        ],
        "Treino (1 min). Mostrar a tela /treinar ou as curvas do notebook.",
        "02-treinar.png",
    )
    add_slide(
        "Resultados",
        [
            f"Acurácia: {manifest.get('metrics', {}).get('accuracy', 0):.2%}",
            f"F1 macro: {manifest.get('metrics', {}).get('precision_recall_f1', {}).get('macro', {}).get('f1', 0):.2%}",
            f"ROC-AUC: {manifest.get('metrics', {}).get('roc_auc', 0):.2%}",
            "Acurácia isolada engana: baseline já acerta ~93%",
            "F1 fatal, PR-AUC e calibração são as métricas centrais",
        ],
        "Resultados (1,5 min). Mostrar /resultados e a matriz de confusão. Explicar falso negativos.",
        "03-resultados.png",
    )
    add_slide(
        "Binário × 3 classes",
        [
            "Mesma arquitetura para os dois alvos",
            "3 classes: Sem Vítimas, Com Feridos, Com Fatais",
            "Multiclasse é mais difícil e menos estável",
            "Binário é mais adequado para triagem de letalidade",
        ],
        "Comparação (1 min). Mostrar a tabela do notebook.",
    )
    add_slide(
        "Aplicação demonstrativa",
        [
            "Dashboard + treino configurável + resultados + comparação",
            "Simulador com probabilidade e contribuições",
            "FastAPI + PostgreSQL + Next.js + Docker Compose",
            "Um comando: make up · demo pronta: make seed",
        ],
        "Demo (2 min). Abrir dashboard, resultados, simulador e comparar. Plano B: make seed.",
        "01-dashboard.png",
    )
    add_slide(
        "Limitações e melhorias",
        [
            "Fatores ausentes: velocidade, cinto, veículo, socorro",
            "Subnotificação e causa provável",
            "Recorte de 2024 e granularidade por ocorrência",
            "Melhorias: calibração, validação temporal/UF, boosting e explicabilidade",
        ],
        "Limitações (30 s). Ser honesto sobre o teto de desempenho.",
    )
    add_slide(
        "Conclusão",
        [
            "MLP do zero viável e didática",
            "Aplicação completa e reproduzível",
            "Teto limitado pela base, não pela arquitetura",
            "Obrigado! Perguntas?",
        ],
        "Fechamento (30 s). Agradecer e abrir perguntas.",
    )
    presentation.save(path)
    return path


def build_roteiro() -> Path:
    path = DOCS / "roteiro_demo.md"
    path.write_text(
        """# Roteiro de demonstração (10 minutos)

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
""",
        encoding="utf-8",
    )
    return path


def build_pendencias() -> Path:
    path = DOCS / "PENDENCIAS_ENTREGA.md"
    path.write_text(
        """# Pendências da entrega

Os itens abaixo dependem de informação externa e **não podem ser inventados**:

- [ ] Substituir `[CURSO]`, `[INSTITUIÇÃO]` e `[SEMESTRE]` no notebook, DOCX/PDF e rodapé do site.
- [ ] Confirmar com o professor a autorização do grupo de 3 integrantes.
- [ ] Definir URL pública (se houver) para o QR code; o atual aponta para `http://localhost:3000`.
- [ ] Revisão ortográfica final humana do DOCX/PDF e do notebook.
- [ ] Ensaiar a demo cronometrada de 10 minutos sem internet.

Observação: o QR code e o link local estão em `docs/qrcode.png` e no documento.
""",
        encoding="utf-8",
    )
    return path


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    run_dir, manifest, evaluation = find_demo_run()
    backup_artifacts(run_dir)
    qr_path = build_qrcode()
    docx = build_docx(manifest, evaluation)
    pdf = build_pdf(manifest, evaluation, qr_path)
    pptx = build_slides(manifest, evaluation)
    roteiro = build_roteiro()
    pendencias = build_pendencias()
    print("DOCX:", docx)
    print("PDF:", pdf)
    print("PPTX:", pptx)
    print("Roteiro:", roteiro)
    print("Pendências:", pendencias)
    print("Backup:", BACKUP)


if __name__ == "__main__":
    main()
