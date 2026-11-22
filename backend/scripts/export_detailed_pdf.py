#!/usr/bin/env python3
"""Converte o DOCX técnico completo em PDF via mammoth + WeasyPrint."""

from __future__ import annotations

from pathlib import Path

import mammoth
from bs4 import BeautifulSoup
from weasyprint import CSS, HTML

ROOT = Path(__file__).resolve().parents[2]
DOCX = ROOT / "docs" / "TDE_documento_completo.docx"
PDF = ROOT / "docs" / "TDE_documento_completo.pdf"

CSS_TEXT = """
@page {
  size: A4;
  margin: 1.8cm 1.9cm 1.8cm 1.9cm;
  @top-right {
    content: "TDE Redes Neurais — Documento técnico";
    font-family: "DejaVu Sans", sans-serif;
    font-size: 7.5pt;
    color: #526581;
  }
  @bottom-center {
    content: counter(page) " / " counter(pages);
    font-family: "DejaVu Sans", sans-serif;
    font-size: 8pt;
    color: #526581;
  }
}
body {
  font-family: "DejaVu Sans", sans-serif;
  font-size: 9.4pt;
  line-height: 1.38;
  color: #0f172a;
}
h1 {
  font-size: 17pt;
  color: #0e7490;
  page-break-before: always;
  page-break-after: avoid;
  margin: 0.2cm 0 0.25cm 0;
}
h2 {
  font-size: 12.5pt;
  color: #0e7490;
  page-break-after: avoid;
  margin: 0.35cm 0 0.15cm 0;
}
h3 {
  font-size: 10.5pt;
  color: #0f172a;
  page-break-after: avoid;
}
p { margin: 0 0 0.18cm 0; text-align: justify; }
ul, ol { margin: 0 0 0.2cm 0.5cm; padding-left: 0.4cm; }
li { margin-bottom: 0.08cm; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.2cm 0 0.35cm 0;
  font-size: 7.6pt;
  page-break-inside: auto;
}
th, td {
  border: 0.5pt solid #cbd5e1;
  padding: 2.5pt 3pt;
  vertical-align: top;
}
th { background: #e6f4f7; color: #0f172a; font-weight: bold; }
tr { page-break-inside: avoid; }
img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0.2cm auto;
  page-break-inside: avoid;
}
strong { color: #0f172a; }
.toc { margin: 0.2cm 0 0.6cm 0; }
.toc p { margin: 0.04cm 0; text-align: left; }
.toc a { color: #0f172a; text-decoration: none; }
.toc a::after {
  content: target-counter(attr(href), page);
  float: right;
  color: #526581;
}
.toc-1 { font-weight: bold; margin-top: 0.14cm !important; }
.toc-2 { margin-left: 0.5cm !important; }
.toc-3 { margin-left: 1.0cm !important; font-size: 8.8pt; }
"""


def main() -> None:
    with DOCX.open("rb") as source:
        result = mammoth.convert_to_html(source)
    soup = BeautifulSoup(result.value, "html.parser")

    headings = soup.find_all(["h1", "h2", "h3"])
    for index, heading in enumerate(headings):
        heading["id"] = f"sec-{index}"

    summary = soup.find("h1", string=lambda text: text and text.strip() == "Sumário")
    if summary is not None:
        placeholder = summary.find_next("p")
        if placeholder is not None and "Atualize o sumário" in placeholder.get_text():
            placeholder.decompose()

        toc = soup.new_tag("div", attrs={"class": "toc"})
        for heading in headings:
            title = heading.get_text(" ", strip=True)
            if title == "Sumário":
                continue
            level = int(heading.name[1])
            paragraph = soup.new_tag("p", attrs={"class": f"toc-{level}"})
            link = soup.new_tag("a", href=f"#{heading['id']}")
            link.string = title
            paragraph.append(link)
            toc.append(paragraph)
        summary.insert_after(toc)

    html = str(soup)
    HTML(string=html, base_url=str(ROOT)).write_pdf(
        PDF, stylesheets=[CSS(string=CSS_TEXT)]
    )
    print(f"PDF escrito em {PDF}")


if __name__ == "__main__":
    main()
