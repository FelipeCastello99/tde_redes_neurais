#!/usr/bin/env python3
"""Gera o documento técnico completo do TDE em DOCX."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
FIGURES = DOCS / "figures"
SHOTS = DOCS / "screenshots"
OUT = DOCS / "TDE_documento_completo.docx"

IDENTITY = (
    "Felipe Medeiros Castello Branco · Herbeth Lucas de Sousa Pereira · "
    "Samuel Pereira da Silva Varão"
)
PROFESSOR = "Prof. Edilson Carlos Silva Lima"
COURSE = "[CURSO] · [INSTITUIÇÃO] · [SEMESTRE]"
TEAL = RGBColor(0x0E, 0x74, 0x90)
DARK = RGBColor(0x0F, 0x17, 0x2A)
GREY = RGBColor(0x52, 0x65, 0x81)


def br(value: float) -> str:
    """Formata número no padrão brasileiro (vírgula decimal)."""
    return f"{value:.4f}".replace(".", ",")


def load_demo() -> tuple[dict, dict]:
    manifest = json.loads((DOCS / "backup_run" / "run.json").read_text(encoding="utf-8"))
    evaluation = json.loads(
        (DOCS / "backup_run" / "evaluation.json").read_text(encoding="utf-8")
    )
    return manifest, evaluation


class Builder:
    def __init__(self) -> None:
        self.doc = Document()
        self._setup()

    # ------------------------------------------------------------------ setup
    def _setup(self) -> None:
        self.doc.core_properties.title = "TDE — Rede Neural aplicada a acidentes em rodovias federais"
        self.doc.core_properties.author = IDENTITY
        self.doc.core_properties.subject = "Documento técnico completo — DATATRAN 2024"
        self.doc.core_properties.language = "pt-BR"
        update_fields = OxmlElement("w:updateFields")
        update_fields.set(qn("w:val"), "true")
        self.doc.settings.element.append(update_fields)

        section = self.doc.sections[0]
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)

        normal = self.doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(10.5)
        normal.font.color.rgb = DARK
        normal.paragraph_format.line_spacing = 1.12
        normal.paragraph_format.space_after = Pt(4)
        self._set_language(normal)

        for name, size, color in (
            ("Heading 1", 16, TEAL),
            ("Heading 2", 13, TEAL),
            ("Heading 3", 11.5, DARK),
        ):
            style = self.doc.styles[name]
            style.font.name = "Calibri"
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.color.rgb = color
            style.paragraph_format.space_before = Pt(10 if name == "Heading 1" else 8)
            style.paragraph_format.space_after = Pt(4)
            style.paragraph_format.keep_with_next = True
            self._set_language(style)

        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run("TDE Redes Neurais · ")
        run.font.size = Pt(8)
        run.font.color.rgb = GREY
        self._add_field(footer, "PAGE")
        run = footer.add_run(" de ")
        run.font.size = Pt(8)
        run.font.color.rgb = GREY
        self._add_field(footer, "NUMPAGES")

        header = section.header.paragraphs[0]
        header.text = "Documento técnico completo — MLP aplicada ao DATATRAN 2024"
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for run in header.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = GREY

    @staticmethod
    def _set_language(style) -> None:
        r_pr = style.element.get_or_add_rPr()
        lang = OxmlElement("w:lang")
        lang.set(qn("w:val"), "pt-BR")
        r_pr.append(lang)

    @staticmethod
    def _add_field(paragraph, field: str) -> None:
        run = paragraph.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = field
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.append(begin)
        run._r.append(instr)
        run._r.append(end)

    # ------------------------------------------------------------------ blocks
    def h(self, text: str, level: int = 1) -> None:
        self.doc.add_heading(text, level=level)

    def p(self, text: str, *, bold: bool = False, italic: bool = False, size: float | None = None) -> None:
        paragraph = self.doc.add_paragraph()
        run = paragraph.add_run(text)
        run.bold = bold
        run.italic = italic
        if size is not None:
            run.font.size = Pt(size)

    def bullet(self, items: list[str]) -> None:
        for item in items:
            self.doc.add_paragraph(item, style="List Bullet")

    def numbered(self, items: list[str]) -> None:
        for item in items:
            self.doc.add_paragraph(item, style="List Number")

    def table(
        self,
        headers: list[str],
        rows: list[list[object]],
        *,
        widths: list[float] | None = None,
        font_size: float = 8.5,
    ) -> None:
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        tbl_header = OxmlElement("w:tblHeader")
        tbl_header.set(qn("w:val"), "true")
        tr_pr.append(tbl_header)
        hdr = table.rows[0].cells
        for i, header in enumerate(headers):
            hdr[i].text = str(header)
            for paragraph in hdr[i].paragraphs:
                for run in paragraph.runs:
                    run.bold = True
                    run.font.size = Pt(font_size)
        for row in rows:
            cells = table.add_row().cells
            for i, value in enumerate(row):
                cells[i].text = str(value)
                for paragraph in cells[i].paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(font_size)
        if widths:
            for row in table.rows:
                for i, width in enumerate(widths):
                    row.cells[i].width = Cm(width)
        self.doc.add_paragraph()

    def code(self, text: str) -> None:
        table = self.doc.add_table(rows=1, cols=1)
        table.style = "Table Grid"
        cell = table.rows[0].cells[0]
        cell.text = ""
        paragraph = cell.paragraphs[0]
        run = paragraph.add_run(text)
        run.font.name = "Consolas"
        run.font.size = Pt(8.2)
        run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
        self._shade(cell, "F1F5F9")
        self.doc.add_paragraph()

    @staticmethod
    def _shade(cell, hex_fill: str) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), hex_fill)
        tc_pr.append(shd)

    def callout(self, title: str, text: str) -> None:
        table = self.doc.add_table(rows=1, cols=1)
        table.style = "Table Grid"
        cell = table.rows[0].cells[0]
        cell.text = ""
        paragraph = cell.paragraphs[0]
        run = paragraph.add_run(title + ": ")
        run.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = TEAL
        run = paragraph.add_run(text)
        run.font.size = Pt(9.5)
        self._shade(cell, "E6F4F7")
        self.doc.add_paragraph()

    def figure(self, path: Path, caption: str, width_cm: float = 15.5) -> None:
        if not path.exists():
            return
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        shape = paragraph.add_run().add_picture(str(path), width=Cm(width_cm))
        shape._inline.docPr.set("descr", caption)
        shape._inline.docPr.set("title", caption)
        caption_paragraph = self.doc.add_paragraph()
        caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = caption_paragraph.add_run(caption)
        run.italic = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = GREY

    def page_break(self) -> None:
        self.doc.add_page_break()

    def toc(self) -> None:
        paragraph = self.doc.add_paragraph()
        run = paragraph.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = 'TOC \\o "1-3" \\h \\z \\u'
        separate = OxmlElement("w:fldChar")
        separate.set(qn("w:fldCharType"), "separate")
        text = OxmlElement("w:t")
        text.text = "Atualize o sumário no Word/LibreOffice: Ctrl+A e F9."
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.append(begin)
        run._r.append(instr)
        run._r.append(separate)
        run._r.append(text)
        run._r.append(end)

    def save(self) -> None:
        OUT.parent.mkdir(exist_ok=True)
        self.doc.save(OUT)


def build() -> None:
    manifest, _evaluation = load_demo()
    metrics = manifest["metrics"]
    per_class = metrics["precision_recall_f1"]["per_class"]
    b = Builder()

    # ------------------------------------------------------------------ cover
    title = b.doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("TDE — Rede Neural aplicada a acidentes em rodovias federais")
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = TEAL

    subtitle = b.doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Documento técnico completo")
    run.bold = True
    run.font.size = Pt(16)

    b.p("")
    b.p("Uma MLP implementada do zero em NumPy aplicada ao DATATRAN 2024", bold=True, size=13)
    b.p("")
    b.p(f"Integrantes: {IDENTITY}")
    b.p(f"Professor: {PROFESSOR}")
    b.p(f"Curso / Instituição / Semestre: {COURSE}")
    b.p("Dataset: Polícia Rodoviária Federal — DATATRAN 2024")
    b.p("Aplicação: http://localhost:3000 · API: http://localhost:8000/api/docs")
    b.p("Versão 1.0 · 2026-11-22")
    b.p("")
    b.callout(
        "Aviso",
        "Este é um protótipo acadêmico. O modelo estima probabilidades a partir de registros históricos e não deve ser usado para decisões reais de segurança viária.",
    )
    b.page_break()

    # ------------------------------------------------------------------ summary
    b.h("Resumo executivo", 1)
    b.p(
        "Este trabalho investiga se uma Rede Neural Multicamadas (MLP), implementada do zero em NumPy, "
        "consegue estimar a probabilidade de vítima fatal em acidentes registrados pela Polícia Rodoviária "
        "Federal em 2024. A base DATATRAN contém 73.202 ocorrências e 30 colunas; após remover o único "
        "registro com alvo indefinido, 73.201 exemplos foram usados. A classe fatal representa 7,1% do total, "
        "o que torna a acurácia uma métrica insuficiente e exige F1, ROC-AUC, PR-AUC, log-loss, Brier e calibração."
    )
    b.p(
        "O pipeline remove colunas de vazamento, deriva features temporais, agrupa categorias raras em "
        "__OUTROS__, faz split estratificado 60/20/20 e ajusta o preprocessor somente no treino. A rede padrão "
        "tem uma camada oculta ReLU e saída softmax, treinada com cross-entropy ponderada, Adam, gradient clipping "
        "e early stopping. Forward, loss, backpropagation, otimizadores e métricas foram implementados no projeto, "
        "sem frameworks de aprendizado profundo."
    )
    b.p(
        "O resultado é deliberadamente apresentado com honestidade: a acurácia do modelo é inferior ao baseline "
        "majoritário, mas o modelo recupera parte dos casos fatais, o que o baseline não faz. O teto de desempenho "
        "é limitado pela ausência de variáveis como velocidade, cinto, tipo de veículo e tempo de socorro."
    )
    b.table(
        ["Indicador", "Run Demo (3.000 amostras)", "Notebook (8.000 amostras)"],
        [
            ["Features", "92", "110 (binário) · 112 (3 classes)"],
            ["Arquitetura", "92 → 24 ReLU → 2", "110/112 → 32 ReLU → 2/3"],
            ["Acurácia", "0,7917", "0,7788"],
            ["F1 macro", "0,5469", "0,5910"],
            ["F1 fatal", "0,2138", "0,3140"],
            ["ROC-AUC", "0,6747", "0,8001"],
            ["PR-AUC", "0,1483", "0,2989"],
            ["Log-loss", "0,4779", "0,5035"],
            ["ECE", "0,0517", "0,0552"],
        ],
        widths=[4.2, 5.4, 5.4],
    )
    b.callout(
        "Como ler os números",
        "O Demo é o run operacional usado na aplicação; o notebook é o experimento acadêmico com mais amostras. "
        "Os dois são treinos distintos e não devem ser misturados. O documento indica a fonte de cada tabela.",
    )
    b.p(
        "O projeto também entrega uma aplicação completa: API FastAPI com treino assíncrono e SSE, PostgreSQL, "
        "frontend Next.js com dashboard, formulário de hiperparâmetros, análise de resultados, comparação e "
        "simulador, além de Docker Compose com um comando de subida. O notebook executado, os testes e os "
        "artefatos tornam o trabalho reproduzível."
    )
    b.page_break()

    b.h("Sumário", 1)
    b.toc()
    b.p(
        "Convenções editoriais: as figuras recebem numeração sequencial e são listadas no Apêndice I; "
        "as tabelas são identificadas pelo título da seção e pelo contexto imediato; trechos de código "
        "aparecem em fonte monoespaçada; os números do run Demo e do notebook são sempre identificados pela fonte."
    )
    b.page_break()

    # ------------------------------------------------------------------ 1
    b.h("1. Contexto, problema e objetivos", 1)
    b.h("1.1 Motivação", 2)
    b.p(
        "Acidentes de trânsito são uma das principais causas externas de morte no Brasil. A PRF registra "
        "ocorrências em rodovias federais e publica os dados abertos do DATATRAN. A gravidade não é distribuída "
        "de forma uniforme: a maioria dos acidentes tem feridos, uma parte menor não tem vítimas e uma minoria "
        "tem vítimas fatais. Prever essa minoria é o desafio central."
    )
    b.p(
        "A motivação acadêmica é dupla. Primeiro, aplicar os conceitos de neurônio, pesos, bias, ativação, loss, "
        "feedforward, backpropagation, épocas e testes em um problema real. Segundo, discutir por que um modelo "
        "com bom desempenho aparente pode ser inútil se a métrica não corresponder ao custo social do erro."
    )
    b.h("1.2 Pergunta e objetivos", 2)
    b.p(
        "Pergunta: é possível estimar a probabilidade de vítima fatal a partir de informações disponíveis no "
        "cenário do acidente, usando uma MLP treinada do zero em NumPy?"
    )
    b.bullet(
        [
            "Objetivo geral: construir, treinar, testar e analisar uma MLP para classificação de gravidade.",
            "Objetivo específico 1: comparar o alvo binário (fatal/não fatal) com o alvo de 3 classes.",
            "Objetivo específico 2: avaliar o modelo com métricas adequadas ao desbalanceamento.",
            "Objetivo aplicado: disponibilizar treino configurável, análise de resultados e simulador em uma aplicação web.",
        ]
    )
    b.h("1.3 Escopo e não escopo", 2)
    b.table(
        ["Dentro do escopo", "Fora do escopo"],
        [
            ["MLP tabular, dados de 2024, alvo binário e 3 classes", "Causalidade, previsão em tempo real e decisão operacional"],
            ["Treino/validação/teste e análise de métricas", "Garantia de desempenho em produção"],
            ["API, banco, frontend, Docker e notebook", "Aplicativo móvel, autenticação e multilíngue"],
            ["Simulador acadêmico de cenários", "Substituir laudo, perícia ou política pública"],
        ],
        widths=[8.0, 8.0],
    )
    b.h("1.4 Por que uma MLP?", 2)
    b.p(
        "O dataset é tabular, com variáveis numéricas e categóricas. Uma MLP é adequada porque aprende "
        "interações não lineares entre features sem exigir engenharia manual de todas as combinações. Redes "
        "convolucionais e recorrentes não são a escolha natural para uma tabela; transformadores seriam "
        "desproporcionais ao tamanho e à natureza do sinal. Além disso, a MLP permite implementar e explicar "
        "cada etapa matemática, que é o objetivo didático do TDE."
    )
    b.h("1.5 Contribuições do trabalho", 2)
    b.bullet(
        [
            "Núcleo de MLP em NumPy, com forward, loss, backward, otimizadores, dropout, L2 e early stopping.",
            "Pipeline de dados com prevenção explícita de vazamento e preprocessor serializável.",
            "Métricas implementadas em NumPy e validadas contra scikit-learn.",
            "API FastAPI com treino em background, SSE, persistência e simulador.",
            "Frontend Next.js com seis páginas e componentes de visualização.",
            "Docker Compose com banco, API, frontend e download automático do dataset.",
            "Notebook executado, documento, slides, capturas e pacote de entrega.",
        ]
    )
    b.page_break()

    # ------------------------------------------------------------------ 2
    b.h("2. Dataset DATATRAN 2024", 1)
    b.h("2.1 Identificação e fonte", 2)
    b.table(
        ["Item", "Descrição"],
        [
            ["Nome", "Acidentes em Rodovias Federais — DATATRAN (agrupados por ocorrência)"],
            ["Órgão", "Polícia Rodoviária Federal (PRF) — Diretoria de Operações"],
            ["Página oficial", "gov.br/prf — Dados Abertos da PRF"],
            ["Ano", "2024"],
            ["Tema", "Transporte, segurança viária e políticas públicas"],
            ["Granularidade", "1 linha = 1 ocorrência de acidente"],
            ["Dados pessoais", "Não; registros agregados por ocorrência"],
            ["Arquivo", "datatran2024.csv (21.365.616 bytes)"],
            ["SHA-256", "7d26e6f4528c2ca2636a8fea2c5bc8755a0ff6a182d82c238a8793b016e4366d"],
        ],
        widths=[3.6, 12.6],
    )
    b.p(
        "O link do CSV é obtido pela página oficial da PRF e validado por hash no script fetch_data.py. "
        "Como o arquivo é grande, ele não é versionado; o comando make fetch (ou o serviço data do Compose) "
        "baixa e valida a versão usada neste trabalho."
    )
    b.h("2.2 Volumetria e formato", 2)
    b.table(
        ["Indicador", "Valor"],
        [
            ["Registros no arquivo", "73.202"],
            ["Registros usados", "73.201 (1 linha com classificação NA)"],
            ["Colunas", "30"],
            ["UFs", "27"],
            ["Municípios", "1.834"],
            ["Causas de acidente", "69"],
            ["Tipos de acidente", "17"],
            ["Valores de tracado_via", "659 combinações; 12 termos principais"],
            ["Mortos no ano", "6.163"],
            ["Feridos no ano", "84.595"],
        ],
        widths=[6.2, 10.0],
    )
    b.p(
        "O arquivo usa codificação latin-1 (ISO-8859-1), separador ponto e vírgula e vírgula decimal em km, "
        "latitude e longitude. Abrir como UTF-8 corrompe acentos e cedilhas. A leitura correta é feita por "
        "pandas.read_csv(..., sep=';', encoding='latin-1', decimal=',') no módulo nn/data.py."
    )
    b.h("2.3 Variável-alvo", 2)
    b.table(
        ["Alvo", "Classes", "Contagem", "Uso"],
        [
            ["fatal_binario", "0 sem vítima fatal · 1 com vítima fatal", "67.976 / 5.225", "Padrão da aplicação"],
            ["gravidade_3_classes", "0 sem vítimas · 1 com feridos · 2 com fatais", "11.782 / 56.194 / 5.225", "Experimento comparativo"],
        ],
        widths=[3.6, 6.8, 3.6, 3.0],
    )
    b.p(
        "A linha com classificacao_acidente = 'NA' é descartada. No alvo binário, a classe positiva é a que "
        "importa socialmente; no alvo de 3 classes, a classe 2 é a fatal. O desbalanceamento é o fato central "
        "do problema: 5.225 casos fatais contra 67.976 não fatais."
    )
    b.h("2.4 Dicionário resumido das variáveis", 2)
    b.p(
        "O dicionário completo, com as 30 colunas, está no Apêndice B. No corpo, vale destacar os grupos usados "
        "pelo modelo e as colunas excluídas."
    )
    b.table(
        ["Grupo", "Colunas", "Papel"],
        [
            ["Localização", "uf, br, km", "Contexto geográfico e posição na rodovia"],
            ["Tempo", "dia_semana, horario", "Rotina, iluminação e fins de semana"],
            ["Via", "tipo_pista, tracado_via, uso_solo, sentido_via", "Geometria e ambiente viário"],
            ["Circunstância", "causa_acidente, tipo_acidente, fase_dia, condicao_metereologica", "Dinâmica e clima"],
            ["Frota", "veiculos", "Número de veículos envolvidos"],
            ["Regional (opcional)", "regional, delegacia, uop", "Alta cardinalidade administrativa"],
        ],
        widths=[3.6, 8.0, 5.0],
    )
    b.h("2.5 Qualidade, limpeza e vazamento de dados", 2)
    b.p(
        "A base tem id único, não possui duplicatas de linha e não tem valores ausentes nas colunas essenciais. "
        "O único alvo NA foi descartado. O ponto mais importante é o vazamento: várias colunas são consequência "
        "do acidente e não podem ser usadas como entrada, pois o modelo aprenderia a resposta."
    )
    b.table(
        ["Coluna(s) excluída(s)", "Motivo"],
        [
            ["classificacao_acidente", "Define o alvo"],
            ["mortos, feridos, feridos_leves, feridos_graves, ilesos, ignorados, pessoas", "São consequência pós-evento"],
            ["id", "Identificador sem poder preditivo"],
            ["data_inversa", "Ano único; data exata não generaliza"],
            ["municipio", "1.834 categorias; alta cardinalidade (opcional fora do padrão)"],
            ["latitude, longitude", "Geolocalização precisa e transformação espacial fora do escopo"],
            ["regional, delegacia, uop", "Alta cardinalidade administrativa; grupo opcional desligado"],
        ],
        widths=[6.8, 9.4],
    )
    b.callout(
        "Teste de vazamento",
        "Além da lista de colunas proibidas, o projeto tem teste automatizado que verifica a interseção entre features e LEAKAGE_COLUMNS. O preprocessor também rejeita colunas de vazamento ao ser carregado.",
    )
    b.h("2.6 Análise exploratória", 2)
    b.figure(
        FIGURES / "notebook_cell06_1.png",
        "Figura 1 — Distribuição da gravidade e do km. A classe com feridos domina; a distribuição do km tem cauda longa, tratada com log1p.",
        16.0,
    )
    b.figure(
        FIGURES / "notebook_cell06_2.png",
        "Figura 2 — Top 10 causas e top 10 tipos de acidente. A causa provável é atribuída no boletim, não medida.",
        16.0,
    )
    b.figure(
        FIGURES / "notebook_cell06_3.png",
        "Figura 3 — Acidentes por hora do dia. Há concentração no fim da tarde/início da noite.",
        14.5,
    )
    b.p(
        "A EDA mostra que a classe majoritária é 'Com Vítimas Feridas' (76,8%), seguida de 'Sem Vítimas' "
        "(16,1%) e 'Com Vítimas Fatais' (7,1%). As causas mais frequentes incluem reação tardia/ineficiente "
        "do condutor, ausência de reação e acesso à via sem observar os outros veículos. Os tipos mais comuns "
        "são colisão traseira, saída de leito carroçável e colisão transversal. O horário tem picos claros, "
        "o que justifica a codificação cíclica."
    )
    b.h("2.7 Limitações da base", 2)
    b.bullet(
        [
            "Não há velocidade no impacto, uso de cinto, tipo de veículo, condições do condutor ou tempo de socorro.",
            "A causa é provável e depende do preenchimento do boletim.",
            "Há subnotificação e diferenças de qualidade entre unidades da PRF.",
            "O recorte de 2024 não garante generalização para outros anos.",
            "A visão por ocorrência perde detalhes por pessoa.",
            "Consequência: o teto de desempenho é limitado; ROC-AUC entre ~0,67 e 0,80 é coerente.",
        ]
    )
    b.page_break()

    # ------------------------------------------------------------------ 3
    b.h("3. Preparação dos dados", 1)
    b.h("3.1 Visão geral do pipeline", 2)
    b.p(
        "O pipeline é implementado em backend/nn/data.py e executado tanto pelo notebook quanto pela API. "
        "A ordem é importante para evitar vazamento: primeiro split, depois fit do preprocessor no treino, "
        "depois transformação das três partições."
    )
    b.code(
        "CSV (latin-1, ';', decimal ',')\n"
        "  → load_raw: remove alvo NA\n"
        "  → build_target: binário ou 3 classes\n"
        "  → feature_frame: grupos, hora_sin/cos, is_fim_semana, tracado_principal\n"
        "  → split_indices: estratificado 60/20/20 (seed 42)\n"
        "  → fit_preprocessor(train): vocabulário, OUTROS, mediana, scaler\n"
        "  → transform(train/val/test): one-hot + escala, float32\n"
        "  → class_weights(train): pesos balanceados"
    )
    b.h("3.2 Leitura e limpeza", 2)
    b.p(
        "load_raw lê o arquivo com dtype para br e km, usa decimal=',' e descarta a linha cujo alvo é NaN. "
        "build_target converte mortos > 0 em 0/1 ou mapeia as três classificações para 0/1/2. target_mask "
        "serve para filtrar linhas sem alvo quando o DataFrame é passado diretamente."
    )
    b.h("3.3 Features e derivações", 2)
    b.table(
        ["Feature", "Origem", "Regra / motivo"],
        [
            ["br, km", "br, km", "Números; km e br recebem log1p"],
            ["hora_sin, hora_cos", "horario", "Codificação cíclica de 24 h; evita descontinuidade 23h→0h"],
            ["is_fim_semana", "dia_semana", "1 para sábado/domingo"],
            ["tracado_principal", "tracado_via", "Primeiro termo antes de ';' (ex.: 'Curva;Declive' → 'Curva')"],
            ["veiculos", "veiculos", "Contagem; log1p opcional"],
            ["uf, dia_semana, tipo_pista, ...", "colunas categóricas", "One-hot com categorias raras em __OUTROS__"],
        ],
        widths=[4.0, 4.4, 7.6],
    )
    b.p(
        "A codificação cíclica é importante: 23h e 0h são próximos no tempo, mas distantes numericamente. "
        "O traçado original tem 659 combinações; reduzir ao primeiro termo diminui a cardinalidade para 12 "
        "sem perder a geometria dominante. O log1p comprime caudas longas de km/br/veículos e só é aplicado "
        "a colunas não negativas."
    )
    b.h("3.4 Split estratificado", 2)
    b.p(
        "O split é feito por classe, com seed 42, garantindo aproximadamente 60% treino, 20% validação e 20% "
        "teste em cada classe. Classes com menos de 3 exemplos vão para o treino; com 3 ou mais, cada partição "
        "recebe pelo menos 1. A amostragem opcional max_rows também é estratificada."
    )
    b.table(
        ["Configuração", "Treino", "Validação", "Teste", "Total"],
        [
            ["Demo (3.000)", "1.800", "600", "600", "3.000"],
            ["Notebook (8.000)", "4.800", "1.600", "1.600", "8.000"],
            ["Dataset completo", "43.921", "14.640", "14.640", "73.201"],
        ],
        widths=[4.6, 3.0, 3.0, 3.0, 2.8],
    )
    b.h("3.5 Preprocessor", 2)
    b.p(
        "O Preprocessor é uma dataclass congelada que guarda vocabulário, imputação, centro e escala. "
        "fit_preprocessor aprende somente no treino: categorias com contagem abaixo de rare_min_count são "
        "substituídas por __OUTROS__; a mediana preenche numéricos ausentes; o scaler pode ser standard "
        "(média 0, desvio 1), minmax (0–1) ou none. O objeto tem to_json/from_json com round-trip exato e "
        "schema_hash estável."
    )
    b.callout(
        "Por que __OUTROS__ sempre existe",
        "Além de agrupar categorias raras, __OUTROS__ absorve categorias nunca vistas no treino. Isso é essencial no simulador: uma UF ou causa nova não quebra a transformação.",
    )
    b.h("3.6 Pesos de classe", 2)
    b.p(
        "A loss ponderada usa pesos inversamente proporcionais à frequência: w_k = n / (k × bincount(y)_k). "
        "No binário do notebook, os pesos foram aproximadamente 0,5385 para a classe 0 e 6,9971 para a classe 1. "
        "Assim, um erro em um caso fatal pesa cerca de 13 vezes mais que um erro na classe majoritária."
    )
    b.code(
        "counts = np.bincount(y, minlength=k)\n"
        "weights = np.ones(k)\n"
        "weights[counts > 0] = len(y) / (k * counts[counts > 0])"
    )
    b.h("3.7 Dataset final", 2)
    b.table(
        ["Item", "Demo", "Notebook binário", "Notebook 3 classes"],
        [
            ["Amostras usadas", "3.000", "8.000", "8.000"],
            ["Features", "92", "110", "112"],
            ["Numéricas", "6", "6", "6"],
            ["Colunas categóricas", "10", "10", "10"],
            ["Schema hash", "—", "a372163e2a4c565e", "—"],
            ["Matrizes", "float32", "float32", "float32"],
        ],
        widths=[4.2, 3.6, 4.2, 4.2],
    )
    b.p(
        "O número de features muda com max_rows e rare_min_count porque o vocabulário é aprendido no treino. "
        "O split de 3.000/8.000 mantém a proporção das classes, mas perde categorias raras; no dataset completo, "
        "o vocabulário é maior. Isso explica por que o Demo tem 92 features e o notebook 110/112."
    )
    b.h("3.8 Invariantes e testes", 2)
    b.bullet(
        [
            "Nenhuma estatística de validação/teste entra no fit do preprocessor.",
            "A ordem das colunas de transform é idêntica à do treino (schema_hash).",
            "transform de uma linha isolada é igual à linha correspondente da matriz.",
            "Split mantém proporção das classes com tolerância de ±1%.",
            "Nenhuma coluna de LEAKAGE_COLUMNS aparece nas features.",
            "Round-trip JSON do preprocessor preserva vocabulário e transformação.",
        ]
    )
    b.page_break()

    # ------------------------------------------------------------------ 4
    b.h("4. Fundamentos e implementação da MLP", 1)
    b.h("4.1 Neurônio, pesos, bias e ativação", 2)
    b.p(
        "Um neurônio calcula uma combinação linear das entradas e aplica uma não linearidade: "
        "z = Σ w_i x_i + b; a = f(z). Os pesos w medem a importância de cada entrada; o bias b desloca a "
        "fronteira de decisão; f é a função de ativação. Sem ativação, várias camadas colapsariam em uma "
        "transformação linear."
    )
    b.p(
        "A rede inteira é uma composição de camadas. Na camada l: Z_l = A_{l-1} W_l + b_l; A_l = f(Z_l). "
        "A última camada usa softmax para produzir probabilidades que somam 1."
    )
    b.h("4.2 Arquitetura usada", 2)
    b.table(
        ["Elemento", "Demo", "Notebook"],
        [
            ["Entrada", "92 features", "110 (binário) / 112 (3 classes)"],
            ["Camadas ocultas", "1", "1"],
            ["Neurônios ocultos", "24", "32"],
            ["Ativação", "ReLU", "ReLU"],
            ["Saída", "2 (softmax)", "2 ou 3 (softmax)"],
            ["Loss", "weighted_ce", "weighted_ce"],
            ["Otimizador", "Adam", "Adam"],
            ["Learning rate", "0,001", "0,001"],
            ["Batch", "256", "256"],
            ["Épocas", "15 (patience 5)", "40 (binário) / 30 (3 classes)"],
        ],
        widths=[4.0, 5.6, 6.6],
    )
    b.h("4.3 Inicialização", 2)
    b.p(
        "Os pesos não podem começar todos em zero, pois neurônios aprenderiam a mesma coisa. O projeto oferece "
        "He normal (std = sqrt(2/fan_in)), recomendada para ReLU; Xavier normal (std = sqrt(1/fan_in)), "
        "recomendada para tanh/sigmoid; e normal com desvio 0,01. Os biases começam em zero."
    )
    b.h("4.4 Forward pass e ativações", 2)
    b.code(
        "A = X\n"
        "for i, (W, b) in enumerate(zip(self.weights, self.biases)):\n"
        "    Z = A @ W + b\n"
        "    if i < len(self.weights) - 1:\n"
        "        A = activation(Z)\n"
        "        if training and dropout > 0:\n"
        "            mask = (rng.random(A.shape) < keep_prob) / keep_prob\n"
        "            A = A * mask\n"
        "    else:\n"
        "        A = softmax(Z)\n"
        "cache.append({...})"
    )
    b.p(
        "As ativações implementadas são ReLU (max(0,z)), tanh, sigmoid (com versão estável) e leaky ReLU "
        "(z se z>0, senão 0,01z). A softmax é calculada como exp(z - max(z)) / Σ exp(z - max(z)), evitando "
        "overflow. O cache guarda A_prev, Z, A e a máscara de dropout para o backward."
    )
    b.h("4.5 Funções de perda", 2)
    b.p(
        "A saída é uma distribuição de probabilidades. A cross-entropy compara a probabilidade atribuída à "
        "classe correta com 1. Para uma amostra i com classe y_i: L_i = -log(p_{i,y_i}). A média é "
        "L = (1/N) Σ L_i."
    )
    b.p(
        "A weighted cross-entropy multiplica cada amostra pelo peso da sua classe: L = Σ w_{y_i} L_i / Σ w_{y_i}. "
        "A focal loss adiciona o fator (1 - p_t)^γ, reduzindo o peso de exemplos fáceis e concentrando o "
        "aprendizado nos difíceis. O projeto oferece ce, weighted_ce e focal; o padrão é weighted_ce porque "
        "o dataset é desbalanceado e a classe fatal é o foco."
    )
    b.callout(
        "Justificativa da loss",
        "A weighted cross-entropy é a escolha principal porque é estável, interpretável e permite compensar a raridade dos casos fatais sem inventar amostras. A focal é uma alternativa experimental; a CE simples serve de controle.",
    )
    b.h("4.6 Backpropagation e regra da cadeia", 2)
    b.p(
        "O gradiente da loss em relação às logits da última camada tem forma fechada: dL/dZ = p - y, "
        "ponderado pelos pesos de classe quando aplicável. Não é necessário dividir por p, o que evita "
        "instabilidade numérica. Para as camadas anteriores, aplica-se a regra da cadeia:"
    )
    b.code(
        "dZ_l = (dA_l * f'(Z_l))\n"
        "dW_l = A_{l-1}.T @ dZ_l\n"
        "db_l = sum(dZ_l, axis=0)\n"
        "dA_{l-1} = dZ_l @ W_l.T"
    )
    b.p(
        "As derivadas usadas são: ReLU 1 se z>0 e 0 caso contrário; tanh 1 - a²; sigmoid a(1-a); leaky ReLU "
        "1 ou 0,01. O L2 entra como +λW em dW (nunca no bias), e o dropout multiplica dA pela mesma máscara "
        "usada no forward."
    )
    b.h("4.7 Otimizadores", 2)
    b.p(
        "SGD atualiza θ = θ - lr·g. Momentum acumula uma média exponencial do gradiente: v = βv + g; "
        "θ = θ - lr·v. Adam mantém primeiro e segundo momentos: m = β1m + (1-β1)g; v = β2v + (1-β2)g²; "
        "corrige o viés (m/(1-β1^t), v/(1-β2^t)) e atualiza θ = θ - lr·m̂/(√v̂ + ε). AdamW aplica o weight "
        "decay de forma desacoplada: θ = θ - lr·λθ antes do passo adaptativo."
    )
    b.p(
        "O gradiente é clipado por norma global: se ||g|| > grad_clip, todos os componentes são multiplicados "
        "por grad_clip/||g||. Isso evita explosão do gradiente, especialmente no início."
    )
    b.h("4.8 Learning rate e épocas", 2)
    b.p(
        "O projeto suporta lr constante, step (multiplica por decay_rate a cada decay_every épocas) e cosine "
        "(decaimento suave até um mínimo). A época é uma passagem completa pelo treino; o mini-batch é um "
        "subconjunto embaralhado. O histórico registra loss_train, loss_val, acc_train, acc_val, f1_val, "
        "grad_norm, lr e seconds por época."
    )
    b.h("4.9 Early stopping e checkpoint", 2)
    b.p(
        "Ao fim de cada época, a loss de validação é comparada com a melhor até então. Se não melhora por "
        "patience épocas, o treino para. O melhor conjunto de pesos/biases é restaurado, garantindo que o "
        "modelo avaliado no teste não seja o último epoch, mas o melhor checkpoint. O método stop() permite "
        "cancelamento cooperativo pela API."
    )
    b.h("4.10 Predição, persistência e reprodutibilidade", 2)
    b.p(
        "predict_proba retorna a matriz de probabilidades; predict usa threshold 0,5 no binário e argmax no "
        "multiclasse. save/load usam NPZ com config JSON, pesos, biases e class_weights. A seed é passada "
        "para np.random.default_rng, nunca para o estado global; dois treinos com a mesma seed produzem "
        "métricas idênticas. Pequenas diferenças de BLAS podem ocorrer (~1e-7), por isso os testes usam "
        "tolerância."
    )
    b.h("4.11 Mapa requisito do professor → implementação", 2)
    b.table(
        ["Requisito do guia", "Onde está atendido"],
        [
            ["__init__: entradas, camadas, neurônios, saídas, pesos, bias", "NnModel.__init__"],
            ["forward / feedforward", "NnModel.forward"],
            ["loss e justificativa", "NnModel.loss + seção 4.5"],
            ["backpropagation", "NnModel.backward"],
            ["derivada, regra da cadeia, gradiente, learning rate", "seções 4.6–4.8 e comentários do model.py"],
            ["fit / épocas / atualização", "NnModel.fit + step"],
            ["arquitetura explícita", "seções 4.2 e 5.1"],
            ["hiperparâmetros justificados", "seção 5.2 e Apêndice C"],
            ["treinamento observável", "histórico + notebook §7 + painel SSE"],
            ["teste em dados não vistos", "seção 5.9 e métricas"],
            ["análise crítica", "capítulo 11"],
        ],
        widths=[8.6, 7.6],
    )
    b.page_break()

    # ------------------------------------------------------------------ 5
    b.h("5. Treinamento em detalhe", 1)
    b.h("5.1 Configuração usada", 2)
    b.table(
        ["Parâmetro", "Demo", "Notebook binário", "Notebook 3 classes"],
        [
            ["max_rows", "3.000", "8.000", "8.000"],
            ["target", "fatal_binario", "fatal_binario", "gravidade_3_classes"],
            ["hidden_layers", "1", "1", "1"],
            ["neurons", "[24]", "[32]", "[32]"],
            ["activation", "relu", "relu", "relu"],
            ["init", "he", "he", "he"],
            ["dropout / l2", "0 / 0", "0 / 0", "0 / 0"],
            ["loss", "weighted_ce", "weighted_ce", "weighted_ce"],
            ["optimizer / lr", "adam / 1e-3", "adam / 1e-3", "adam / 1e-3"],
            ["batch_size", "256", "256", "256"],
            ["epochs / patience", "15 / 5", "40 / 8", "30 / 8"],
            ["grad_clip", "5,0", "5,0", "5,0"],
            ["threshold", "0,5", "0,5", "0,5"],
            ["seed", "42", "42", "42"],
        ],
        widths=[4.2, 3.8, 4.0, 4.2],
    )
    b.h("5.2 Justificativa dos hiperparâmetros", 2)
    b.bullet(
        [
            "Uma camada oculta é suficiente para capturar não linearidades básicas sem aumentar muito a variância; o sinal disponível é limitado.",
            "Poucos neurônios (24–32) reduzem overfitting e mantêm o modelo interpretável; redes maiores não criam informação ausente.",
            "ReLU + He é a combinação padrão estável para redes pequenas; tanh/Xavier é alternativa para saturação suave.",
            "weighted_ce compensa a classe fatal rara e evita que o modelo ignore a classe de interesse.",
            "Adam com lr=1e-3 converge rápido e é robusto a escalas; não exige tuning agressivo em um TDE.",
            "Batch 256 equilibra ruído e velocidade; o preset rápido usa full batch para demos.",
            "Early stopping com patience 5–8 evita overfitting e reduz tempo; o melhor checkpoint é restaurado.",
            "Gradient clipping em 5 protege contra explosão no início do treino.",
            "Threshold 0,5 é o padrão; a varredura mostra que o ponto ótimo de F1 pode ser diferente.",
        ]
    )
    b.h("5.3 Protocolo de treinamento", 2)
    b.numbered(
        [
            "Carregar e limpar o CSV, construir o alvo.",
            "Separar treino/validação/teste de forma estratificada.",
            "Ajustar o preprocessor somente no treino e transformar as três partições.",
            "Calcular pesos de classe no treino.",
            "Inicializar a rede com He/Xavier e seed fixa.",
            "Para cada época: embaralhar, iterar mini-batches, forward, loss, backward, clipping, step.",
            "Ao fim da época: medir loss/acurácia/F1 em treino e validação.",
            "Guardar o melhor checkpoint e aplicar early stopping.",
            "Restaurar o melhor checkpoint.",
            "Avaliar uma única vez no teste e gerar métricas/artefatos.",
        ]
    )
    b.h("5.4 Evolução do treinamento", 2)
    b.figure(
        FIGURES / "notebook_cell14_1.png",
        "Figura 4 — Curvas do notebook: loss de treino e validação, acurácia e F1 de validação. A linha verde marca o melhor checkpoint (época 14).",
        16.0,
    )
    b.p(
        "A loss de treino cai de ~0,68 para ~0,40. A loss de validação cai até ~0,54 e depois estabiliza/sobe "
        "levemente, indicando o início do overfitting. O early stopping interrompe na época 14 e restaura o "
        "melhor ponto. A acurácia de validação fica em ~0,78–0,80; o F1 de validação fica em ~0,60. "
        "A distância treino–validação é o sinal de que o modelo começa a memorizar."
    )
    b.h("5.5 Verificação de gradientes", 2)
    b.p(
        "Além do treino, o projeto verifica a matemática. Para cada ativação e cada loss, o gradiente analítico "
        "é comparado ao gradiente numérico por diferenças finitas: (L(θ+ε) - L(θ-ε))/(2ε). O erro relativo "
        "máximo deve ficar abaixo de 1e-4. Esse teste pega erros de sinal, transposição e esquecimento de "
        "máscara de dropout. Os testes cobrem ReLU, tanh, sigmoid e leaky ReLU com ce, weighted_ce e focal."
    )
    b.h("5.6 Sanidade com XOR", 2)
    b.p(
        "XOR é o problema clássico que uma rede linear não resolve. A mesma classe é treinada com SGD, "
        "Momentum, Adam e AdamW; todos devem convergir para loss < 0,05 e acertar as quatro combinações. "
        "Isso valida forward, backward, ativação não linear e atualização de pesos antes de aplicar ao dataset."
    )
    b.h("5.7 Reprodutibilidade", 2)
    b.p(
        "Dois modelos criados com a mesma seed e os mesmos dados produzem os mesmos pesos e as mesmas "
        "métricas. O split usa default_rng(seed); o embaralhamento de mini-batches usa uma RNG própria; a "
        "inicialização usa a RNG do modelo. O teste de reprodutibilidade compara loss_train e loss_val época "
        "a época."
    )
    b.h("5.8 Overfitting, underfitting e leitura das curvas", 2)
    b.p(
        "Underfitting apareceria se treino e validação ficassem altos; não é o caso. Overfitting aparece quando "
        "a loss de treino continua caindo e a de validação sobe; é o que acontece após a época 14. A escolha de "
        "modelo pequeno e early stopping é uma resposta a esse comportamento. O teste é a medida final de "
        "generalização: não se deve escolher hiperparâmetros olhando o teste."
    )
    b.h("5.9 Resultados do run Demo", 2)
    b.table(
        ["Métrica", "Valor"],
        [
            ["Acurácia", br(metrics['accuracy'])],
            ["F1 macro", br(metrics['precision_recall_f1']['macro']['f1'])],
            ["F1 classe fatal", br(per_class[1]['f1'])],
            ["ROC-AUC", br(metrics['roc_auc'])],
            ["PR-AUC", br(metrics['pr_auc'])],
            ["Log-loss", br(metrics['log_loss'])],
            ["Brier", br(metrics['brier_score'])],
            ["ECE", br(metrics['ece'])],
        ],
        widths=[8.0, 6.0],
    )
    b.table(
        ["Classe", "Precisão", "Recall", "F1", "Suporte"],
        [
            ["sem_vitima_fatal", br(per_class[0]['precision']), br(per_class[0]['recall']), br(per_class[0]['f1']), per_class[0]["support"]],
            ["vitima_fatal", br(per_class[1]['precision']), br(per_class[1]['recall']), br(per_class[1]['f1']), per_class[1]["support"]],
        ],
        widths=[5.0, 3.4, 3.2, 3.2, 3.0],
    )
    b.p(
        "A acurácia de 0,7917 é menor que o baseline majoritário (~0,9287 no notebook), mas o modelo recupera "
        "39,5% dos fatais com precisão de 14,7%. O F1 fatal de 0,2138 mostra o trade-off. A matriz de confusão "
        "do Demo é [[458, 99], [26, 17]]: 26 falsos negativos e 99 falsos positivos."
    )
    b.h("5.10 Análise de erros", 2)
    b.figure(
        FIGURES / "notebook_cell17_1.png",
        "Figura 5 — Matriz de confusão do notebook (teste): 33 falsos negativos e 321 falsos positivos.",
        10.5,
    )
    b.p(
        "O falso negativo é o erro mais caro socialmente: um acidente fatal classificado como não fatal. "
        "O falso positivo gera alarme desnecessário, mas é menos grave no contexto de triagem. Por isso, "
        "além da acurácia, observamos recall e F1 da classe fatal. O threshold pode ser reduzido para aumentar "
        "o recall, aceitando mais falsos positivos; essa escolha é política e deve ser explícita."
    )
    b.figure(
        FIGURES / "notebook_cell17_2.png",
        "Figura 6 — ROC, PR e varredura de limiar. A AUC mede separação; o ponto de operação escolhe o trade-off.",
        16.0,
    )
    b.h("5.11 Threshold e calibração", 2)
    b.p(
        "A varredura de limiar mostra precisão, recall e F1 em função do ponto de corte. No binário, baixar "
        "o threshold aumenta o recall e reduz a precisão. O threshold 0,5 não é necessariamente o melhor para "
        "F1; a escolha depende do custo relativo dos erros. A calibração (ECE ~0,05) indica que as probabilidades "
        "não estão grosseiramente descalibradas, mas a curva mostra regiões de subconfiança."
    )
    b.figure(
        FIGURES / "notebook_cell17_3.png",
        "Figura 7 — Histograma de probabilidades e curva de calibração (ECE = 0,055 no notebook).",
        16.0,
    )
    b.h("5.12 Binário × 3 classes", 2)
    b.table(
        ["Métrica", "Binário", "3 classes"],
        [
            ["Acurácia", "0,7788", "0,5931"],
            ["F1 macro", "0,5910", "0,4817"],
            ["ROC-AUC", "0,8001", "0,7494"],
            ["PR-AUC", "0,2989", "0,5385"],
            ["Log-loss", "0,5035", "0,8857"],
        ],
        widths=[5.0, 4.0, 4.0],
    )
    b.p(
        "O alvo de 3 classes é mais difícil: a acurácia e o F1 macro caem, e a log-loss sobe. O PR-AUC macro "
        "de 3 classes é maior porque é uma média One-vs-Rest de três curvas, não porque a tarefa seja mais fácil. "
        "Para triagem de letalidade, o binário é mais direto e interpretável; o 3 classes é útil para distinguir "
        "sem vítimas de feridos."
    )
    b.h("5.13 Custo computacional", 2)
    b.p(
        "O run Demo treina 3.000 amostras em ~0,1 s; o notebook treina 8.000 em ~0,4 s por modelo no ambiente "
        "usado. O dataset completo leva mais tempo, mas continua viável em CPU. O gargalo é a multiplicação de "
        "matrizes e o número de épocas, não a complexidade da rede. O cache de dataset da API evita refazer o "
        "pipeline em runs consecutivos com a mesma configuração."
    )
    b.h("5.14 O que funcionou e o que não funcionou", 2)
    b.table(
        ["Funcionou", "Não funcionou / limitação"],
        [
            ["Pipeline anti-leakage e split estratificado", "Base sem variáveis decisivas de letalidade"],
            ["Weighted CE para classe rara", "Precisão baixa na classe fatal"],
            ["Early stopping e modelo pequeno", "Teto de ROC-AUC ~0,8"],
            ["Métricas além da acurácia", "Acurácia isolada enganosa"],
            ["SSE e artefatos para reprodutibilidade", "Treino completo ainda depende de CPU"],
        ],
        widths=[8.2, 8.0],
    )
    b.page_break()

    # ------------------------------------------------------------------ 6
    b.h("6. Métricas e avaliação", 1)
    b.p(
        "Todas as métricas são implementadas em NumPy em backend/nn/metrics.py e validadas contra scikit-learn. "
        "Isso permite usar o mesmo código no notebook, na API e nos testes, sem dependência de framework no runtime."
    )
    b.table(
        ["Métrica", "O que mede", "Por que importa aqui"],
        [
            ["Matriz de confusão", "TP, TN, FP, FN por classe", "Mostra o custo real dos erros"],
            ["Acurácia", "Acertos / total", "Enganosa com 7,1% de fatais"],
            ["Precisão", "TP / (TP+FP)", "Dos previstos fatais, quantos eram"],
            ["Recall", "TP / (TP+FN)", "Dos fatais, quantos foram encontrados"],
            ["F1", "2PR/(P+R)", "Equilíbrio entre precisão e recall"],
            ["F1 macro", "Média simples por classe", "Trata classes igualmente"],
            ["F1 weighted", "Média pelo suporte", "Reflete a distribuição"],
            ["ROC-AUC", "Separação em todos os thresholds", "Ranking global"],
            ["PR-AUC", "Área precisão×recall", "Melhor para classe rara"],
            ["Log-loss", "Qualidade das probabilidades", "Penaliza confiança errada"],
            ["Brier", "Erro quadrático das probabilidades", "Calibração e acurácia"],
            ["ECE", "Erro de calibração em bins", "Probabilidade é confiável?"],
        ],
        widths=[3.8, 6.0, 6.0],
    )
    b.p(
        "ROC-AUC é calculada pela estatística U de Mann-Whitney, com postos médios para empates. PR-AUC é "
        "integrada por trapézios. O ECE divide as confianças em 10 bins e compara acurácia observada com "
        "confiança média. A varredura de limiar gera 50 pontos entre 0,05 e 0,95."
    )
    b.callout(
        "Paridade com scikit-learn",
        "Os testes exigem diferença < 1e-9 para acurácia, matriz, P/R/F1, log-loss e Brier, e < 1e-6 para ROC-AUC. Isso dá confiança de que as fórmulas implementadas estão corretas.",
    )
    b.page_break()

    # ------------------------------------------------------------------ 7
    b.h("7. Arquitetura de software", 1)
    b.h("7.1 Mapa do repositório", 2)
    b.table(
        ["Caminho", "Responsabilidade"],
        [
            ["backend/nn", "Núcleo NumPy: config, data, model, metrics, export, utils"],
            ["backend/api", "FastAPI, schemas, DB, models, store, trainer, Dockerfile"],
            ["backend/scripts", "fetch_data, seed_demo, export_openapi, build_notebook, build_deliverables, package_delivery"],
            ["backend/notebooks", "Notebook executado do TDE"],
            ["backend/tests", "Testes unitários e integração Postgres"],
            ["frontend/app", "Rotas Next.js e proxy de API"],
            ["frontend/components", "Layout, formulários, gráficos, treino, resultados e simulador"],
            ["frontend/lib", "Cliente API, validação Zod, presets, formatadores, tipos OpenAPI"],
            ["frontend/hooks", "useRunStream (SSE)"],
            ["docs", "Dataset, documento, slides, prints, backup, roteiro"],
            [".specs", "Especificações e planejamento (local)"],
        ],
        widths=[5.2, 10.8],
    )
    b.h("7.2 Núcleo nn", 2)
    b.p(
        "config.py concentra DataConfig, ModelConfig, presets, validação e estimativa. data.py implementa "
        "carga, alvo, features, split, preprocessor, transform, pesos e Dataset. model.py implementa a MLP. "
        "metrics.py implementa avaliação. export.py serializa modelo/preprocessor e faz predição autocontida. "
        "utils.py concentra seed e caminhos."
    )
    b.h("7.3 API", 2)
    b.p(
        "schemas.py define os contratos Pydantic (RunCreate, EstimateRequest, PredictRequest, RunStatus). "
        "models.py define runs e run_epochs. db.py cria engine lazy, sessões e retry. store.py faz CRUD e "
        "serialização. trainer.py executa o treino em thread, com lock de 1 run, cache de dataset e artefatos. "
        "main.py expõe as rotas, SSE, meta, estimate, predict e lifespan."
    )
    b.h("7.4 Scripts", 2)
    b.bullet(
        [
            "fetch_data.py: baixa o ZIP do Drive, valida SHA-256, extrai e confere 73.202 linhas/30 colunas.",
            "seed_demo.py: treina um run pequeno e grava o Demo no Postgres e em artifacts.",
            "export_openapi.py: gera frontend/lib/openapi.json.",
            "build_notebook.py: gera o notebook a partir de células versionadas.",
            "build_deliverables.py: gera DOCX, PDF, PPTX, QR, roteiro e backup.",
            "package_delivery.py: cria o zip final sem dataset/venv/node_modules.",
        ]
    )
    b.h("7.5 Notebook", 2)
    b.p(
        "O notebook tem 27 células (13 de código) e cobre EDA, preparação, inspect.getsource(NnModel), "
        "arquitetura, treino, métricas, baseline, comparativo 3 classes, simulador, reprodutibilidade e análise "
        "crítica. Ele foi executado do início ao fim, com saídas visíveis."
    )
    b.h("7.6 Testes", 2)
    b.table(
        ["Camada", "Cobertura principal", "Quantidade"],
        [
            ["Backend unitário", "dados, modelo, métricas, export/paridade", "60 testes executados"],
            ["Backend integração", "run + SSE + predict + export com Postgres", "1 teste opcional"],
            ["Frontend Vitest", "format, Zod, presets, contraste, componente", "17 testes"],
            ["Frontend Playwright", "treinar, simulador, tema, responsivo", "5 fluxos"],
        ],
        widths=[4.4, 8.6, 3.4],
    )
    b.h("7.7 Fluxo de dados ponta a ponta", 2)
    b.code(
        "datatran2024.csv\n"
        "  → nn.data.prepare_dataset\n"
        "  → nn.model.NnModel.fit\n"
        "  → nn.metrics.calculate_all_metrics\n"
        "  → nn.export.export_model (model.json + weights.npz)\n"
        "  → api.store (runs/run_epochs + artifacts)\n"
        "  → Next.js (dashboard, resultados, simulador)"
    )
    b.page_break()

    # ------------------------------------------------------------------ 8
    b.h("8. API, banco e orquestração do treino", 1)
    b.h("8.1 Stack", 2)
    b.p(
        "A API usa FastAPI + Uvicorn, Pydantic v2, SQLAlchemy 2.0 e psycopg3 sobre PostgreSQL 16. O treino "
        "roda em background com um lock de processo; a interface acompanha por SSE. O banco guarda metadados "
        "e métricas; os arquivos grandes ficam em backend/artifacts."
    )
    b.h("8.2 Endpoints", 2)
    b.table(
        ["Método", "Rota", "Função"],
        [
            ["GET", "/api/health", "status e SELECT 1"],
            ["GET", "/api/meta", "grupos, categorias, alvos, defaults, presets e resumo"],
            ["GET", "/api/datasets/summary", "volumetria, balanceamento, nulos e top categorias"],
            ["POST", "/api/estimate", "tempo, n_train, n_features, passos e warnings"],
            ["POST", "/api/runs", "valida, cria run e agenda o worker"],
            ["GET", "/api/runs", "lista o histórico"],
            ["GET", "/api/runs/{id}", "detalhe do run"],
            ["POST", "/api/runs/{id}/cancel", "cancelamento cooperativo"],
            ["DELETE", "/api/runs/{id}", "remove run e artefatos"],
            ["GET", "/api/runs/{id}/stream", "SSE de progresso"],
            ["GET", "/api/runs/{id}/events", "alias do SSE"],
            ["GET", "/api/runs/{id}/export", "download de artefatos"],
            ["POST", "/api/predict", "inferência de uma linha + contribuições"],
        ],
        widths=[2.2, 6.4, 9.2],
    )
    b.h("8.3 Ciclo de vida do run", 2)
    b.p(
        "Ao criar, o run fica queued. O worker adquire o lock, marca running e começa o pipeline. A cada 10 "
        "épocas, grava run_epochs em lote e publica eventos SSE. No fim, calcula métricas no teste, grava "
        "artefatos e marca done. Falhas marcam failed com error; cancelamento marca canceled. O SSE emite "
        "status, epoch, done, failed e canceled; o frontend ignora status e só plota epochs."
    )
    b.h("8.4 SSE e o bug corrigido", 2)
    b.p(
        "O servidor envia primeiro um evento status e depois eventos epoch. A primeira versão do frontend "
        "tratava todo evento como época, chamava epoch.toString() em undefined e derrubava a página ao iniciar "
        "o treino. A correção separa os tipos, ignora status, fecha o EventSource em done/failed/canceled e "
        "protege LogConsole/RunProgress. O teste E2E de treino agora envia status + epoch + done para cobrir "
        "a regressão."
    )
    b.h("8.5 Artefatos por run", 2)
    b.table(
        ["Arquivo", "Conteúdo"],
        [
            ["run.json", "config, status, tempos, contagens, métricas"],
            ["evaluation.json", "matriz, P/R/F1, ROC/PR, calibração, histograma, sweep"],
            ["curves.json", "histórico por época"],
            ["preprocessor.json", "vocabulário, centros, escalas, schema"],
            ["model.json", "modelo autocontido"],
            ["weights.npz", "pesos e biases"],
            ["log.txt", "log textual por época"],
        ],
        widths=[4.2, 11.8],
    )
    b.h("8.6 Predição e contribuições", 2)
    b.p(
        "POST /api/predict carrega o model.json, reconstrói a DataConfig, aplica feature_frame e transform, "
        "executa o forward e devolve classe, probabilidades e contribuições. As contribuições são calculadas "
        "por perturbação: para cada campo bruto, o valor é substituído pelo baseline (numérico neutro ou "
        "primeira categoria) e a diferença de logit é medida. As seis maiores diferenças absolutas são "
        "retornadas. Isso explica o que puxou a probabilidade sem exigir SHAP."
    )
    b.h("8.7 Banco", 2)
    b.table(
        ["Tabela", "Campos principais"],
        [
            ["runs", "id, name, status, target, config JSONB, metrics JSONB, n_features, n_train/val/test, best_epoch, duration_s, timestamps, error"],
            ["run_epochs", "id, run_id, epoch, loss_train, loss_val, acc_train, acc_val, f1_val, lr, grad_norm, seconds"],
        ],
        widths=[3.4, 12.6],
    )
    b.h("8.8 Guardrails e erros", 2)
    b.bullet(
        [
            "Validação de DataConfig/ModelConfig com mensagens em pt-BR.",
            "Passos máximos de 2.000.000 e soma de neurônios ≤ 1024.",
            "422 para configuração inválida; 409 para run em execução/finalizado; 404 para recurso ausente.",
            "Um treino ativo por processo; os demais aguardam o lock.",
            "Timeout e cancelamento cooperativo via model.stop().",
        ]
    )
    b.h("8.9 Docker", 2)
    b.p(
        "O Compose sobe data (download one-shot), db (Postgres 16), api (FastAPI) e web (Next.js standalone). "
        "Healthchecks garantem a ordem data → db → api → web. O volume pgdata preserva o banco; bind mounts "
        "preservam backend/data e backend/artifacts. make up sobe em background; make refresh recria tudo "
        "preservando os dados; make seed cria o run Demo."
    )
    b.page_break()

    # ------------------------------------------------------------------ 9
    b.h("9. Frontend — o que cada página faz", 1)
    b.h("9.1 Stack e arquitetura", 2)
    b.p(
        "O frontend usa Next.js 16 (App Router), TypeScript, Tailwind CSS, Recharts, react-hook-form + Zod, "
        "next-themes e react-icons. O layout tem sidebar, header, seletor de tema claro/escuro/sistema e "
        "conteúdo responsivo. O proxy em app/api/[...path]/route.ts encaminha REST e SSE em runtime para "
        "API_INTERNAL_URL, permitindo construir a imagem antes da API existir."
    )
    b.h("9.2 Dashboard — /", 2)
    b.p(
        "Mostra quatro cards (total de runs, melhor F1 macro, tempo médio, amostras), uma tabela com nome, "
        "status, alvo, F1/ROC, épocas e link de análise, além do CTA 'Novo Treinamento'. O estado vazio "
        "orienta o primeiro treino."
    )
    b.figure(SHOTS / "01-dashboard.png", "Figura 8 — Dashboard com o run Demo.", 15.2)
    b.h("9.3 Treinar — /treinar", 2)
    b.p(
        "O formulário tem seis seções em acordeão: Objetivo (nome, alvo, presets), Dados (grupos, max_rows, "
        "seed, estratificação, duplicatas), Pré-processamento (scaler, log1p, rare_min_count, pesos), "
        "Arquitetura (camadas, neurônios, ativação, init, dropout, L2), Otimização (otimizador, lr, decay, "
        "batch, épocas, paciência, clipping) e Avaliação (loss, focal_gamma, threshold). O NeuronsEditor "
        "sincroniza o array com hidden_layers; o Zod espelha o backend."
    )
    b.p(
        "Ao iniciar, o run é criado e o painel mostra status, barra de progresso, loss treino×validação, "
        "acurácia/F1, console de épocas, botão cancelar e link para resultados. O SSE atualiza em tempo real; "
        "o console mantém as últimas 100 épocas."
    )
    b.figure(SHOTS / "02-treinar.png", "Figura 9 — Formulário e painel de treino.", 15.2)
    b.h("9.4 Resultados — /resultados/[id]", 2)
    b.p(
        "Apresenta cabeçalho, cards de métricas, matriz de confusão, abas ROC/PR, varredura de limiar, tabela "
        "por classe, histograma, calibração, hiperparâmetros, downloads e ações (repetir, simular, comparar). "
        "Os gráficos leem apenas dados agregados do backend."
    )
    b.figure(SHOTS / "03-resultados.png", "Figura 10 — Página de resultados do run Demo.", 14.0)
    b.h("9.5 Comparar — /comparar", 2)
    b.p(
        "Permite selecionar até quatro runs concluídos. Mostra barras agrupadas de F1/ROC/acurácia e uma "
        "tabela que cruza métricas e hiperparâmetros. A seleção pode vir por query string (?ids=...)."
    )
    b.figure(SHOTS / "04-comparar.png", "Figura 11 — Comparação de runs.", 15.0)
    b.h("9.6 Simulador — /simulador", 2)
    b.p(
        "Seleciona um run concluído, monta o formulário a partir de /api/meta (categorias reais), envia "
        "POST /api/predict e exibe a probabilidade: gauge no binário, três barras no 3 classes. Mostra as "
        "contribuições por campo, histórico local das últimas cinco simulações e o aviso ético."
    )
    b.figure(SHOTS / "06-simulador.png", "Figura 12 — Simulador com probabilidade e contribuições.", 15.0)
    b.h("9.7 Dataset — /dados", 2)
    b.p(
        "Explica origem, volumetria, distribuição do alvo, vazamento e limitações. É a página de consulta "
        "para a banca entender por que certas colunas foram excluídas."
    )
    b.figure(SHOTS / "05-dados.png", "Figura 13 — Página do dataset.", 15.0)
    b.figure(DOCS / "qrcode.png", "Figura 14 — QR code para a aplicação local (http://localhost:3000).", 3.8)
    b.h("9.8 Componentes, validação e testes", 2)
    b.table(
        ["Área", "Componentes"],
        [
            ["Layout", "Header, Sidebar, PageHeader, StatCard, ThemeToggle, Icons"],
            ["Formulário", "SectionAccordion, NumberField, SelectField, SwitchField, MultiCheckbox, NeuronsEditor"],
            ["Treino", "RunProgress, LiveLossChart, MetricChart, LogConsole, CancelButton, useRunStream"],
            ["Gráficos", "ConfusionMatrix, RocPrChart, ThresholdChart, PredictedProbHistogram, CalibrationChart"],
            ["Resultados", "RunHeader, MetricsGrid, MetricsGridDetailed, HyperparameterTable, ArtifactDownloads"],
            ["Simulador", "AccidentForm, ProbabilityCard, ContributionBars"],
        ],
        widths=[3.6, 12.4],
    )
    b.p(
        "Os formulários usam Zod para espelhar as faixas do backend. Erros de API viram banners; estados de "
        "loading usam skeletons; tabelas e gráficos têm labels. O contraste foi testado por cálculo WCAG "
        "(≥ 4,5:1) e a responsividade por Playwright em 1366×768 e 390×844. Vitest cobre formatadores, "
        "validação, presets, contraste e um componente; Playwright cobre treinar, simular, tema e responsivo."
    )
    b.page_break()

    # ------------------------------------------------------------------ 10
    b.h("10. Reprodutibilidade e operação", 1)
    b.h("10.1 Ambiente local", 2)
    b.code(
        "make venv\n"
        "make install\n"
        "make test\n"
        "make lint\n"
        "make typecheck\n"
        "make types\n"
        "cd frontend && npm install && npm run dev"
    )
    b.h("10.2 Docker", 2)
    b.code(
        "cp .env.example .env\n"
        "make up          # data + db + api + web em background\n"
        "make seed        # run Demo no Postgres e artifacts\n"
        "make logs\n"
        "make down\n"
        "make refresh     # recria preservando pgdata/artifacts\n"
        "make reset-db    # destrutivo: apaga o volume"
    )
    b.table(
        ["Variável", "Default", "Uso"],
        [
            ["POSTGRES_USER", "tde", "usuário do banco"],
            ["POSTGRES_PASSWORD", "tde", "senha do banco"],
            ["POSTGRES_DB", "tde", "nome do banco"],
            ["DB_PORT", "5432", "porta publicada do Postgres"],
            ["API_PORT", "8000", "porta da API"],
            ["WEB_PORT", "3000", "porta do frontend"],
            ["API_INTERNAL_URL", "http://api:8000", "proxy do Next dentro da rede"],
            ["HOST_UID/GID", "1000", "dono do CSV baixado"],
        ],
        widths=[4.8, 4.4, 6.6],
    )
    b.h("10.3 Dataset e artefatos", 2)
    b.p(
        "make fetch baixa o CSV; o serviço data faz o mesmo automaticamente no Compose. O hash é validado. "
        "Os artefatos ficam em backend/artifacts/runs/<id>/; docs/backup_run guarda uma cópia do run Demo "
        "para a entrega. O zip final é gerado por make package."
    )
    b.h("10.4 Verificações e troubleshooting", 2)
    b.table(
        ["Situação", "Ação"],
        [
            ["Porta 5432 ocupada", "alterar DB_PORT no .env e make refresh"],
            ["dependency db failed to start", "make refresh; ver docker compose logs db"],
            ["This page couldn't load", "recarregar Ctrl+Shift+R; verificar web healthy"],
            ["CSV ausente", "make fetch ou deixar o serviço data baixar"],
            ["run travado", "cancelar, ver logs, make refresh"],
            ["volume incompatível", "make reset-db (destrutivo)"],
        ],
        widths=[6.0, 10.6],
    )
    b.page_break()

    # ------------------------------------------------------------------ 11
    b.h("11. Resultados consolidados e análise crítica", 1)
    b.table(
        ["Métrica", "Demo", "Notebook binário", "Notebook 3 classes"],
        [
            ["Acurácia", "0,7917", "0,7788", "0,5931"],
            ["F1 macro", "0,5469", "0,5910", "0,4817"],
            ["F1 fatal", "0,2138", "0,3140", "—"],
            ["ROC-AUC", "0,6747", "0,8001", "0,7494"],
            ["PR-AUC", "0,1483", "0,2989", "0,5385"],
            ["Log-loss", "0,4779", "0,5035", "0,8857"],
            ["ECE", "0,0517", "0,0552", "—"],
        ],
        widths=[3.6, 4.0, 4.0, 4.4],
    )
    b.p(
        "A leitura correta é: o modelo não supera o baseline majoritário em acurácia, mas encontra parte "
        "dos casos fatais. O F1 fatal de 0,21–0,31 e o PR-AUC baixo mostram que ainda há muito espaço. "
        "O ROC-AUC de 0,67–0,80 indica separação razoável, mas não excelente. A calibração é aceitável "
        "(ECE ~0,05), embora a curva tenha regiões de subconfiança."
    )
    b.p(
        "A diferença entre treino e validação/teste é o overfitting controlado pelo early stopping. O modelo "
        "pequeno é adequado ao sinal disponível; aumentar a rede sem novas variáveis não resolve o problema. "
        "A base não contém os fatores mais importantes para letalidade, o que impõe um teto."
    )
    b.h("11.1 Limitações", 2)
    b.bullet(
        [
            "Variáveis ausentes: velocidade, cinto, tipo de veículo, condições do condutor, tempo de socorro.",
            "Causa provável e subnotificação.",
            "Recorte de 2024 e granularidade por ocorrência.",
            "Desbalanceamento extremo e poucos positivos no teste.",
            "Métrica de probabilidade não é decisão; threshold é escolha de política.",
            "Não há validação temporal ou por UF.",
        ]
    )
    b.h("11.2 Melhorias", 2)
    b.bullet(
        [
            "Engenharia de features e interações (tipo de acidente × via × clima).",
            "Calibração (Platt/isotônica) e ajuste de threshold por custo.",
            "Baselines de regressão logística e gradient boosting.",
            "Validação temporal e por UF; análise de subgrupos.",
            "Explicabilidade local (SHAP/permutação) e monitoramento.",
            "Coleta de variáveis faltantes em parceria com a PRF.",
        ]
    )
    b.h("11.3 Respostas às perguntas do guia", 2)
    b.numbered(
        [
            "Qual problema foi resolvido? A estimativa da probabilidade de vítima fatal a partir do cenário registrado, com comparação entre alvo binário e 3 classes.",
            "Por que a arquitetura escolhida faz sentido? Uma MLP tabular pequena captura interações não lineares sem exigir dados sequenciais ou espaciais; o sinal disponível não justifica uma rede maior.",
            "A rede aprendeu? Sim: a loss de treino caiu, a validação estabilizou e o F1 fatal ficou acima do acaso. O aprendizado é parcial e limitado pela base.",
            "Como a função de perda se comportou durante o treinamento? A weighted cross-entropy caiu de ~0,68 para ~0,40 no treino; na validação, caiu até ~0,54 e estabilizou, com early stopping na época 14.",
            "Qual foi o resultado nos dados de teste? Acurácia 0,7788, F1 macro 0,5910, F1 fatal 0,3140 e ROC-AUC 0,8001 no notebook; no Demo, 0,7917, 0,5469, 0,2138 e 0,6747.",
            "Houve diferença entre treinamento e teste? Sim: a loss de treino continuou caindo enquanto a de validação estabilizou, indicando overfitting; o early stopping e o modelo pequeno reduziram o problema.",
            "Quais limitações foram identificadas? Falta de velocidade, cinto, tipo de veículo e tempo de socorro; subnotificação; causa provável; recorte de 2024; granularidade por ocorrência.",
            "O que poderia ser modificado para melhorar o modelo? Novas variáveis, calibração, validação temporal/por UF, baselines de boosting, explicabilidade local e ajuste de threshold por custo.",
        ]
    )
    b.page_break()

    b.h("12. Conclusão", 1)
    b.p(
        "O objetivo didático foi cumprido: a MLP foi implementada do zero, treinada, testada e analisada, "
        "com métricas corretas e discussão honesta. O objetivo aplicado também: a aplicação permite configurar, "
        "acompanhar, comparar e simular. O resultado é um protótipo acadêmico útil para ensinar redes neurais "
        "e discutir limites de dados públicos, não uma ferramenta de decisão."
    )
    b.p(
        "A principal lição é que arquitetura e métrica não substituem dados. O modelo encontrou parte do sinal, "
        "mas o teto de desempenho é imposto pela ausência de variáveis determinantes para a letalidade. "
        "Reconhecer esse limite é parte do resultado, não uma falha escondida."
    )
    b.page_break()

    # ------------------------------------------------------------------ appendices
    b.h("Apêndice A — Glossário", 1)
    glossary = [
        ("Neurônio", "Unidade que calcula soma ponderada + bias e aplica ativação."),
        ("Peso", "Parâmetro que escala a contribuição de uma entrada."),
        ("Bias", "Deslocamento da soma ponderada, independente das entradas."),
        ("Camada de entrada", "Recebe as features."),
        ("Camada oculta", "Transforma representações intermediárias."),
        ("Camada de saída", "Produz logits/probabilidades."),
        ("Ativação", "Não linearidade aplicada ao neurônio."),
        ("ReLU", "max(0, z); derivada 1 se z>0."),
        ("Tanh", "Tangente hiperbólica; saída entre -1 e 1."),
        ("Sigmoid", "1/(1+exp(-z)); saída entre 0 e 1."),
        ("Leaky ReLU", "z se z>0, 0,01z caso contrário."),
        ("Softmax", "Transforma logits em probabilidades que somam 1."),
        ("Logits", "Saída linear antes da softmax."),
        ("Forward pass", "Propagação da entrada até a saída."),
        ("Loss", "Função que mede o erro."),
        ("Cross-entropy", "Loss para classificação probabilística."),
        ("Weighted CE", "Cross-entropy com pesos por classe."),
        ("Focal loss", "CE modulada por (1-p_t)^γ."),
        ("Gradiente", "Vetor de derivadas parciais."),
        ("Regra da cadeia", "Composição de derivadas no backward."),
        ("Backpropagation", "Cálculo dos gradientes camada a camada."),
        ("Learning rate", "Tamanho do passo de atualização."),
        ("Época", "Uma passagem completa pelo treino."),
        ("Batch", "Subconjunto de amostras usado por passo."),
        ("Mini-batch", "Batch menor que o dataset."),
        ("Full batch", "Batch igual ao dataset."),
        ("SGD", "Gradiente descendente estocástico."),
        ("Momentum", "Média exponencial de gradientes."),
        ("Adam", "Otimizador com momentos e correção de viés."),
        ("AdamW", "Adam com weight decay desacoplado."),
        ("Dropout", "Desliga neurônios aleatoriamente no treino."),
        ("L2", "Penalidade proporcional ao quadrado dos pesos."),
        ("Gradient clipping", "Limita a norma do gradiente."),
        ("Early stopping", "Para quando a validação não melhora."),
        ("Checkpoint", "Conjunto de pesos salvos."),
        ("Overfitting", "Memoriza treino e perde generalização."),
        ("Underfitting", "Não aprende nem no treino."),
        ("Seed", "Semente para reprodutibilidade."),
        ("Acurácia", "Acertos / total."),
        ("Precisão", "TP/(TP+FP)."),
        ("Recall", "TP/(TP+FN)."),
        ("F1", "Média harmônica de precisão e recall."),
        ("Matriz de confusão", "TP/TN/FP/FN por classe."),
        ("ROC-AUC", "Área sob a curva TPR×FPR."),
        ("PR-AUC", "Área sob precisão×recall."),
        ("Log-loss", "Entropia cruzada média."),
        ("Brier", "Erro quadrático das probabilidades."),
        ("ECE", "Erro esperado de calibração."),
        ("Threshold", "Limiar de decisão binária."),
        ("Data leakage", "Uso de informação que não estaria disponível na predição."),
        ("One-hot", "Codificação de categoria em vetores binários."),
        ("__OUTROS__", "Categoria reservada para raras/não vistas."),
        ("Padronização", "Subtrair média e dividir pelo desvio."),
        ("Estratificação", "Preservar proporção de classes no split."),
        ("Inferência", "Predição em dados novos."),
        ("SSE", "Server-Sent Events; stream unidirecional."),
        ("API", "Interface de programação da aplicação."),
        ("Container", "Ambiente isolado empacotado."),
    ]
    b.table(["Termo", "Definição"], [[x, y] for x, y in glossary], widths=[4.2, 11.8], font_size=8.0)
    b.page_break()

    b.h("Apêndice B — Dicionário das 30 colunas", 1)
    columns = [
        ("id", "Inteiro", "Identificador único da ocorrência", "Excluído"),
        ("data_inversa", "Data", "Data do acidente", "Excluída"),
        ("dia_semana", "Categórica", "Dia da semana", "Usada"),
        ("horario", "Hora", "Horário do acidente", "Base de hora_sin/cos"),
        ("uf", "Categórica", "Unidade da Federação", "Usada"),
        ("br", "Inteiro", "Número da rodovia", "Usada"),
        ("km", "Decimal", "Quilômetro do trecho", "Usada"),
        ("municipio", "Categórica", "Município", "Opcional"),
        ("causa_acidente", "Categórica", "Causa provável", "Usada"),
        ("tipo_acidente", "Categórica", "Tipo de colisão/evento", "Usada"),
        ("classificacao_acidente", "Categórica", "Gravidade registrada", "Alvo"),
        ("fase_dia", "Categórica", "Iluminação", "Usada"),
        ("sentido_via", "Categórica", "Sentido do tráfego", "Usada"),
        ("condicao_metereologica", "Categórica", "Clima", "Usada"),
        ("tipo_pista", "Categórica", "Configuração da pista", "Usada"),
        ("tracado_via", "Categórica", "Geometria do trecho", "Reduzida a tracado_principal"),
        ("uso_solo", "Booleana", "Área urbana?", "Usada"),
        ("pessoas", "Inteiro", "Pessoas envolvidas", "Vazamento"),
        ("mortos", "Inteiro", "Total de mortos", "Vazamento/alvo binário"),
        ("feridos_leves", "Inteiro", "Feridos leves", "Vazamento"),
        ("feridos_graves", "Inteiro", "Feridos graves", "Vazamento"),
        ("ilesos", "Inteiro", "Pessoas ilesas", "Vazamento"),
        ("ignorados", "Inteiro", "Estado ignorado", "Vazamento"),
        ("feridos", "Inteiro", "Total de feridos", "Vazamento"),
        ("veiculos", "Inteiro", "Veículos envolvidos", "Usada"),
        ("latitude", "Decimal", "Latitude", "Excluída"),
        ("longitude", "Decimal", "Longitude", "Excluída"),
        ("regional", "Categórica", "Superintendência regional", "Opcional"),
        ("delegacia", "Categórica", "Delegacia da PRF", "Opcional"),
        ("uop", "Categórica", "Unidade operacional", "Opcional"),
    ]
    b.table(["#", "Coluna", "Tipo", "Significado", "Uso"], [[i+1, c, t, s, u] for i, (c, t, s, u) in enumerate(columns)], widths=[0.8, 4.0, 2.2, 6.2, 3.8], font_size=7.6)
    b.page_break()

    b.h("Apêndice C — Catálogo de hiperparâmetros", 1)
    hp = [
        ("target", "Alvo", "fatal_binario / gravidade_3_classes", "fatal_binario"),
        ("feature_groups", "Grupos de features", "localizacao, tempo, via, circunstancia, frota, regional", "5 primeiros"),
        ("max_rows", "Subamostra estratificada", "100–73.201", "null"),
        ("val_size / test_size", "Frações de validação/teste", "0,05–0,4", "0,2 / 0,2"),
        ("stratify", "Split estratificado", "on/off", "on"),
        ("seed", "Semente", "0–999999", "42"),
        ("rare_min_count", "Limite para OUTROS", "0–500", "30"),
        ("scaler", "Escala numérica", "standard/minmax/none", "standard"),
        ("log1p_numeric", "log1p em br/km/veículos", "on/off", "on"),
        ("class_weight", "Pesos", "none/balanced/custom", "balanced"),
        ("drop_duplicates", "Remover linhas duplicadas", "on/off", "on"),
        ("hidden_layers", "Camadas ocultas", "1–4", "2"),
        ("neurons", "Neurônios por camada", "1–1024 no total", "[64, 32]"),
        ("activation", "Ativação", "relu/tanh/sigmoid/leaky", "relu"),
        ("init", "Inicialização", "he/xavier/normal", "he"),
        ("dropout", "Dropout", "0–0,5", "0"),
        ("l2", "L2", "0–0,1", "0"),
        ("loss", "Loss", "ce/weighted_ce/focal", "weighted_ce"),
        ("focal_gamma", "Gamma da focal", "0–10", "2"),
        ("optimizer", "Otimizador", "sgd/momentum/adam/adamw", "adam"),
        ("lr", "Learning rate", "1e-6–1", "1e-3"),
        ("lr_decay", "Decaimento", "none/step/cosine", "none"),
        ("decay_rate / decay_every", "Step decay", "0–1 / 1+", "0,5 / 50"),
        ("batch_size", "Batch", "1+ ou full", "256"),
        ("epochs", "Épocas", "1–2000", "200"),
        ("patience", "Early stopping", "0–100", "15"),
        ("grad_clip", "Clipping", "0–10", "5"),
        ("threshold", "Limiar binário", "0,05–0,95", "0,5"),
    ]
    b.table(["Parâmetro", "Significado", "Faixa/opções", "Default"], [list(x) for x in hp], widths=[4.0, 5.6, 4.8, 3.0], font_size=7.8)
    b.page_break()

    b.h("Apêndice D — Endpoints e exemplos", 1)
    b.code(
        "curl http://localhost:8000/api/health\n"
        "curl http://localhost:8000/api/meta\n"
        "curl http://localhost:8000/api/datasets/summary\n"
        "curl -X POST http://localhost:8000/api/estimate \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"data\": {}, \"model\": {}}'\n"
        "curl -X POST http://localhost:8000/api/runs \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"name\":\"Demo\",\"data\":{},\"model\":{}}'\n"
        "curl http://localhost:8000/api/runs\n"
        "curl -N http://localhost:8000/api/runs/<id>/stream\n"
        "curl -X POST http://localhost:8000/api/predict \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"run_id\":\"<id>\",\"features\":{\"uf\":\"SP\"}}'"
    )
    b.p(
        "A documentação interativa fica em /api/docs (Swagger) e /api/redoc. O contrato OpenAPI é gerado "
        "por make types e consumido pelo frontend."
    )
    b.h("Apêndice E — Mapa de arquivos", 1)
    b.table(
        ["Arquivo", "Papel"],
        [
            ["backend/nn/config.py", "configurações e presets"],
            ["backend/nn/data.py", "pipeline de dados"],
            ["backend/nn/model.py", "MLP"],
            ["backend/nn/metrics.py", "métricas"],
            ["backend/nn/export.py", "serialização e predição"],
            ["backend/api/main.py", "rotas"],
            ["backend/api/trainer.py", "worker de treino"],
            ["backend/api/store.py", "repositório"],
            ["backend/scripts/fetch_data.py", "download"],
            ["backend/scripts/seed_demo.py", "demo"],
            ["backend/notebooks/TDE_rede_neural_acidentes_PRF.ipynb", "notebook executado"],
            ["frontend/app/page.tsx", "dashboard"],
            ["frontend/app/treinar/page.tsx", "treino"],
            ["frontend/app/resultados/[id]/page.tsx", "resultados"],
            ["frontend/app/comparar/page.tsx", "comparação"],
            ["frontend/app/simulador/page.tsx", "simulador"],
            ["frontend/app/dados/page.tsx", "dataset"],
            ["docker-compose.yml", "orquestração"],
            ["docs/backup_run", "artefatos do run Demo"],
        ],
        widths=[8.8, 7.2],
        font_size=8.0,
    )
    b.page_break()

    b.h("Apêndice F — Conformidade com o guia do professor", 1)
    b.table(
        ["Exigência", "Onde atendida", "Página (PDF)"],
        [
            ["Dataset oficial + órgão + link + variáveis + entrada/saída + treino/teste", "2.1–2.4, 3.4, Apêndice B", "7–9"],
            ["Leitura, colunas, tipos, nulos, seleção, preparação, split", "2.2, 2.5, 3.1–3.7", "7–12"],
            ["__init__, forward, loss, backpropagation, fit", "4.3–4.10", "13–16"],
            ["Justificativa da função de perda", "4.5 e 5.2", "14 e 16"],
            ["Derivada, regra da cadeia, gradiente, lr, atualização", "4.6–4.8", "14–15"],
            ["Arquitetura explícita", "4.2 e 5.1", "13 e 16"],
            ["Hiperparâmetros justificados", "5.2 e Apêndice C", "16–17 e 41"],
            ["≥ 2 entradas, ≥ 1 camada oculta, saída adequada, épocas", "4.2 e 5.1", "13 e 16"],
            ["Evolução do treino", "5.4 e notebook §7", "17"],
            ["Teste em dados não vistos + previsões + erros + métricas", "5.9–5.11 e capítulo 6", "18–21"],
            ["Acurácia vs métricas adequadas", "5.9, 5.12 e 11", "18–19 e 34"],
            ["Análise crítica completa", "11 e 12", "34–36"],
            ["Notebook comentado", "backend/notebooks (27 células)", "arquivo"],
            ["Documento nas 8 seções", "Resumo executivo + capítulos 1–12", "2–36"],
        ],
        widths=[8.0, 5.4, 2.4],
        font_size=7.8,
    )
    b.p(
        "Pendência externa: o guia menciona grupos de 2 alunos; este grupo tem 3. A autorização do professor "
        "deve ser confirmada. Os placeholders [CURSO], [INSTITUIÇÃO] e [SEMESTRE] também dependem do grupo."
    )
    b.page_break()

    b.h("Apêndice G — Inventário de testes", 1)
    b.table(
        ["Arquivo", "O que cobre"],
        [
            ["tests/test_data.py", "carga, alvos, split, leakage, preprocessor, JSON, OUTROS, pesos, max_rows"],
            ["tests/test_model.py", "gradiente numérico, softmax, dropout, XOR, early stopping, seed, save/load"],
            ["tests/test_metrics.py", "paridade com sklearn, calibração, sweep, histograma"],
            ["tests/test_parity.py", "predict_with_json × matriz NumPy"],
            ["tests/test_api.py", "meta, estimate, summary, OpenAPI, 422"],
            ["tests/test_api_integration.py", "run + SSE + predict + export com Postgres"],
            ["frontend/tests/*.test.ts", "format, Zod, presets, contraste WCAG, ConfusionMatrix"],
            ["frontend/e2e/*.spec.ts", "treinar, simulador, tema, responsivo"],
        ],
        widths=[6.4, 9.6],
        font_size=8.0,
    )
    b.h("Apêndice H — Comandos de reprodução e demo", 1)
    b.code(
        "make fetch\nmake install\nmake test\nmake lint\nmake typecheck\nmake types\nmake up\nmake seed\nmake logs\nmake down\nmake refresh\nmake reset-db\nmake package"
    )
    b.h("Apêndice I — Lista de figuras", 1)
    b.bullet(
        [
            "Figura 1 — Distribuição da gravidade e do km.",
            "Figura 2 — Top causas e tipos de acidente.",
            "Figura 3 — Acidentes por hora.",
            "Figura 4 — Curvas de loss/acurácia/F1.",
            "Figura 5 — Matriz de confusão.",
            "Figura 6 — ROC, PR e varredura de limiar.",
            "Figura 7 — Histograma e calibração.",
            "Figura 8 — Dashboard.",
            "Figura 9 — Formulário de treino.",
            "Figura 10 — Resultados.",
            "Figura 11 — Comparação.",
            "Figura 12 — Simulador.",
            "Figura 13 — Dataset.",
            "Figura 14 — QR code da aplicação local.",
        ]
    )
    b.h("Apêndice J — Referências", 1)
    b.bullet(
        [
            "PRF — Dados Abertos e Dicionário de Acidentes (DATATRAN 2024).",
            "Material e vídeos de Redes Neurais do professor Edilson Carlos Silva Lima.",
            "Série Neural Network from Scratch in Python (referência didática).",
            "Documentação do NumPy, pandas, FastAPI, SQLAlchemy, Next.js e scikit-learn.",
            "Documentação do PostgreSQL 16 e Docker Compose.",
        ]
    )

    b.save()
    print(f"DOCX escrito em {OUT}")


if __name__ == "__main__":
    build()
