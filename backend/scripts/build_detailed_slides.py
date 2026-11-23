#!/usr/bin/env python3
"""Gera a apresentação detalhada (25 slides) a partir do documento técnico."""

from __future__ import annotations

import json
from pathlib import Path

import qrcode
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
FIG = DOCS / "figures"
SHOTS = DOCS / "screenshots"
OUT = DOCS / "TDE_apresentacao_detalhada.pptx"
VPS_URL = "http://185.173.110.137:3000/"


def br(value: float) -> str:
    return f"{value:.4f}".replace(".", ",")

BG = RGBColor(0x0B, 0x0F, 0x14)
PANEL = RGBColor(0x11, 0x18, 0x23)
PANEL2 = RGBColor(0x18, 0x22, 0x33)
BORDER = RGBColor(0x22, 0x30, 0x4A)
TEXT = RGBColor(0xE6, 0xED, 0xF7)
MUTED = RGBColor(0x8F, 0xA3, 0xBF)
TEAL = RGBColor(0x22, 0xD3, 0xEE)
PINK = RGBColor(0xF4, 0x72, 0xB6)
GREEN = RGBColor(0x34, 0xD3, 0x99)
RED = RGBColor(0xF8, 0x71, 0x71)
YELLOW = RGBColor(0xFB, 0xBF, 0x24)

W = 13.333
H = 7.5


def load_demo() -> tuple[dict, dict]:
    manifest = json.loads((DOCS / "backup_run" / "run.json").read_text(encoding="utf-8"))
    evaluation = json.loads(
        (DOCS / "backup_run" / "evaluation.json").read_text(encoding="utf-8")
    )
    return manifest, evaluation


def make_qr() -> Path:
    path = DOCS / "qrcode_vps.png"
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=2,
    )
    qr.add_data(VPS_URL)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#0B0F14", back_color="white")
    image.save(path)
    return path


class Deck:
    def __init__(self) -> None:
        self.prs = Presentation()
        self.prs.slide_width = Inches(W)
        self.prs.slide_height = Inches(H)
        self.page = 0

    def blank(self, section: str, title: str) -> object:
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.page += 1
        background = slide.background.fill
        background.solid()
        background.fore_color.rgb = BG

        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(W), Inches(0.08))
        bar.fill.solid()
        bar.fill.fore_color.rgb = TEAL
        bar.line.fill.background()

        self.text(slide, 0.6, 0.28, 9.5, 0.3, section.upper(), 10, TEAL, bold=True)
        self.text(slide, 0.6, 0.58, 12.1, 0.8, title, 28, TEXT, bold=True)
        self.text(slide, 0.6, 7.15, 7.5, 0.2, "TDE Redes Neurais · PRF DATATRAN 2024", 8, MUTED)
        self.text(slide, 12.1, 7.15, 0.7, 0.2, f"{self.page:02d}", 8, MUTED, align=PP_ALIGN.RIGHT)
        return slide

    @staticmethod
    def notes(slide, text: str) -> None:
        slide.notes_slide.notes_text_frame.text = text

    @staticmethod
    def text(
        slide,
        x: float,
        y: float,
        w: float,
        h: float,
        value: str,
        size: float = 16,
        color: RGBColor = TEXT,
        *,
        bold: bool = False,
        align=PP_ALIGN.LEFT,
        font: str = "Calibri",
        valign=MSO_ANCHOR.TOP,
        line_spacing: float = 1.0,
    ):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = 0
        frame.margin_right = 0
        frame.margin_top = 0
        frame.margin_bottom = 0
        frame.vertical_anchor = valign
        paragraph = frame.paragraphs[0]
        paragraph.alignment = align
        paragraph.line_spacing = line_spacing
        run = paragraph.add_run()
        run.text = value
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        return box

    @staticmethod
    def bullets(slide, x, y, w, h, items, size=15, color=TEXT):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = 0
        frame.margin_right = 0
        frame.margin_top = 0
        frame.margin_bottom = 0
        for index, item in enumerate(items):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.space_after = Pt(5)
            paragraph.line_spacing = 1.0
            if isinstance(item, tuple):
                value, level = item
            else:
                value, level = item, 0
            prefix = "• " if level == 0 else "   – "
            run = paragraph.add_run()
            run.text = prefix + value
            run.font.name = "Calibri"
            run.font.size = Pt(size if level == 0 else size - 1)
            run.font.color.rgb = color if level == 0 else MUTED
        return box

    @staticmethod
    def card(slide, x, y, w, h, fill=PANEL):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
        shape.line.color.rgb = BORDER
        shape.line.width = Pt(0.7)
        shape.adjustments[0] = 0.05
        return shape

    def kpi(self, slide, x, y, w, h, label, value, sub="", color=TEAL, value_size=30):
        self.card(slide, x, y, w, h)
        self.text(slide, x + 0.18, y + 0.15, w - 0.36, 0.28, label.upper(), 9, MUTED, bold=True)
        self.text(slide, x + 0.18, y + 0.45, w - 0.36, 0.7, value, value_size, color, bold=True)
        if sub:
            self.text(slide, x + 0.18, y + h - 0.42, w - 0.36, 0.3, sub, 9, MUTED)

    @staticmethod
    def image(slide, path: Path, x, y, w, h, caption: str | None = None):
        if not path.exists():
            return
        with Image.open(path) as image:
            iw, ih = image.size
        caption_h = 0.32 if caption else 0
        avail_h = h - caption_h
        scale = min(w / iw, avail_h / ih)
        nw, nh = iw * scale, ih * scale
        left = x + (w - nw) / 2
        top = y + (avail_h - nh) / 2
        pic = slide.shapes.add_picture(str(path), Inches(left), Inches(top), Inches(nw), Inches(nh))
        pic.line.color.rgb = BORDER
        pic.line.width = Pt(0.6)
        if caption:
            Deck.text(slide, x, y + h - 0.28, w, 0.25, caption, 8.5, MUTED, align=PP_ALIGN.CENTER)

    def table(self, slide, headers, rows, x, y, w, h, widths=None, font_size=9.5):
        shape = slide.shapes.add_table(
            len(rows) + 1, len(headers), Inches(x), Inches(y), Inches(w), Inches(h)
        )
        table = shape.table
        if widths:
            for index, width in enumerate(widths):
                table.columns[index].width = Inches(width)
        for col, header in enumerate(headers):
            cell = table.cell(0, col)
            cell.text = header
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            for paragraph in cell.text_frame.paragraphs:
                paragraph.alignment = PP_ALIGN.CENTER
                for run in paragraph.runs:
                    run.font.name = "Calibri"
                    run.font.size = Pt(font_size)
                    run.font.bold = True
                    run.font.color.rgb = BG
        for row_index, row in enumerate(rows, start=1):
            for col, value in enumerate(row):
                cell = table.cell(row_index, col)
                cell.text = str(value)
                cell.fill.solid()
                cell.fill.fore_color.rgb = PANEL if row_index % 2 else PANEL2
                cell.margin_left = Inches(0.06)
                cell.margin_right = Inches(0.06)
                cell.margin_top = Inches(0.025)
                cell.margin_bottom = Inches(0.025)
                for paragraph in cell.text_frame.paragraphs:
                    paragraph.alignment = PP_ALIGN.LEFT if col == 0 else PP_ALIGN.CENTER
                    for run in paragraph.runs:
                        run.font.name = "Calibri"
                        run.font.size = Pt(font_size)
                        run.font.color.rgb = TEXT

    def code(self, slide, x, y, w, h, text, size=10):
        self.card(slide, x, y, w, h, PANEL2)
        self.text(slide, x + 0.15, y + 0.12, w - 0.3, h - 0.24, text, size, TEXT, font="Consolas")

    def flow_box(self, slide, x, y, w, h, number, title, sub, color=TEAL):
        self.card(slide, x, y, w, h)
        self.text(slide, x + 0.12, y + 0.1, 0.35, 0.3, str(number), 16, color, bold=True)
        self.text(slide, x + 0.12, y + 0.42, w - 0.24, 0.35, title, 12, TEXT, bold=True)
        self.text(slide, x + 0.12, y + 0.75, w - 0.24, h - 0.8, sub, 8.5, MUTED)

    def save(self) -> None:
        OUT.parent.mkdir(exist_ok=True)
        self.prs.save(OUT)


def build() -> None:
    manifest, _evaluation = load_demo()
    metrics = manifest["metrics"]
    per_class = metrics["precision_recall_f1"]["per_class"]
    qr_path = make_qr()
    deck = Deck()

    # 1 ---------------------------------------------------------------- cover
    slide = deck.prs.slides.add_slide(deck.prs.slide_layouts[6])
    deck.page += 1
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = BG
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.16), Inches(H))
    bar.fill.solid()
    bar.fill.fore_color.rgb = TEAL
    bar.line.fill.background()
    deck.text(slide, 0.85, 0.65, 7.5, 0.3, "TDE · REDES NEURAIS", 11, TEAL, bold=True)
    deck.text(
        slide,
        0.85,
        1.15,
        7.7,
        1.7,
        "MLP do zero em NumPy para estimar letalidade em acidentes da PRF",
        34,
        TEXT,
        bold=True,
        line_spacing=1.0,
    )
    deck.text(
        slide,
        0.85,
        3.05,
        7.5,
        0.7,
        "DATATRAN 2024 · treinamento, avaliação e aplicação web",
        17,
        MUTED,
    )
    deck.text(
        slide,
        0.85,
        4.15,
        7.5,
        1.5,
        "Felipe Medeiros Castello Branco\nHerbeth Lucas de Sousa Pereira\nSamuel Pereira da Silva Varão",
        13,
        TEXT,
        line_spacing=1.15,
    )
    deck.text(slide, 0.85, 5.85, 7.5, 0.3, "Prof. Edilson Carlos Silva Lima", 12, MUTED)
    deck.text(
        slide,
        0.85,
        6.2,
        7.5,
        0.3,
        "[CURSO] · [INSTITUIÇÃO] · [SEMESTRE] · 2026",
        10,
        MUTED,
    )
    deck.card(slide, 9.15, 1.05, 3.45, 5.55, PANEL)
    qr = slide.shapes.add_picture(str(qr_path), Inches(9.55), Inches(1.45), Inches(2.65), Inches(2.65))
    qr.line.color.rgb = BORDER
    deck.text(slide, 9.4, 4.35, 2.95, 0.3, "ACESSE A APLICAÇÃO", 9, TEAL, bold=True, align=PP_ALIGN.CENTER)
    deck.text(slide, 9.3, 4.72, 3.15, 0.7, VPS_URL, 11, TEXT, bold=True, align=PP_ALIGN.CENTER)
    deck.text(
        slide,
        9.4,
        5.6,
        2.95,
        0.7,
        "Protótipo acadêmico. Não usar para decisões reais.",
        8.5,
        MUTED,
        align=PP_ALIGN.CENTER,
    )
    deck.notes(
        slide,
        "Abertura (30 s). Apresentar o grupo e o objetivo: estimar a probabilidade de vítima fatal "
        "em acidentes da PRF. Apontar o QR e o link da VPS. Reforçar que é protótipo acadêmico.",
    )

    # 2 ---------------------------------------------------------------- agenda
    slide = deck.blank("Roteiro", "O que vamos mostrar")
    for idx, (title, sub) in enumerate(
        [
            ("Problema e dados", "DATATRAN, colunas, vazamento e EDA"),
            ("Treinamento", "forward, loss, backprop, otimizadores e curvas"),
            ("Resultados", "métricas, erros, threshold e 3 classes"),
            ("Aplicação", "API, banco, páginas web e simulador"),
        ]
    ):
        deck.card(slide, 0.65 + idx * 3.08, 1.65, 2.85, 1.7)
        deck.text(slide, 0.85 + idx * 3.08, 1.85, 2.45, 0.35, f"0{idx + 1}", 18, TEAL, bold=True)
        deck.text(slide, 0.85 + idx * 3.08, 2.25, 2.45, 0.35, title, 13, TEXT, bold=True)
        deck.text(slide, 0.85 + idx * 3.08, 2.65, 2.45, 0.55, sub, 9, MUTED)
    deck.card(slide, 0.65, 3.85, 7.5, 2.3)
    deck.text(slide, 0.9, 4.05, 6.9, 0.35, "MENSAGEM CENTRAL", 10, PINK, bold=True)
    deck.text(
        slide,
        0.9,
        4.45,
        6.9,
        1.4,
        "A rede aprende parte do sinal e recupera casos fatais, "
        "mas o teto de desempenho é imposto pelas variáveis ausentes na base.",
        21,
        TEXT,
        bold=True,
    )
    deck.card(slide, 8.55, 3.85, 4.15, 2.3)
    deck.text(slide, 8.8, 4.05, 3.6, 0.35, "FOCO DA APRESENTAÇÃO", 10, TEAL, bold=True)
    deck.bullets(
        slide,
        8.8,
        4.45,
        3.6,
        1.5,
        ["Treinamento da MLP em detalhe", "Decisões e trade-offs", "O que a aplicação entrega"],
        12,
    )
    deck.notes(
        slide,
        "Roteiro (30 s). Dizer que o foco é treinamento; a aplicação é a materialização do modelo. "
        "A mensagem central será repetida no fim.",
    )

    # 3 ---------------------------------------------------------------- problem
    slide = deck.blank("Contexto", "Problema: gravidade rara, impacto alto")
    deck.bullets(
        slide,
        0.65,
        1.55,
        6.4,
        3.1,
        [
            "Acidentes em rodovias federais são um problema de saúde pública.",
            "Apenas 7,1% das ocorrências de 2024 tiveram vítima fatal.",
            "A base não contém velocidade, cinto, tipo de veículo ou tempo de socorro.",
            "Objetivo: estimar a probabilidade de fatalidade a partir do cenário registrado.",
            "Acurácia isolada engana: é preciso olhar recall/F1 da classe fatal.",
        ],
        15,
    )
    deck.kpi(slide, 7.35, 1.6, 2.65, 1.55, "Vítimas fatais", "5.225", "de 73.201 registros", RED)
    deck.kpi(slide, 10.2, 1.6, 2.45, 1.55, "Taxa-base", "7,1%", "classe positiva", YELLOW)
    deck.card(slide, 7.35, 3.5, 5.3, 2.45)
    deck.text(slide, 7.6, 3.7, 4.8, 0.3, "POR QUE ISSO IMPORTA", 9, PINK, bold=True)
    deck.text(
        slide,
        7.6,
        4.05,
        4.8,
        1.6,
        "Um classificador que sempre prevê “sem vítima fatal” acerta ~93%, "
        "mas tem recall zero para a classe que importa. O modelo precisa ser avaliado "
        "pelo que encontra, não apenas pelo que acerta.",
        12.5,
        TEXT,
    )
    deck.notes(
        slide,
        "Problema (1 min). Explicar o desbalanceamento e o custo assimétrico do erro. "
        "Perguntar à plateia por que acurácia não basta.",
    )

    # 4 ---------------------------------------------------------------- dataset
    slide = deck.blank("Dataset", "DATATRAN 2024: o que temos")
    deck.table(
        slide,
        ["Indicador", "Valor", "Indicador", "Valor"],
        [
            ["Registros no arquivo", "73.202", "Registros usados", "73.201"],
            ["Colunas", "30", "UFs", "27"],
            ["Municípios", "1.834", "Causas", "69"],
            ["Tipos de acidente", "17", "Mortos no ano", "6.163"],
            ["Feridos no ano", "84.595", "Alvo NA", "1"],
        ],
        0.65,
        1.55,
        12.0,
        3.0,
        widths=[3.0, 2.4, 3.4, 2.4],
        font_size=11,
    )
    deck.kpi(slide, 0.65, 4.95, 3.85, 1.45, "Binário", "67.976 / 5.225", "sem fatal / fatal", TEAL)
    deck.kpi(slide, 4.7, 4.95, 3.85, 1.45, "3 classes", "11.782 / 56.194 / 5.225", "sem / feridos / fatais", PINK, value_size=18)
    deck.card(slide, 8.75, 4.95, 3.95, 1.45)
    deck.text(slide, 8.95, 5.1, 3.55, 0.3, "FORMATO", 9, MUTED, bold=True)
    deck.text(slide, 8.95, 5.4, 3.55, 0.8, "latin-1 · separador “;” · decimal com vírgula", 11, TEXT)
    deck.notes(
        slide,
        "Dataset (1 min). Destacar 73.201 usados, 30 colunas e o desbalanceamento. "
        "Mencionar que a base é de ocorrências, não de pessoas.",
    )

    # 5 ---------------------------------------------------------------- columns
    slide = deck.blank("Colunas", "O que entra no treinamento")
    deck.table(
        slide,
        ["Grupo", "Numéricas", "Categóricas"],
        [
            ["Localização", "br, km", "uf"],
            ["Tempo", "hora_sin, hora_cos, is_fim_semana", "dia_semana"],
            ["Via", "—", "tipo_pista, tracado_principal, uso_solo, sentido_via"],
            ["Circunstância", "—", "causa_acidente, tipo_acidente, fase_dia, condicao_metereologica"],
            ["Frota", "veiculos", "—"],
            ["Regional (opcional)", "—", "regional, delegacia, uop"],
        ],
        0.65,
        1.5,
        12.0,
        3.7,
        widths=[2.5, 4.1, 5.4],
        font_size=9.5,
    )
    deck.card(slide, 0.65, 5.45, 5.85, 1.3)
    deck.text(slide, 0.85, 5.62, 5.4, 0.3, "DERIVADAS", 9, TEAL, bold=True)
    deck.text(
        slide,
        0.85,
        5.92,
        5.4,
        0.65,
        "hora_sin/cos, is_fim_semana, tracado_principal e log1p em br, km e veículos.",
        10.5,
        TEXT,
    )
    deck.card(slide, 6.75, 5.45, 5.9, 1.3)
    deck.text(slide, 6.95, 5.62, 5.4, 0.3, "DIMENSÃO", 9, PINK, bold=True)
    deck.text(
        slide,
        6.95,
        5.92,
        5.4,
        0.65,
        "6 numéricas + 10 categóricas → 92/110/112 features após one-hot.",
        10.5,
        TEXT,
    )
    deck.notes(
        slide,
        "Colunas (1,5 min). Este é um slide-chave: mostrar o que o modelo realmente vê. "
        "Explicar por que hora é cíclica e por que tracado foi reduzido ao primeiro termo. "
        "Dizer que a dimensão varia com max_rows/rare_min_count.",
    )

    # 6 ---------------------------------------------------------------- leakage
    slide = deck.blank("Colunas", "O que ficou de fora — e por quê")
    deck.table(
        slide,
        ["Coluna(s)", "Motivo"],
        [
            ["classificacao_acidente", "Define o alvo"],
            ["mortos, feridos, feridos_leves, feridos_graves, ilesos, ignorados, pessoas", "Consequência pós-evento (vazamento)"],
            ["id", "Identificador sem poder preditivo"],
            ["data_inversa", "Ano único; data exata não generaliza"],
            ["latitude, longitude", "Geolocalização precisa fora do escopo"],
            ["municipio, regional, delegacia, uop", "Alta cardinalidade administrativa (opcionais)"],
        ],
        0.65,
        1.55,
        12.0,
        3.4,
        widths=[7.0, 5.0],
        font_size=9.5,
    )
    deck.card(slide, 0.65, 5.25, 12.0, 1.35)
    deck.text(slide, 0.9, 5.42, 11.5, 0.3, "INVARIANTE TESTADO", 9, GREEN, bold=True)
    deck.text(
        slide,
        0.9,
        5.72,
        11.5,
        0.7,
        "Nenhuma coluna de LEAKAGE_COLUMNS pode aparecer nas features. O preprocessor também rejeita vazamento ao carregar.",
        12,
        TEXT,
    )
    deck.notes(
        slide,
        "Vazamento (1 min). Explicar que usar mortos/feridos seria trapaça. "
        "Mostrar que há teste automatizado para isso.",
    )

    # 7 ---------------------------------------------------------------- EDA
    slide = deck.blank("EDA", "O que os dados mostram")
    deck.image(slide, FIG / "notebook_cell06_1.png", 0.55, 1.45, 6.1, 2.55, "Gravidade e km")
    deck.image(slide, FIG / "notebook_cell06_2.png", 6.75, 1.45, 6.0, 2.55, "Causas e tipos")
    deck.image(slide, FIG / "notebook_cell06_3.png", 0.55, 4.15, 5.4, 2.35, "Acidentes por hora")
    deck.bullets(
        slide,
        6.35,
        4.2,
        6.2,
        2.2,
        [
            "Classe majoritária: com feridos (76,8%).",
            "Fatais: 7,1%; sem vítimas: 16,1%.",
            "Cauda longa de km e picos de horário.",
            "Causa provável é atribuição do boletim.",
        ],
        11,
    )
    deck.notes(
        slide,
        "EDA (1 min). Não ler todos os números; apontar o desbalanceamento e a cauda longa. "
        "Dizer que a causa é provável, não medida.",
    )

    # 8 ---------------------------------------------------------------- pipeline
    slide = deck.blank("Preparação", "Pipeline de dados")
    flow = [
        ("1", "CSV", "latin-1, ';', decimal ','"),
        ("2", "Limpeza", "remove alvo NA"),
        ("3", "Features", "hora, traçado, log1p"),
        ("4", "Split", "60/20/20 estratificado"),
        ("5", "Preprocessor", "fit só no treino"),
        ("6", "Matrizes", "one-hot + escala, float32"),
    ]
    for idx, (number, title, sub) in enumerate(flow):
        x = 0.55 + idx * 2.08
        deck.flow_box(slide, x, 1.55, 1.85, 1.55, number, title, sub, TEAL if idx % 2 == 0 else PINK)
        if idx < len(flow) - 1:
            deck.text(slide, x + 1.87, 1.95, 0.2, 0.3, "→", 18, MUTED, bold=True)
    deck.card(slide, 0.65, 3.55, 5.9, 2.75)
    deck.text(slide, 0.9, 3.75, 5.4, 0.3, "DECISÕES CRÍTICAS", 9, PINK, bold=True)
    deck.bullets(
        slide,
        0.9,
        4.1,
        5.4,
        2.0,
        [
            "Fit do preprocessor somente no treino.",
            "__OUTROS__ para categorias raras e não vistas.",
            "Padronização após log1p; imputação por mediana.",
            "Pesos de classe calculados no treino.",
        ],
        11,
    )
    deck.card(slide, 6.75, 3.55, 5.9, 2.75)
    deck.text(slide, 7.0, 3.75, 5.4, 0.3, "SPLIT", 9, TEAL, bold=True)
    deck.table(
        slide,
        ["Recorte", "Treino", "Val", "Teste"],
        [["Demo", "1.800", "600", "600"], ["Notebook", "4.800", "1.600", "1.600"], ["Completo", "43.921", "14.640", "14.640"]],
        7.0,
        4.1,
        5.3,
        1.6,
        widths=[1.7, 1.2, 1.1, 1.2],
        font_size=9,
    )
    deck.notes(
        slide,
        "Pipeline (1,5 min). Enfatizar prevenção de vazamento: split antes do fit do preprocessor. "
        "Explicar __OUTROS__ e pesos de classe.",
    )

    # 9 ---------------------------------------------------------------- architecture
    slide = deck.blank("Arquitetura", "A MLP usada no treinamento")
    deck.card(slide, 0.7, 1.75, 3.35, 1.65)
    deck.text(slide, 0.9, 1.9, 2.95, 0.3, "ENTRADA", 9, MUTED, bold=True)
    deck.text(slide, 0.9, 2.25, 2.95, 0.6, "92 / 110 / 112", 24, TEXT, bold=True)
    deck.text(slide, 0.9, 2.85, 2.95, 0.3, "features", 10, MUTED)
    deck.card(slide, 4.65, 1.75, 3.35, 1.65)
    deck.text(slide, 4.85, 1.9, 2.95, 0.3, "OCULTA", 9, MUTED, bold=True)
    deck.text(slide, 4.85, 2.25, 2.95, 0.6, "24 / 32", 24, TEAL, bold=True)
    deck.text(slide, 4.85, 2.85, 2.95, 0.3, "neurônios ReLU", 10, MUTED)
    deck.card(slide, 8.6, 1.75, 3.35, 1.65)
    deck.text(slide, 8.8, 1.9, 2.95, 0.3, "SAÍDA", 9, MUTED, bold=True)
    deck.text(slide, 8.8, 2.25, 2.95, 0.6, "2 / 3", 24, PINK, bold=True)
    deck.text(slide, 8.8, 2.85, 2.95, 0.3, "softmax", 10, MUTED)
    deck.text(slide, 3.95, 2.3, 0.5, 0.4, "→", 22, MUTED, bold=True)
    deck.text(slide, 7.9, 2.3, 0.5, 0.4, "→", 22, MUTED, bold=True)
    deck.kpi(slide, 0.7, 3.85, 2.9, 1.3, "Parâmetros Demo", "2.282", "92→24→2", TEAL)
    deck.kpi(slide, 3.8, 3.85, 2.9, 1.3, "Parâmetros binário", "3.618", "110→32→2", TEAL)
    deck.kpi(slide, 6.9, 3.85, 2.9, 1.3, "Parâmetros 3 classes", "3.715", "112→32→3", PINK)
    deck.card(slide, 10.0, 3.85, 2.65, 1.3)
    deck.text(slide, 10.2, 4.0, 2.25, 0.3, "INICIALIZAÇÃO", 9, MUTED, bold=True)
    deck.text(slide, 10.2, 4.3, 2.25, 0.6, "He normal", 16, TEXT, bold=True)
    deck.bullets(
        slide,
        0.7,
        5.5,
        11.9,
        1.2,
        [
            "Rede pequena e interpretável: o sinal disponível não justifica uma rede maior.",
            "ReLU + He; saída softmax; loss weighted cross-entropy; Adam 1e-3.",
        ],
        11,
    )
    deck.notes(
        slide,
        "Arquitetura (1 min). Mostrar que a rede é pequena de propósito. "
        "Comparar Demo e notebook sem misturar os números.",
    )

    # 10 --------------------------------------------------------------- forward
    slide = deck.blank("Treinamento", "Forward pass: da entrada à probabilidade")
    deck.card(slide, 0.65, 1.55, 6.0, 2.1)
    deck.text(slide, 0.9, 1.75, 5.5, 0.3, "MATEMÁTICA", 9, TEAL, bold=True)
    deck.text(
        slide,
        0.9,
        2.1,
        5.5,
        1.3,
        "Z = A_prev · W + b\nA = f(Z)\nsoftmax(z) = exp(z − max(z)) / Σ exp(z − max(z))",
        16,
        TEXT,
        font="Consolas",
    )
    deck.card(slide, 6.85, 1.55, 5.8, 2.1)
    deck.text(slide, 7.1, 1.75, 5.3, 0.3, "ATIVAÇÕES", 9, PINK, bold=True)
    deck.text(
        slide,
        7.1,
        2.1,
        5.3,
        1.3,
        "ReLU · tanh · sigmoid · leaky ReLU\nA saída é sempre softmax (2 ou 3 classes).",
        13,
        TEXT,
    )
    deck.card(slide, 0.65, 4.0, 12.0, 2.35, PANEL2)
    deck.text(slide, 0.9, 4.15, 11.4, 0.3, "LOOP DE CAMADAS (SIMPLIFICADO)", 9, TEAL, bold=True)
    deck.text(
        slide,
        0.9,
        4.5,
        11.4,
        1.7,
        "A = X\nfor W, b in zip(pesos, biases):\n    Z = A @ W + b\n    A = ativação(Z) se oculta, senão softmax(Z)\n    cache.append(A_prev, Z, A, máscara)",
        11,
        TEXT,
        font="Consolas",
    )
    deck.notes(
        slide,
        "Forward (1 min). Explicar a multiplicação de matrizes e por que softmax estável. "
        "Dizer que o cache será usado no backward.",
    )

    # 11 --------------------------------------------------------------- loss
    slide = deck.blank("Treinamento", "Loss: por que weighted cross-entropy")
    deck.card(slide, 0.65, 1.55, 5.9, 2.15)
    deck.text(slide, 0.9, 1.75, 5.4, 0.3, "CROSS-ENTROPY", 9, TEAL, bold=True)
    deck.text(slide, 0.9, 2.1, 5.4, 1.2, "L = −Σ y · log(p)\nL_weighted = Σ w_y · L_i / Σ w_y", 17, TEXT, font="Consolas")
    deck.card(slide, 6.75, 1.55, 5.9, 2.15)
    deck.text(slide, 7.0, 1.75, 5.4, 0.3, "PESOS DO NOTEBOOK", 9, PINK, bold=True)
    deck.text(slide, 7.0, 2.1, 5.4, 1.2, "classe 0: 0,5385\nclasse 1: 6,9971\n≈ 13× mais peso para o fatal", 15, TEXT)
    deck.card(slide, 0.65, 4.0, 12.0, 2.3)
    deck.text(slide, 0.9, 4.2, 11.4, 0.3, "JUSTIFICATIVA", 9, GREEN, bold=True)
    deck.bullets(
        slide,
        0.9,
        4.55,
        11.4,
        1.6,
        [
            "A classe fatal é rara; sem peso, o modelo aprende a ignorá-la.",
            "Weighted CE é estável, interpretável e não inventa amostras.",
            "Focal loss é alternativa; CE simples serve de controle.",
            "A ponderação muda o gradiente: erros fatais pesam mais.",
        ],
        12,
    )
    deck.notes(
        slide,
        "Loss (1 min). Esta é uma das decisões centrais. Mostrar a fórmula e os pesos. "
        "Explicar que a loss não é só uma métrica: ela define o que o modelo prioriza.",
    )

    # 12 --------------------------------------------------------------- backprop
    slide = deck.blank("Treinamento", "Backpropagation: como os pesos são ajustados")
    deck.card(slide, 0.65, 1.5, 6.0, 2.7)
    deck.text(slide, 0.9, 1.7, 5.5, 0.3, "REGRAGEM DA CADEIA", 9, TEAL, bold=True)
    deck.text(
        slide,
        0.9,
        2.05,
        5.5,
        1.8,
        "dL/dZ = p − y\n\ndZ_l = dA_l ⊙ f'(Z_l)\ndW_l = A_{l−1}ᵀ · dZ_l\ndb_l = Σ dZ_l",
        14,
        TEXT,
        font="Consolas",
    )
    deck.card(slide, 6.85, 1.5, 5.8, 2.7)
    deck.text(slide, 7.1, 1.7, 5.3, 0.3, "DETALHES", 9, PINK, bold=True)
    deck.bullets(
        slide,
        7.1,
        2.05,
        5.3,
        1.9,
        [
            "L2 entra como +λW em dW, não no bias.",
            "Dropout multiplica dA pela máscara.",
            "Clipping por norma global evita explosão.",
            "Gradiente numérico confere o analítico.",
        ],
        10.5,
    )
    deck.card(slide, 0.65, 4.55, 12.0, 1.8)
    deck.text(slide, 0.9, 4.72, 11.4, 0.3, "VERIFICAÇÃO", 9, GREEN, bold=True)
    deck.text(
        slide,
        0.9,
        5.05,
        11.4,
        1.0,
        "Diferenças finitas: (L(θ+ε) − L(θ−ε)) / 2ε. Erro relativo < 1e-4 em ReLU, tanh, sigmoid e leaky ReLU, "
        "com CE, weighted CE e focal.",
        12,
        TEXT,
    )
    deck.notes(
        slide,
        "Backprop (1,5 min). Explicar a regra da cadeia sem entrar em todas as derivadas. "
        "Destacar o teste de gradiente como garantia de que a matemática está correta.",
    )

    # 13 --------------------------------------------------------------- optimizers
    slide = deck.blank("Treinamento", "Otimizadores e regularização")
    cards = [
        ("SGD", "passo simples\nθ ← θ − lr·g", TEAL),
        ("Momentum", "média exponencial\nv ← βv + g", PINK),
        ("Adam", "momentos + viés\nm, v, ε", GREEN),
        ("AdamW", "weight decay\ndesacoplado", YELLOW),
    ]
    for idx, (title, sub, color) in enumerate(cards):
        deck.card(slide, 0.65 + idx * 3.05, 1.55, 2.8, 1.55)
        deck.text(slide, 0.85 + idx * 3.05, 1.72, 2.4, 0.35, title, 15, color, bold=True)
        deck.text(slide, 0.85 + idx * 3.05, 2.15, 2.4, 0.75, sub, 9.5, MUTED)
    deck.card(slide, 0.65, 3.45, 5.9, 2.6)
    deck.text(slide, 0.9, 3.63, 5.4, 0.3, "ADAM", 9, TEAL, bold=True)
    deck.text(slide, 0.9, 3.95, 5.4, 1.8, "m_t = β1m + (1−β1)g\nv_t = β2v + (1−β2)g²\nθ ← θ − lr·m̂/(√v̂ + ε)", 14, TEXT, font="Consolas")
    deck.card(slide, 6.75, 3.45, 5.9, 2.6)
    deck.text(slide, 7.0, 3.63, 5.4, 0.3, "REGULARIZAÇÃO", 9, PINK, bold=True)
    deck.bullets(
        slide,
        7.0,
        3.95,
        5.4,
        1.8,
        [
            "Dropout inverted (só no treino).",
            "L2 nos pesos, não no bias.",
            "Gradient clipping por norma.",
            "LR decay: none, step, cosine.",
        ],
        10.5,
    )
    deck.text(slide, 0.65, 6.4, 12.0, 0.35, "Padrão do projeto: Adam · lr = 1e-3 · grad_clip = 5 · sem dropout/L2.", 11, MUTED)
    deck.notes(
        slide,
        "Otimizadores (1 min). Não decorar equações; explicar que Adam adapta o passo e que clipping/regularização controlam instabilidade. "
        "Dizer por que Adam foi o padrão.",
    )

    # 14 --------------------------------------------------------------- loop
    slide = deck.blank("Treinamento", "Loop de treino e early stopping")
    steps = [
        ("1", "Split", "60/20/20"),
        ("2", "Preprocessor", "fit no treino"),
        ("3", "Mini-batches", "embaralhados"),
        ("4", "Forward", "probs + cache"),
        ("5", "Loss", "weighted CE"),
        ("6", "Backward", "gradientes"),
        ("7", "Step", "Adam + clip"),
    ]
    for idx, (number, title, sub) in enumerate(steps):
        x = 0.5 + idx * 1.82
        deck.flow_box(slide, x, 1.55, 1.65, 1.5, number, title, sub, TEAL if idx % 2 == 0 else PINK)
    deck.card(slide, 0.65, 3.55, 5.9, 2.55)
    deck.text(slide, 0.9, 3.73, 5.4, 0.3, "AO FIM DE CADA ÉPOCA", 9, TEAL, bold=True)
    deck.bullets(
        slide,
        0.9,
        4.08,
        5.4,
        1.8,
        [
            "Loss/acurácia/F1 em treino e validação.",
            "Melhor checkpoint por loss_val.",
            "Patience 5–8 sem melhora → para.",
            "Restaura o melhor conjunto de pesos.",
        ],
        10.5,
    )
    deck.card(slide, 6.75, 3.55, 5.9, 2.55)
    deck.text(slide, 7.0, 3.73, 5.4, 0.3, "POR QUE EARLY STOPPING", 9, PINK, bold=True)
    deck.text(
        slide,
        7.0,
        4.08,
        5.4,
        1.7,
        "A loss de treino continua caindo, mas a de validação estabiliza. "
        "Continuar treinando memoriza o treino e piora a generalização. "
        "O checkpoint escolhido é o da melhor validação.",
        11.5,
        TEXT,
    )
    deck.notes(
        slide,
        "Loop (1 min). Mostrar o ciclo e explicar early stopping como controle de overfitting. "
        "Dizer que o teste nunca é usado para escolher época.",
    )

    # 15 --------------------------------------------------------------- curves
    slide = deck.blank("Treinamento", "Curvas: a rede aprendeu?")
    deck.image(slide, FIG / "notebook_cell14_1.png", 0.55, 1.45, 8.2, 4.9, "Loss treino × validação e métricas")
    deck.card(slide, 8.95, 1.5, 3.85, 4.8)
    deck.text(slide, 9.15, 1.7, 3.45, 0.3, "LEITURA", 9, TEAL, bold=True)
    deck.bullets(
        slide,
        9.15,
        2.05,
        3.45,
        3.9,
        [
            "Loss de treino cai de ~0,68 para ~0,40.",
            "Validação cai até ~0,54 e estabiliza.",
            "Melhor época: 14.",
            "Early stopping interrompe.",
            "A distância treino–val indica overfitting.",
        ],
        10.5,
    )
    deck.text(slide, 0.65, 6.55, 12.0, 0.3, "Notebook: 8.000 amostras · 40 épocas máximas · 0,4 s no ambiente de teste.", 9, MUTED)
    deck.notes(
        slide,
        "Curvas (1 min). Esta é a evidência visual do aprendizado. Explicar o ponto de early stopping e o gap treino/validação.",
    )

    # 16 --------------------------------------------------------------- results
    slide = deck.blank("Resultados", "Métricas e matriz de confusão")
    deck.table(
        slide,
        ["Métrica", "Demo (3k)", "Notebook (8k)"],
        [
            ["Acurácia", br(metrics["accuracy"]), "0,7788"],
            ["F1 macro", br(metrics["precision_recall_f1"]["macro"]["f1"]), "0,5910"],
            ["F1 fatal", br(per_class[1]["f1"]), "0,3140"],
            ["ROC-AUC", br(metrics["roc_auc"]), "0,8001"],
            ["PR-AUC", br(metrics["pr_auc"]), "0,2989"],
            ["Log-loss", br(metrics["log_loss"]), "0,5035"],
        ],
        0.65,
        1.5,
        5.2,
        3.2,
        widths=[2.3, 1.5, 1.4],
        font_size=9.5,
    )
    deck.image(slide, FIG / "notebook_cell17_1.png", 6.2, 1.45, 3.7, 3.2, "Matriz de confusão (notebook)")
    deck.card(slide, 10.1, 1.5, 2.65, 3.2)
    deck.text(slide, 10.3, 1.68, 2.25, 0.3, "ALERTA", 9, RED, bold=True)
    deck.text(slide, 10.3, 2.02, 2.25, 2.3, "Baseline majoritário: 0,9287\n\nA acurácia do modelo é menor, mas ele encontra parte dos fatais.", 11, TEXT)
    deck.card(slide, 0.65, 5.0, 12.0, 1.45)
    deck.text(
        slide,
        0.9,
        5.18,
        11.5,
        0.95,
        "Matriz do notebook: 33 falsos negativos e 321 falsos positivos. "
        "O erro mais caro é o falso negativo; por isso F1 fatal e recall importam mais que acurácia.",
        12,
        TEXT,
    )
    deck.notes(
        slide,
        "Resultados (1,5 min). Explicar a matriz e o baseline. Não esconder que a acurácia é menor; "
        "mostrar o que o modelo ganha em recall da classe fatal.",
    )

    # 17 --------------------------------------------------------------- roc/calib
    slide = deck.blank("Resultados", "ROC, PR, threshold e calibração")
    deck.image(slide, FIG / "notebook_cell17_2.png", 0.55, 1.45, 7.7, 3.25, "ROC, PR e varredura de limiar")
    deck.image(slide, FIG / "notebook_cell17_3.png", 0.55, 4.75, 7.7, 2.05, "Histograma e calibração")
    deck.card(slide, 8.55, 1.5, 4.25, 5.25)
    deck.text(slide, 8.75, 1.7, 3.85, 0.3, "INTERPRETAÇÃO", 9, TEAL, bold=True)
    deck.bullets(
        slide,
        8.75,
        2.05,
        3.85,
        4.3,
        [
            "ROC-AUC mede separação global.",
            "PR-AUC é mais informativo na classe rara.",
            "Threshold 0,5 não é ótimo universal.",
            "Baixar threshold aumenta recall.",
            "ECE ~0,05: calibração razoável.",
            "A escolha do ponto é política/custo.",
        ],
        10.5,
    )
    deck.notes(
        slide,
        "Métricas (1,5 min). Explicar ROC × PR, o que é threshold e por que calibrar. "
        "Dizer que o ponto de operação depende do custo do falso negativo.",
    )

    # 18 --------------------------------------------------------------- 3 classes
    slide = deck.blank("Comparação", "Binário × 3 classes")
    deck.table(
        slide,
        ["Métrica", "Binário", "3 classes"],
        [["Acurácia", "0,7788", "0,5931"], ["F1 macro", "0,5910", "0,4817"], ["ROC-AUC", "0,8001", "0,7494"], ["PR-AUC", "0,2989", "0,5385"], ["Log-loss", "0,5035", "0,8857"]],
        0.65,
        1.55,
        5.3,
        2.8,
        widths=[2.0, 1.5, 1.5],
        font_size=10,
    )
    deck.card(slide, 6.3, 1.55, 6.3, 2.8)
    deck.text(slide, 6.55, 1.75, 5.8, 0.3, "O QUE MUDOU", 9, PINK, bold=True)
    deck.bullets(
        slide,
        6.55,
        2.1,
        5.8,
        2.0,
        [
            "3 classes: 112 features e 3 saídas.",
            "3.715 parâmetros.",
            "A tarefa fica mais difícil: F1 cai.",
            "PR-AUC 0,5385 é média OvR, não tarefa mais fácil.",
        ],
        10.5,
    )
    deck.card(slide, 0.65, 4.75, 12.0, 1.65)
    deck.text(slide, 0.9, 4.93, 11.5, 0.3, "CONCLUSÃO PRÁTICA", 9, GREEN, bold=True)
    deck.text(slide, 0.9, 5.25, 11.5, 0.9, "Para triagem de letalidade, o binário é mais direto e interpretável. O 3 classes é útil para separar sem vítimas de feridos, mas não substitui o binário.", 12, TEXT)
    deck.notes(
        slide,
        "Binário × 3 classes (1 min). Explicar que o 3 classes não é uma melhoria automática. "
        "Cada formulação responde a uma pergunta diferente.",
    )

    # 19 --------------------------------------------------------------- simulator
    slide = deck.blank("Aplicação", "Simulador e explicabilidade")
    deck.image(slide, SHOTS / "06-simulador.png", 0.55, 1.45, 7.3, 5.3, "Simulador com probabilidade e contribuições")
    deck.card(slide, 8.2, 1.5, 4.55, 5.2)
    deck.text(slide, 8.45, 1.7, 4.1, 0.3, "COMO FUNCIONA", 9, TEAL, bold=True)
    deck.bullets(
        slide,
        8.45,
        2.05,
        4.1,
        4.4,
        [
            "Escolhe um run concluído.",
            "Formulário vem de /api/meta.",
            "POST /api/predict aplica feature_frame + preprocessor.",
            "Forward com pesos do model.json.",
            "Probabilidade + classe + contribuições.",
            "Histórico local de 5 simulações.",
        ],
        10.5,
    )
    deck.text(slide, 0.6, 6.85, 12.0, 0.25, "Aviso fixo: protótipo acadêmico; não usar para decisões reais.", 8.5, RED)
    deck.notes(
        slide,
        "Simulador (1 min). Mostrar um cenário e explicar as contribuições. "
        "Reforçar que o modelo não prova causalidade; ele associa padrões.",
    )

    # 20 --------------------------------------------------------------- pages
    slide = deck.blank("Aplicação web", "Seis páginas, seis funções")
    deck.table(
        slide,
        ["Página", "Função principal", "Destaques"],
        [
            ["/", "Dashboard", "cards, histórico, CTA de treino"],
            ["/treinar", "Configurar e treinar", "6 seções, presets, SSE, curvas ao vivo"],
            ["/resultados/[id]", "Analisar um run", "matriz, ROC/PR, threshold, calibração, downloads"],
            ["/comparar", "Comparar até 4 runs", "barras, tabela de hiperparâmetros"],
            ["/simulador", "Prever um cenário", "probabilidade, contribuições, histórico"],
            ["/dados", "Consultar o dataset", "volumetria, vazamento, limitações"],
        ],
        0.65,
        1.55,
        12.0,
        3.9,
        widths=[2.7, 3.6, 5.7],
        font_size=10,
    )
    deck.callout = None
    deck.card(slide, 0.65, 5.65, 12.0, 0.85)
    deck.text(slide, 0.9, 5.82, 11.5, 0.4, "Stack: Next.js 16 · TypeScript · Tailwind · Recharts · react-hook-form + Zod · next-themes · react-icons", 10, MUTED)
    deck.notes(
        slide,
        "Páginas (1 min). Passar rapidamente pelas seis rotas antes de mostrar os prints. "
        "Dizer que o formulário reflete exatamente o DataConfig/ModelConfig da API.",
    )

    # 21 --------------------------------------------------------------- dashboard/train
    slide = deck.blank("Aplicação web", "Dashboard e treino ao vivo")
    deck.image(slide, SHOTS / "01-dashboard.png", 0.5, 1.45, 6.1, 4.7, "Dashboard")
    deck.image(slide, SHOTS / "02-treinar.png", 6.8, 1.45, 6.05, 4.7, "Formulário e painel de treino")
    deck.text(slide, 0.65, 6.25, 12.0, 0.55, "Dashboard: quatro cards + tabela de runs. Treinar: seis seções, presets, validação Zod e progresso via SSE.", 10, MUTED)
    deck.notes(
        slide,
        "Prints 1 (1 min). Mostrar o dashboard e o formulário. Destacar o painel ao vivo e o botão de resultados.",
    )

    # 22 --------------------------------------------------------------- results pages
    slide = deck.blank("Aplicação web", "Resultados, comparação e dataset")
    deck.image(slide, SHOTS / "03-resultados.png", 0.45, 1.4, 4.1, 4.55, "Resultados")
    deck.image(slide, SHOTS / "04-comparar.png", 4.65, 1.4, 4.1, 4.55, "Comparar")
    deck.image(slide, SHOTS / "05-dados.png", 8.85, 1.4, 4.1, 4.55, "Dados")
    deck.text(slide, 0.55, 6.15, 12.0, 0.6, "Resultados: matriz, ROC/PR, threshold, calibração e downloads. Comparar: até 4 runs. Dados: origem e vazamento.", 9.5, MUTED)
    deck.notes(
        slide,
        "Prints 2 (1 min). Mostrar que a análise completa está na interface, não só no notebook.",
    )

    # 23 --------------------------------------------------------------- system
    slide = deck.blank("Sistema", "Arquitetura da aplicação")
    boxes = [
        ("WEB", "Next.js 16\nproxy runtime + SSE", TEAL),
        ("API", "FastAPI\nworker de treino", PINK),
        ("DB", "PostgreSQL 16\nruns + run_epochs", GREEN),
    ]
    for idx, (title, sub, color) in enumerate(boxes):
        deck.card(slide, 1.1 + idx * 3.6, 1.65, 2.9, 1.8)
        deck.text(slide, 1.3 + idx * 3.6, 1.85, 2.5, 0.4, title, 20, color, bold=True)
        deck.text(slide, 1.3 + idx * 3.6, 2.3, 2.5, 0.9, sub, 10, MUTED)
        if idx < 2:
            deck.text(slide, 4.1 + idx * 3.6, 2.2, 0.5, 0.4, "→", 22, MUTED, bold=True)
    deck.card(slide, 0.65, 4.0, 5.9, 2.35)
    deck.text(slide, 0.9, 4.18, 5.4, 0.3, "DATA + ARTEFATOS", 9, TEAL, bold=True)
    deck.bullets(
        slide,
        0.9,
        4.5,
        5.4,
        1.6,
        [
            "data: baixa/valida o CSV uma vez.",
            "bind: backend/data e backend/artifacts.",
            "model.json, weights.npz, run.json.",
        ],
        10.5,
    )
    deck.card(slide, 6.75, 4.0, 5.9, 2.35)
    deck.text(slide, 7.0, 4.18, 5.4, 0.3, "DOCKER", 9, PINK, bold=True)
    deck.bullets(
        slide,
        7.0,
        4.5,
        5.4,
        1.6,
        [
            "make up: data → db → api → web.",
            "healthchecks e volume pgdata.",
            "make seed: run Demo.",
        ],
        10.5,
    )
    deck.notes(
        slide,
        "Arquitetura (1 min). Explicar que a API é a fonte da verdade e o frontend é um cliente. "
        "Mostrar os volumes e o papel do SSE.",
    )

    # 24 --------------------------------------------------------------- quality
    slide = deck.blank("Qualidade", "Reprodutibilidade, testes e limites")
    deck.kpi(slide, 0.65, 1.55, 2.9, 1.3, "Backend", "61", "testes", TEAL)
    deck.kpi(slide, 3.75, 1.55, 2.9, 1.3, "Frontend", "17", "Vitest", PINK)
    deck.kpi(slide, 6.85, 1.55, 2.9, 1.3, "E2E", "5", "Playwright", GREEN)
    deck.kpi(slide, 9.95, 1.55, 2.6, 1.3, "Notebook", "27", "células", YELLOW)
    deck.card(slide, 0.65, 3.15, 5.9, 2.9)
    deck.text(slide, 0.9, 3.35, 5.4, 0.3, "REPRODUTIBILIDADE", 9, TEAL, bold=True)
    deck.bullets(
        slide,
        0.9,
        3.7,
        5.4,
        2.0,
        [
            "Seed 42 em dados, split e init.",
            "SHA-256 e validação do CSV.",
            "OpenAPI + tipos TypeScript.",
            "DOCX/PDF, slides, prints e backup.",
        ],
        10.5,
    )
    deck.card(slide, 6.75, 3.15, 5.9, 2.9)
    deck.text(slide, 7.0, 3.35, 5.4, 0.3, "LIMITAÇÕES", 9, RED, bold=True)
    deck.bullets(
        slide,
        7.0,
        3.7,
        5.4,
        2.0,
        [
            "Sem velocidade, cinto, veículo ou socorro.",
            "Subnotificação e causa provável.",
            "Recorte de 2024.",
            "Próximo passo: calibração e validação por UF.",
        ],
        10.5,
    )
    deck.notes(
        slide,
        "Qualidade (1 min). Mostrar que o projeto é reproduzível e testado. "
        "Terminar com limitações para não vender o modelo como solução pronta.",
    )

    # 25 --------------------------------------------------------------- conclusion
    slide = deck.blank("Conclusão", "O que fica")
    deck.text(slide, 0.7, 1.55, 7.2, 0.35, "TRÊS CONCLUSÕES", 10, TEAL, bold=True)
    deck.bullets(
        slide,
        0.7,
        1.95,
        7.2,
        3.2,
        [
            "A MLP do zero é viável e didática.",
            "A aplicação permite treinar, comparar e simular.",
            "O teto é imposto pelos dados, não pela arquitetura.",
        ],
        19,
    )
    deck.card(slide, 0.7, 5.2, 7.2, 1.05)
    deck.text(slide, 0.95, 5.38, 6.7, 0.3, "OBRIGADO! PERGUNTAS?", 13, PINK, bold=True)
    deck.text(slide, 0.95, 5.72, 6.7, 0.3, "Protótipo acadêmico — não usar para decisões reais.", 9, MUTED)
    deck.card(slide, 8.4, 1.45, 4.3, 5.0)
    qr = slide.shapes.add_picture(str(qr_path), Inches(8.9), Inches(1.75), Inches(3.3), Inches(3.3))
    qr.line.color.rgb = BORDER
    deck.text(slide, 8.6, 5.25, 3.9, 0.3, "ACESSE", 9, TEAL, bold=True, align=PP_ALIGN.CENTER)
    deck.text(slide, 8.5, 5.6, 4.1, 0.5, VPS_URL, 10.5, TEXT, bold=True, align=PP_ALIGN.CENTER)
    deck.notes(
        slide,
        "Conclusão (30 s). Repetir as três conclusões e abrir perguntas. "
        "Deixar o QR visível para a plateia acessar a aplicação.",
    )

    deck.save()
    print(f"PPTX escrito em {OUT} ({len(deck.prs.slides)} slides)")


if __name__ == "__main__":
    build()
